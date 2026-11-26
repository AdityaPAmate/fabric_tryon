"""Real requests/HTTP against a local Gimmeclip stand-in, no external calls."""
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import skipUnless
from shutil import which
from unittest.mock import patch
from urllib.parse import urlsplit
import requests
from PIL import Image
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from fabricapp.video.gimmeclip import BASE, GimmeclipClient, checked_url
from fabricapp.video.errors import VideoError
from fabricapp.video.profiles import PROFILES, select_profile
from fabricapp.video.garments.shirt_prompts import WALKING_PROMPT
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

    def test_walking_recipe_keeps_source_and_uses_eight_seconds(self):
        client=GimmeclipClient()
        self.assertEqual(client.submit(PHOTO,select_profile({'garment_type':'shirt','video_motion':'walking'})),JOB)
        recipe=json.loads(self.calls[-1][3])['recipe']
        self.assertEqual(recipe['source'],{'url':PHOTO,'start':0,'end':8})
        self.assertEqual(recipe['aiEdit'],{'idea':WALKING_PROMPT,'animate':True})
        self.assertLessEqual(len(WALKING_PROMPT),300)

    def test_saree_catwalk_uses_the_complete_photo_and_a_single_eight_second_animation(self):
        profile = select_profile({'garment_type': 'saree'})
        self.assertEqual(profile['motion'], 'walking')
        self.assertEqual(profile['version'], 'fabric-gimme-saree-catwalk-v5')
        self.assertEqual(profile['camera_motion'], 'zoom_out')
        self.assertNotIn('multi_shot', profile)
        self.assertEqual(GimmeclipClient().submit(PHOTO, profile), JOB)
        recipe = json.loads(self.calls[-1][3])['recipe']
        self.assertEqual(recipe['source'], {'url': PHOTO, 'start': 0, 'end': 8})
        self.assertEqual(recipe['frame'], 'original')
        self.assertEqual(recipe['aiEdit'], {'idea': profile['prompt'], 'animate': True})
        idea = recipe['aiEdit']['idea']
        self.assertIn('TWO slow short steps', idea)
        self.assertLess(idea.index('turn RIGHT to full BACK'), idea.index('turn LEFT to front'))
        self.assertIn('No spin/dance/anklets/bells/new jewellery/pulling', idea)
        self.assertIn('hem/drape, scene/light and footwear', idea)
        self.assertNotIn('feet planted', idea)
        self.assertNotIn('15 degrees', idea)
        self.assertEqual(set(recipe), {'v', 'source', 'frame', 'aiEdit'})

    def test_commercial_recipe_uses_gimmeclip_with_four_shot_prompt(self):
        profile = select_profile({'garment_type':'shirt','video_motion': 'shirt_commercial'})
        self.assertEqual(GimmeclipClient().submit(PHOTO, profile), JOB)
        recipe = json.loads(self.calls[-1][3])['recipe']
        self.assertEqual(recipe['source'], {'url': PHOTO, 'start': 0, 'end': 8})
        self.assertEqual(recipe['frame'], 'original')
        self.assertEqual(recipe['aiEdit'], {'idea': profile['prompt'], 'animate': True})
        self.assertLessEqual(len(profile['prompt']), 300)
        self.assertTrue(profile['source_collar_opening'])
        for cue in ('0-3.5s sleeve/cuff close-up', 'arm moves gently', 'head-to-waist',
                    'front waist-up walk TOWARD camera', 'Slightly elevated camera tracks BACKWARD only', 'No side view',
                    'EXACT source colour/print/scale/weave/fit in ALL shots', 'No redesign/recolour'):
            self.assertIn(cue, profile['prompt'])

    @skipUnless(which('ffmpeg'), 'FFmpeg required')
    def test_commercial_worker_animates_saved_image_via_gimmeclip_only(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory, override_settings(
                MEDIA_ROOT=directory, CLOUDFLARE_ACCOUNT_ID='', CLOUDFLARE_API_TOKEN=''):
            response = self.client.post('/api/animate-image/', {
                'source_image': SimpleUploadedFile('result.png', photo_bytes(), 'image/png'),
                'garment_type': 'shirt', 'video_motion': 'shirt_commercial'},
                HTTP_AUTHORIZATION='Bearer test-token')
            self.assertEqual(response.status_code, 202, response.content)
            job = VideoJob.objects.get(pk=response.json()['job_id'])
            self.__class__.video_payload = animation_bytes('saturation', seconds=8)
            with patch('fabricapp.video.collar.find_face', return_value=(18, 3, 28, 34)), \
                 patch('fabricapp.video.service.generate_image') as generate, \
                 patch('fabricapp.video.service.upload_generated_image', return_value={'url': 'https://cdn.example/photo.png'}), \
                 patch('fabricapp.video.storage.cloudinary.uploader.upload', return_value={'secure_url': 'https://cdn.example/commercial.mp4'}):
                process_job(job)
                self.assertEqual(job.status, 'completed', job.error_message)
                self.assertEqual(job.provider_video_url, EDITED_VIDEO)
                self.assertEqual(job.video['continuity']['status'], 'not_applicable')
                self.assertEqual(job.video['composition']['opening_seconds'], 2)
                self.assertEqual(next(c for c in self.calls if c[1] == '/api/v0/photos')[3], photo_bytes())
                submitted = next(c for c in self.calls if c[1] == '/api/v0/edits')
                self.assertEqual(json.loads(submitted[3])['recipe']['aiEdit']['idea'], job.motion_profile['prompt'])
                generate.assert_not_called()
                before = len(self.calls)
                process_job(job)
                self.assertEqual(len(self.calls), before)
            self.assertEqual(sum(method == 'POST' and path == '/api/v0/edits'
                                 for method, path, _, _ in self.calls), 1)

    def test_removed_provider_job_is_not_silently_resubmitted_to_gimmeclip(self):
        job = VideoJob.objects.create(status='queued',
            motion_profile={'provider': 'cloudflare_pixverse', 'motion': 'shirt_commercial'},
            image={'url': 'https://cdn.example/photo.png'})
        with patch('fabricapp.video.service.generate_image') as generate:
            process_job(job)
        self.assertEqual(job.status, 'failed')
        self.assertEqual(job.error_code, 'legacy_provider_job')
        self.assertFalse(job.retryable)
        self.assertEqual(self.calls, [])
        generate.assert_not_called()

    def test_missing_collar_fails_before_paid_gimmeclip_submission(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory, override_settings(MEDIA_ROOT=directory):
            response = self.client.post('/api/animate-image/', {
                'source_image': SimpleUploadedFile('result.png', photo_bytes(), 'image/png'),
                'garment_type': 'shirt', 'video_motion': 'shirt_commercial'},
                HTTP_AUTHORIZATION='Bearer test-token')
            self.assertEqual(response.status_code, 202)
            job = VideoJob.objects.get(pk=response.json()['job_id'])
            with patch('fabricapp.video.service.upload_generated_image', return_value={'url': 'https://cdn.example/photo.png'}):
                process_job(job)
            self.assertEqual(job.error_code, 'collar_not_found')
            self.assertTrue(job.image)
            self.assertTrue(job.image_file)
            self.assertFalse(job.retryable)
            self.assertEqual(self.calls, [])

    def test_saved_older_commercial_job_is_delivered_without_a_new_opening(self):
        job = VideoJob.objects.create(status='video_storing', profile_version='fabric-gimme-shirt-commercial-v5',
            motion_profile={'motion': 'shirt_commercial', 'multi_shot': True},
            provider_video_url=EDITED_VIDEO, image={'url': 'https://cdn.example/photo.png'})
        with patch('fabricapp.video.collar.render_commercial') as render, \
             patch('fabricapp.video.storage.cloudinary.uploader.upload', return_value={'secure_url': 'https://cdn.example/old.mp4'}):
            process_job(job)
        self.assertEqual(job.status, 'completed', job.error_message)
        self.assertNotIn('composition', job.video)
        render.assert_not_called()
        self.assertEqual([(method, path) for method, path, _, _ in self.calls],
                         [('GET', urlsplit(EDITED_VIDEO).path)])

    def test_provider_failure_details_survive_worker_and_hide_credentials(self):
        from fabricapp.video.service import job_response
        job=VideoJob.objects.create(status='video_generating',polling_url=JOB,
            image={'url':'https://cdn.example/photo.png'})
        self.__class__.poll_reply=(200,{'state':'error','code':'upstream_error',
            'failedStage':'generating',
            'error':'Model unavailable fake-gimme-key test-token Bearer secret123 https://private.example/photo gc_privatekey'})
        process_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status,'failed')
        self.assertEqual(job.provider_error['code'],'upstream_error')
        self.assertEqual(job.provider_error['stage'],'generating')
        data=job_response(job)
        self.assertEqual(data['error']['provider'],job.provider_error)
        serialized=json.dumps(data)
        for secret in ('fake-gimme-key','test-token','secret123','private.example','gc_privatekey'):
            self.assertNotIn(secret,serialized)
        self.assertIn('Model unavailable',serialized)
        self.assertFalse(data['error']['retryable'])

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

    def test_visual_warning_keeps_image_and_delivers_video_for_review(self):
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
                 patch('fabricapp.video.storage.cloudinary.uploader.upload',return_value={'secure_url':'https://cdn.example/review.mp4'}) as upload:
                process_job(job)
            self.assertEqual(job.status,'completed',job.error_message)
            self.assertEqual(job.image['url'],'https://cdn.example/photo.png')
            self.assertEqual(job.video['continuity']['status'],'review_required')
            upload.assert_called_once()
            retry=self.client.post(f'/api/video-jobs/{job.pk}/retry/', HTTP_AUTHORIZATION='Bearer test-token')
            self.assertEqual(retry.status_code,409)
            self.assertEqual(sum(method=='POST' and path=='/api/v0/edits' for method,path,_,_ in self.calls),1)

    def test_legacy_quality_failure_recovers_same_clip_without_new_generation(self):
        job=VideoJob.objects.create(status='failed',error_code='video_continuity_failed',
            error_message='Old blocking check',retryable=False,
            provider_video_url=EDITED_VIDEO,image={'url':'https://cdn.example/photo.png'})
        auth={'HTTP_AUTHORIZATION':'Bearer test-token'}
        response=self.client.get(f'/api/video-jobs/{job.pk}/',**auth)
        self.assertTrue(response.json()['error']['retryable'])
        retry=self.client.post(f'/api/video-jobs/{job.pk}/retry/',**auth)
        self.assertEqual(retry.status_code,202)
        self.assertEqual(self.client.post(f'/api/video-jobs/{job.pk}/retry/',**auth).status_code,409)
        job.refresh_from_db()
        self.__class__.video_payload=animation_bytes('saturation')
        with patch('fabricapp.video.service.generate_image') as generate, \
             patch('fabricapp.video.storage.cloudinary.uploader.upload',return_value={'secure_url':'https://cdn.example/recovered.mp4'}):
            process_job(job)
        self.assertEqual(job.status,'completed',job.error_message)
        self.assertEqual(job.video['continuity']['status'],'review_required')
        generate.assert_not_called()
        self.assertEqual([(method,path) for method,path,_,_ in self.calls], [('GET',urlsplit(EDITED_VIDEO).path)])
