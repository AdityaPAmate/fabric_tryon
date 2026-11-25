"""Real HTTP stand-in for commercial generation/CDN; no paid external calls."""
import base64
import io
import json
import tempfile
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import requests
from PIL import Image
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.models import VideoJob
from fabricapp.video.commercial import profile, PROMPT
from fabricapp.video.errors import VideoError
from fabricapp.video.pixverse import PixverseClient, checked_video_url
from fabricapp.video.service import process_job
from fabricapp.test_video_continuity import animation_bytes

VIDEO = 'https://media.pixverse.ai/pixverse%2Fmp4%2Fcommercial.mp4'


def photo(colour):
    out=io.BytesIO()
    Image.new('RGB',(64,96),colour).save(out,'PNG')
    return out.getvalue()


@override_settings(GIMMECLIP_API_KEY='fake-gimme', VIDEO_API_TOKEN='test-token',
                   CLOUDFLARE_ACCOUNT_ID='a'*32, CLOUDFLARE_API_TOKEN='private-cf-token')
class PixverseHTTPTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.video=animation_bytes('saturation')  # intentional storyboard cuts
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                body=self.rfile.read(int(self.headers.get('Content-Length',0)))
                cls.calls.append(('POST',dict(self.headers),body))
                status,payload=cls.reply
                self.send_response(status);self.end_headers()
                self.wfile.write(payload if isinstance(payload,bytes) else json.dumps(payload).encode())
            def do_GET(self):
                cls.calls.append(('GET',dict(self.headers),b''))
                self.send_response(200);self.end_headers();self.wfile.write(cls.video)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
        super().tearDownClass()

    def setUp(self):
        self.__class__.calls=[]
        self.__class__.reply=(200,{'state':'Completed','result':{'video':VIDEO}})
        session=requests.Session();session.trust_env=False;self.addCleanup(session.close)
        local=f'http://127.0.0.1:{self.server.server_port}'
        def post(url,**kwargs):
            self.assertEqual(url,'https://api.cloudflare.com/client/v4/accounts/'+'a'*32+'/ai/run')
            self.assertFalse(kwargs['allow_redirects'])
            return session.post(local+'/ai/run',**kwargs)
        def get(url,**kwargs):
            self.assertEqual(url,VIDEO)
            self.assertNotIn('Authorization',kwargs['headers'])
            self.assertFalse(kwargs['allow_redirects'])
            return session.get(local+'/video.mp4',**kwargs)
        for name,handler in (('post',post),('get',get)):
            mock=patch('fabricapp.video.pixverse.requests.'+name,side_effect=handler)
            mock.start();self.addCleanup(mock.stop)

    def test_request_preserves_source_and_all_four_shots(self):
        image=photo('navy');client=PixverseClient()
        self.assertEqual(client.generate(image,profile()),VIDEO)
        data=json.loads(self.calls[0][2]);inputs=data['input']
        self.assertEqual(data['model'],'pixverse/v6')
        self.assertEqual(inputs['prompt'],PROMPT)
        for shot in ('0-1.5s','1.5-3s','3-6s','6-8s','35-45-degree','SAME head-to-mid-thigh'):
            self.assertIn(shot,inputs['prompt'])
        self.assertEqual(base64.b64decode(inputs['image_input'].split(',',1)[1]),image)
        self.assertEqual((inputs['duration'],inputs['quality'],inputs['aspect_ratio']),(8,'540p','9:16'))
        self.assertFalse(inputs['generate_audio'])
        self.assertEqual(self.calls[0][1]['Authorization'],'Bearer private-cf-token')
        with client.download(VIDEO) as response:self.assertEqual(response.content,self.video)
        self.assertNotIn('Authorization',self.calls[-1][1])

    def test_ambiguous_submission_never_retries(self):
        for reply in ((503,{}),(302,{}),(200,b'bad json'),(200,{}),
                      (200,{'state':'Completed','result':{'video':'https://evil.example/video.mp4'}})):
            with self.subTest(reply=reply):
                self.__class__.reply=reply;before=len(self.calls)
                with self.assertRaises(VideoError) as error:PixverseClient().generate(photo('navy'),profile())
                self.assertEqual(error.exception.code,'submission_unknown')
                self.assertFalse(error.exception.retryable)
                self.assertEqual(len(self.calls),before+1)

    def test_billing_rejection_is_safe_and_does_not_retry(self):
        self.__class__.reply=(402,{'errors':[{'message':'Add credits private-cf-token https://private.example'}]})
        with self.assertRaises(VideoError) as error:PixverseClient().generate(photo('navy'),profile())
        self.assertEqual(error.exception.code,'provider_failed')
        self.assertIn('Add credits',str(error.exception))
        self.assertNotIn('private-cf-token',str(error.exception))
        self.assertNotIn('private.example',str(error.exception))
        self.assertEqual(len(self.calls),1)

    def test_download_rejects_untrusted_hosts_before_request(self):
        for url in ('http://media.pixverse.ai/video.mp4','https://evil.example/video.mp4',
                    'https://media.pixverse.ai.evil.example/video.mp4','https://user@media.pixverse.ai/video.mp4'):
            with self.subTest(url=url),self.assertRaises(VideoError):PixverseClient().download(url)
        self.assertEqual(self.calls,[])

    def test_worker_uses_fabric_swapped_image_and_reuses_finished_video_on_retry(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory,override_settings(MEDIA_ROOT=directory):
            response=self.client.post('/api/generate-tryon-video/',{
                'fabric_image':SimpleUploadedFile('swatch.png',photo('gold'),'image/png'),
                'garment_type':'shirt','gender':'men','video_motion':'shirt_commercial'},
                HTTP_AUTHORIZATION='Bearer test-token')
            self.assertEqual(response.status_code,202,response.content)
            job=VideoJob.objects.get(pk=response.json()['job_id'])
            with patch('fabricapp.video.service.generate_image',return_value=GenerationResult(photo('navy'),42)) as generate, \
                 patch('fabricapp.video.service.upload_generated_image',return_value={'url':'https://cdn.example/source.png'}), \
                 patch('fabricapp.video.service.GimmeclipClient') as gimme, \
                 patch('fabricapp.video.storage.cloudinary.uploader.upload',side_effect=[RuntimeError(),{'secure_url':'https://cdn.example/commercial.mp4'}]):
                process_job(job)
                self.assertEqual(job.status,'failed');self.assertTrue(job.retryable)
                self.assertEqual(job.provider_video_url,VIDEO)
                retry=self.client.post(f'/api/video-jobs/{job.pk}/retry/',HTTP_AUTHORIZATION='Bearer test-token')
                self.assertEqual(retry.status_code,202);job.refresh_from_db();process_job(job)
            self.assertEqual(job.status,'completed',job.error_message)
            self.assertEqual(job.video['continuity']['status'],'not_applicable')
            generate.assert_called_once();gimme.assert_not_called()
            self.assertEqual([x[0] for x in self.calls],['POST','GET','GET'])
            sent=json.loads(self.calls[0][2])['input']['image_input']
            self.assertEqual(base64.b64decode(sent.split(',',1)[1]),photo('navy'))

    def test_interrupted_commercial_submission_cannot_resubmit(self):
        job=VideoJob.objects.create(status='video_submitting',motion_profile=profile(),
            image={'url':'https://cdn.example/source.png'})
        process_job(job)
        self.assertEqual(job.error_code,'submission_unknown')
        self.assertFalse(job.retryable)
        self.assertIn('Cloudflare',job.error_message)
        self.assertEqual(self.calls,[])
