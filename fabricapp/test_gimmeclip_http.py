"""Real requests/HTTP against a local Gimmeclip stand-in, no external calls."""
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import urlsplit
import requests
from PIL import Image
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from fabricapp.video.gimmeclip import BASE, GimmeclipClient, checked_url
from fabricapp.video.errors import VideoError
from fabricapp.video.profiles import PROFILES
from fabricapp.models import VideoJob
from fabricapp.video.service import process_job
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.test_video_continuity import animation_bytes

PHOTO = BASE + '/api/v0/photos/' + 'a' * 32
JOB = BASE + '/api/v0/edits/' + 'b' * 64
EDITED_VIDEO = BASE + '/api/v0/clips/' + 'c' * 64 + '/file'
VIDEO = BASE + '/api/v0/clips/' + 'd' * 64 + '/file'


def photo_bytes():
    out = io.BytesIO()
    Image.new('RGB', (64, 96), '#338899').save(out, 'PNG')
    return out.getvalue()


@override_settings(GIMMECLIP_API_KEY='fake-gimme-key', VIDEO_API_TOKEN='test-token')
class GimmeclipHTTPTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stable_video = animation_bytes()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def handle_request(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                cls.calls.append((self.command, self.path, dict(self.headers), raw))
                if self.path.endswith('/config'):
                    code, body = 200, {'aiEdit': {'perDay': 6}}
                elif self.path == '/api/v0/photos':
                    code, body = 201, {'url': PHOTO}
                elif self.path == '/api/v0/edits':
                    code, body = cls.submit_reply
                elif self.path.startswith('/api/v0/edits/'):
                    code, body = cls.poll_reply
                elif self.path in (urlsplit(VIDEO).path, urlsplit(EDITED_VIDEO).path):
                    code, body = 200, cls.video_payload
                else:
                    code, body = 501, {'error': 'Endpoint not modeled'}
                self.send_response(code)
                if code == 302:
                    self.send_header('Location', 'https://evil.example/steal')
                self.end_headers()
                self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())
            do_POST = handle_request
            do_GET = handle_request
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.__class__.calls = []
        self.__class__.submit_reply = (202, {'id': 'b' * 64})
        self.__class__.poll_reply = (200, {'state': 'done', 'clip': {'id': 'c' * 64}, 'aiClip': 'd' * 64})
        self.__class__.video_payload = self.stable_video
        self.session = requests.Session()
        self.session.trust_env = False
        self.addCleanup(self.session.close)
        def route(method, url, **kwargs):
            self.assertTrue(url.startswith(BASE + '/api/v0/'), url)
            self.assertFalse(kwargs['allow_redirects'])
            return self.session.request(method, url.replace(BASE, f'http://127.0.0.1:{self.server.server_port}', 1), **kwargs)
        self.routing = patch('fabricapp.video.gimmeclip.requests.request', side_effect=route)
        self.routing.start()
        self.addCleanup(self.routing.stop)

    def test_upload_submit_poll_and_authenticated_download(self):
        client = GimmeclipClient()
        image = photo_bytes()
        self.assertEqual(client.upload_photo(image), PHOTO)
        upload = self.calls[-1]
        self.assertEqual(upload[2]['Content-Type'], 'image/png')
        self.assertEqual(upload[3], image)
        self.assertEqual(client.submit(PHOTO, PROFILES['shirt']), JOB)
        body = json.loads(self.calls[-1][3])['recipe']
        self.assertEqual(body['source'], {'url': PHOTO, 'start': 0, 'end': 8})
        self.assertTrue(body['aiEdit']['animate'])
        self.assertEqual(set(body), {'v','source','frame','aiEdit'})
        self.assertEqual(body['frame'],'original')
        self.assertLessEqual(len(body['aiEdit']['idea']), 300)
        self.assertNotIn('seed', body)
        self.assertEqual(client.poll(JOB), EDITED_VIDEO)
        with client.download(EDITED_VIDEO) as response:
            self.assertEqual(response.content, self.stable_video)
        self.assertEqual(len(self.calls), 5)
        for _, _, headers, _ in self.calls:
            self.assertEqual(headers['Authorization'], 'Bearer fake-gimme-key')

    def test_completed_clip_selection_matches_gimme_video_lab(self):
        client=GimmeclipClient()
        self.assertEqual(client.poll(JOB),EDITED_VIDEO)
        self.__class__.poll_reply=(200,{'state':'done','clip':{'id':'c'*64}})
        self.assertEqual(client.poll(JOB),EDITED_VIDEO)
        self.__class__.poll_reply=(200,{'state':'done','aiClip':'d'*64})
        self.assertEqual(client.poll(JOB),VIDEO)
        for value in ('not-a-clip-id', 'https://evil.example/video', 42):
            with self.subTest(value=value):
                self.__class__.poll_reply=(200,{'state':'done','clip':{'id':value}})
                with self.assertRaises(VideoError):
                    client.poll(JOB)

    def test_pending_errors_and_invalid_completion(self):
        client = GimmeclipClient()
        for state in ['source', 'generating', 'transcribing', 'translating', 'rendering', 'saving']:
            self.__class__.poll_reply = (200, {'state': state})
            self.assertIsNone(client.poll(JOB))
        for code, body, expected in [(503, b'<html>down</html>', 'provider_rejected'),
                                      (200, b'not-json', 'invalid_provider_response'),
                                      (200, {'state': 'error'}, 'provider_failed'),
                                      (200, {'state': 'done'}, 'invalid_video_response')]:
            with self.subTest(body=body):
                self.__class__.poll_reply = (code, body)
                with self.assertRaises(VideoError) as error:
                    client.poll(JOB)
                self.assertEqual(error.exception.code, expected)

    def test_ambiguous_submission_is_never_retried(self):
        for reply in [(502, b'bad gateway'), (202, b'not-json'), (202, {}),
                      (302, {}), (408, {})]:
            with self.subTest(reply=reply):
                self.__class__.submit_reply = reply
                before = len(self.calls)
                with self.assertRaises(VideoError) as error:
                    GimmeclipClient().submit(PHOTO, PROFILES['shirt'])
                self.assertEqual(error.exception.code, 'submission_unknown')
                self.assertFalse(error.exception.retryable)
                self.assertEqual(len(self.calls), before + 1)

    def test_quota_rejection_is_retryable_but_does_not_resubmit(self):
        self.__class__.submit_reply = (429, {'error': 'quota'})
        with self.assertRaises(VideoError) as error:
            GimmeclipClient().submit(PHOTO, PROFILES['shirt'])
        self.assertEqual(error.exception.code, 'quota_exceeded')
        self.assertTrue(error.exception.retryable)
        self.assertEqual(len(self.calls), 1)

    def test_untrusted_paths_never_receive_a_request(self):
        for kind, url in [('job', 'https://evil.example/status'),
                          ('job', 'http://gimmeclip.com/api/v0/edits/' + 'b' * 64),
                          ('video', VIDEO + '?redirect=evil'),
                          ('photo', 'https://gimmeclip.com.evil.example/api/v0/photos/' + 'a' * 32)]:
            with self.subTest(url=url), self.assertRaises(VideoError):
                checked_url(url, kind)
        self.assertEqual(self.calls, [])

    def test_full_worker_uses_generated_fabric_swap_photo_over_real_http(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory, override_settings(MEDIA_ROOT=directory):
            # Different bytes distinguish the input swatch from the generated photo.
            swatch = io.BytesIO()
            Image.new('RGB', (32, 32), '#ffcc00').save(swatch, 'PNG')
            response = self.client.post('/api/generate-tryon-video/', {
                'fabric_image': SimpleUploadedFile('fabric.png', swatch.getvalue(), 'image/png'),
                'garment_type': 'shirt', 'gender': 'men'}, HTTP_AUTHORIZATION='Bearer test-token')
            self.assertEqual(response.status_code, 202)
            job = VideoJob.objects.get(pk=response.json()['job_id'])
            with patch('fabricapp.video.service.generate_image', return_value=GenerationResult(photo_bytes(), 42)) as generate, \
                 patch('fabricapp.video.service.upload_generated_image', return_value={'url': 'https://res.cloudinary.com/test/image.png'}), \
                 patch('fabricapp.video.storage.cloudinary.uploader.upload', return_value={'secure_url': 'https://res.cloudinary.com/test/video.mp4', 'duration': 8}):
                process_job(job)
                self.assertEqual(job.status, 'completed', job.error_message)
                self.assertEqual(next(c for c in self.calls if c[1] == '/api/v0/photos')[3], photo_bytes())
                self.assertIsNotNone(job.timing.get('video_ready_at'))
                before = len(self.calls)
                process_job(job)
                self.assertEqual(len(self.calls), before)
                self.assertEqual(generate.call_count, 1)

    def test_missing_clip_retry_reuses_photo_and_existing_provider_job(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory, override_settings(MEDIA_ROOT=directory):
            response=self.client.post('/api/animate-image/', {
                'source_image':SimpleUploadedFile('result.png',photo_bytes(),'image/png'),
                'garment_type':'shirt'}, HTTP_AUTHORIZATION='Bearer test-token')
            self.assertEqual(response.status_code,202)
            job=VideoJob.objects.get(pk=response.json()['job_id'])
            with patch('fabricapp.video.service.generate_image') as generate, \
                 patch('fabricapp.video.service.upload_generated_image',return_value={'url':'https://cdn.example/photo.png'}), \
                 patch('fabricapp.video.storage.cloudinary.uploader.upload',return_value={'secure_url':'https://cdn.example/video.mp4'}) as store:
                self.__class__.poll_reply=(200,{'state':'done'})
                process_job(job)
                self.assertEqual(job.status,'failed')
                self.assertEqual(job.error_code,'invalid_video_response')
                self.assertTrue(job.retryable)
                self.assertEqual(job.polling_url,JOB)
                self.assertFalse(job.provider_video_url)
                store.assert_not_called()
                retry=self.client.post(f'/api/video-jobs/{job.pk}/retry/', HTTP_AUTHORIZATION='Bearer test-token')
                self.assertEqual(retry.status_code,202)
                job.refresh_from_db()
                self.__class__.poll_reply=(200,{'state':'done','clip':{'id':'c'*64},'aiClip':'d'*64})
                process_job(job)
                self.assertEqual(job.status,'completed',job.error_message)
                self.assertEqual(job.provider_video_url,EDITED_VIDEO)
                self.assertTrue(any(method=='GET' and path==urlsplit(EDITED_VIDEO).path
                                    for method,path,_,_ in self.calls))
                generate.assert_not_called()
                store.assert_called_once()
            self.assertEqual(sum(method=='POST' and path=='/api/v0/photos' for method,path,_,_ in self.calls),1)
            self.assertEqual(sum(method=='POST' and path=='/api/v0/edits' for method,path,_,_ in self.calls),1)

    def test_quality_failure_keeps_image_and_does_not_upload_or_queue_again(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory, override_settings(MEDIA_ROOT=directory):
            response=self.client.post('/api/animate-image/', {
                'source_image':SimpleUploadedFile('result.png',photo_bytes(),'image/png'),
                'garment_type':'shirt'}, HTTP_AUTHORIZATION='Bearer test-token')
            self.assertEqual(response.status_code,202)
            job=VideoJob.objects.get(pk=response.json()['job_id'])
            self.__class__.video_payload=animation_bytes('saturation')
            with patch('fabricapp.video.service.upload_generated_image',return_value={'url':'https://cdn.example/photo.png'}), \
                 patch('fabricapp.video.storage.cloudinary.uploader.upload') as upload:
                process_job(job)
            self.assertEqual(job.status,'failed')
            self.assertEqual(job.error_code,'video_continuity_failed')
            self.assertFalse(job.retryable)
            self.assertEqual(job.image['url'],'https://cdn.example/photo.png')
            self.assertFalse(job.video)
            upload.assert_not_called()
            retry=self.client.post(f'/api/video-jobs/{job.pk}/retry/', HTTP_AUTHORIZATION='Bearer test-token')
            self.assertEqual(retry.status_code,409)
            self.assertEqual(sum(method=='POST' and path=='/api/v0/edits' for method,path,_,_ in self.calls),1)
