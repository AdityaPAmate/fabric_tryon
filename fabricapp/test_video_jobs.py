"""Durable orchestration tests. No Cloudflare, Gimmeclip or Cloudinary calls."""
import io
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.models import VideoJob
from fabricapp.video.errors import VideoError
from fabricapp.video.service import process_job
from fabricapp.video.worker_lock import exclusive_worker


def image_bytes():
    output = io.BytesIO()
    Image.new('RGB', (64, 96), '#336699').save(output, 'PNG')
    return output.getvalue()


@override_settings(GIMMECLIP_API_KEY='test-gimmeclip-key', VIDEO_API_TOKEN='test-token')
class VideoJobTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path.cwd())
        self.addCleanup(self.temp.cleanup)
        self.config = override_settings(MEDIA_ROOT=Path(self.temp.name))
        self.config.enable()
        self.addCleanup(self.config.disable)
        self.auth = {}

    def create(self, **changes):
        data = {'fabric_image': SimpleUploadedFile('swatch.png', image_bytes(), 'image/png'),
                'garment_type': 'shirt', 'gender': 'men', 'camera_view': 'front', 'wait': False}
        data.update(changes)
        return self.client.post('/api/generate-tryon-video/', data, **self.auth)

    def job(self):
        response = self.create()
        self.assertEqual(response.status_code, 202, response.content)
        return VideoJob.objects.get(pk=response.json()['job_id'])

    def test_create_only_queues_and_persists_inputs(self):
        with patch('fabricapp.video.service.generate_image') as generate:
            job = self.job()
        generate.assert_not_called()
        self.assertEqual(job.status, 'queued')
        self.assertTrue((Path(self.temp.name) / job.inputs['fabric_image']).exists())
        self.assertEqual(job.payload['camera_view'], 'front')

    def test_default_post_waits_and_returns_both_urls_from_one_job(self):
        def complete(_seconds):
            job = VideoJob.objects.get()
            self.assertNotIn('wait', job.payload)
            VideoJob.objects.filter(pk=job.pk).update(status='completed',
                image={'url': 'https://cdn.example/photo.png'},
                video={'url': 'https://cdn.example/video.mp4', 'duration': 8})
        with patch('fabricapp.video.views.time.sleep', side_effect=complete), \
             patch('fabricapp.video.service.generate_image') as image_generator:
            data = {'fabric_image': SimpleUploadedFile('fabric.png', image_bytes(), 'image/png'),
                    'garment_type': 'saree', 'gender': 'women'}
            response = self.client.post('/api/generate-tryon-video/', data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'completed')
        self.assertTrue(response.json()['image']['url'])
        self.assertTrue(response.json()['video']['url'])
        self.assertEqual(VideoJob.objects.count(), 1)
        image_generator.assert_not_called()  # Generation remains in the worker.

    def test_wait_returns_failure_and_saved_image_without_resubmission(self):
        def fail(_seconds):
            VideoJob.objects.all().update(status='failed', image={'url': 'saved-photo'},
                error_code='provider_failed', error_message='Video unavailable')
        with patch('fabricapp.video.views.time.sleep', side_effect=fail):
            response = self.client.post('/api/animate-image/', {
                'source_image': SimpleUploadedFile('photo.png', image_bytes(), 'image/png'),
                'garment_type': 'saree'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'failed')
        self.assertEqual(response.json()['image']['url'], 'saved-photo')
        self.assertEqual(VideoJob.objects.count(), 1)

    def test_wait_deadline_returns_same_pending_job_without_cancelling(self):
        with patch('fabricapp.video.views.MAX_WAIT_SECONDS', 0):
            response = self.create(wait=True)
        self.assertEqual(response.status_code, 202)
        job = VideoJob.objects.get(pk=response.json()['job_id'])
        self.assertEqual(job.status, 'queued')
        self.assertNotIn('wait', job.payload)

    def test_invalid_wait_is_rejected_before_creating_a_job(self):
        self.assertEqual(self.create(wait='unknown').status_code, 400)
        self.assertEqual(VideoJob.objects.count(), 0)

    def test_retry_can_return_the_final_result_on_the_same_post(self):
        job = self.job()
        job.status = 'failed'
        job.retryable = True
        job.save()
        def complete(_seconds):
            VideoJob.objects.filter(pk=job.pk).update(status='completed', video={'url': 'saved-clip'})
        with patch('fabricapp.video.views.time.sleep', side_effect=complete):
            response = self.client.post(f'/api/video-jobs/{job.pk}/retry/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['job_id'], str(job.pk))
        self.assertEqual(response.json()['video']['url'], 'saved-clip')
        self.assertEqual(VideoJob.objects.count(), 1)

    def test_no_token_needed_but_provider_configuration_is_still_required(self):
        with override_settings(VIDEO_API_TOKEN=''):
            response = self.create()
        self.assertEqual(response.status_code, 202)
        job_id = response.json()['job_id']
        self.assertEqual(self.client.get(f'/api/video-jobs/{job_id}/').status_code, 200)
        self.assertEqual(self.client.get('/api/video-jobs/00000000-0000-0000-0000-000000000000/').status_code, 404)
        with override_settings(GIMMECLIP_API_KEY=''):
            self.assertEqual(self.create().status_code, 503)
            # Existing results remain readable even if provider config is missing.
            self.assertEqual(self.client.get(f'/api/video-jobs/{job_id}/').status_code, 200)
        self.assertEqual(VideoJob.objects.count(), 1)

    def test_queued_response_has_only_the_public_contract(self):
        data = self.create().json()
        self.assertEqual(set(data), {'job_id', 'status', 'image', 'video', 'timing', 'quality_status', 'error'})
        self.assertEqual(data['timing'], {'elapsed_seconds': None, 'total_seconds': None, 'video_generation_seconds': None})
        self.assertIsNone(data['image'])
        self.assertIsNone(data['video'])

    def test_compact_result_hides_diagnostics_and_preserves_review_and_retry(self):
        from fabricapp.video.service import job_response
        job = self.job()
        job.status = 'completed'
        job.image = {'url': 'photo', 'format': 'png', 'public_id': 'private-photo-id', 'width': 100}
        job.video = {'url': 'clip', 'format': 'mp4', 'duration': 8, 'public_id': 'private-video-id',
                     'timing': {'download_seconds': 5}, 'continuity': {'status': 'review_required', 'samples': [1, 2]}}
        data = job_response(job)
        self.assertEqual(data['image'], {'url': 'photo', 'format': 'png'})
        self.assertEqual(data['video'], {'url': 'clip', 'format': 'mp4', 'duration': 8})
        self.assertEqual(data['quality_status'], 'needs_review')
        self.assertIn('samples', job.video['continuity'])
        job.status = 'failed'
        job.retryable = True
        job.error_code = 'provider_unavailable'
        job.error_message = 'Temporarily unavailable'
        job.provider_error = {'stage': 'generating', 'code': 'upstream_error'}
        self.assertEqual(job_response(job)['error'], {'code': 'provider_unavailable',
                         'message': 'Temporarily unavailable', 'retryable': True})

    def test_quality_failure_without_saved_provider_clip_cannot_resubmit(self):
        job=self.job()
        job.status='failed'
        job.error_code='video_continuity_failed'
        job.retryable=False
        job.save()
        response=self.client.get(f'/api/video-jobs/{job.pk}/',**self.auth)
        self.assertFalse(response.json()['error']['retryable'])
        self.assertEqual(self.client.post(f'/api/video-jobs/{job.pk}/retry/', {'wait': False},**self.auth).status_code,409)

    def test_video_keeps_all_valid_image_choices(self):
        for changes in ({'garment_type': 'saree'}, {'gender': 'boy'},
                        {'gender': 'girl'}, {'camera_view': 'close_up'},
                        {'camera_view': 'side'}, {'pose': 'pocket_walk'},
                        {'garment_type': 'kurta', 'garment_style': 'plain'},
                        {'garment_type': 'kurti_pant'}, {'garment_type': 'pant'},
                        {'garment_type': 'blazer', 'garment_style': 'business'}):
            with self.subTest(changes=changes):
                response = self.create(**changes)
                self.assertEqual(response.status_code, 202, response.content)

    def test_person_and_ready_garment_uploads_are_persisted(self):
        response = self.client.post('/api/generate-tryon-video/', {'wait': False,
            'person_image': SimpleUploadedFile('person.png', image_bytes(), 'image/png'),
            'garment_image': SimpleUploadedFile('outfit.png', image_bytes(), 'image/png'),
            'garment_type': 'shirt',
        }, **self.auth)
        self.assertEqual(response.status_code, 202, response.content)
        job = VideoJob.objects.get(pk=response.json()['job_id'])
        self.assertEqual(set(job.inputs), {'person_image', 'garment_image'})
        self.assertEqual(job.motion_profile['motion'], 'mirror_check')
        self.assertNotIn('person_image', job.payload)

    def test_existing_generated_photo_skips_image_generation(self):
        response = self.client.post('/api/animate-image/', {'wait': False,
            'source_image': SimpleUploadedFile('generated.png', image_bytes(), 'image/png'),
            'garment_type': 'saree', 'camera_view': 'close_up',
        }, **self.auth)
        self.assertEqual(response.status_code, 202, response.content)
        job = VideoJob.objects.get(pk=response.json()['job_id'])
        self.assertTrue(job.image_file)
        import hashlib
        self.assertEqual(job.payload['_video_source']['sha256'], hashlib.sha256(image_bytes()).hexdigest())
        self.assertEqual(job.motion_profile['motion'], 'walking')
        with patch('fabricapp.video.service.generate_image') as generate, \
             patch('fabricapp.video.service.upload_generated_image', return_value={'url': 'https://cdn.example/photo.png'}), \
             patch('fabricapp.video.service.GimmeclipClient') as provider, \
             patch('fabricapp.video.service.store_video', return_value={'url': 'https://cdn.example/video.mp4'}):
            provider.return_value.upload_photo.return_value = 'https://gimmeclip.com/api/v0/photos/' + 'a' * 32
            provider.return_value.submit.return_value = 'https://gimmeclip.com/api/v0/edits/' + 'b' * 64
            provider.return_value.poll.return_value = 'https://gimmeclip.com/api/v0/clips/' + 'c' * 64 + '/file'
            process_job(job)
        generate.assert_not_called()
        self.assertEqual(job.status, 'completed')

    def test_ready_garment_type_is_video_context_only_for_the_image_adapter(self):
        response = self.client.post('/api/generate-tryon-video/', {'wait': False,
            'person_image': SimpleUploadedFile('person.png', image_bytes(), 'image/png'),
            'garment_image': SimpleUploadedFile('outfit.png', image_bytes(), 'image/png'),
            'garment_type': 'pant',
        }, **self.auth)
        self.assertEqual(response.status_code, 202, response.content)
        job = VideoJob.objects.get(pk=response.json()['job_id'])
        with patch('fabricapp.video.service.generate_image', return_value=GenerationResult(image_bytes(), 7)) as generate, \
             patch('fabricapp.video.service.upload_generated_image', side_effect=RuntimeError('stop after generation')):
            process_job(job)
        self.assertNotIn('garment_type', generate.call_args.args[0])
        self.assertEqual(job.payload['garment_type'], 'pant')
        self.assertEqual(job.motion_profile['garment_type'], 'pant')

    def test_success_stores_both_urls_and_hides_internal_provider_details(self):
        job = self.job()
        with patch('fabricapp.video.service.generate_image', return_value=GenerationResult(image_bytes(), 7)) as generate, \
             patch('fabricapp.video.service.upload_generated_image', return_value={'url': 'https://res.cloudinary.com/test/image.png'}), \
             patch('fabricapp.video.service.GimmeclipClient') as provider, \
             patch('fabricapp.video.service.store_video', return_value={'url': 'https://res.cloudinary.com/test/video.mp4'}):
            provider.return_value.upload_photo.return_value = 'https://gimmeclip.com/api/v0/photos/' + 'a' * 32
            provider.return_value.submit.return_value = 'https://gimmeclip.com/api/v0/edits/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
            provider.return_value.poll.return_value = 'https://cdn.example/video.mp4'
            process_job(job)
        job.refresh_from_db()
        self.assertEqual(job.status, 'completed')
        self.assertEqual(generate.call_args.args[0]['camera_view'], 'front')
        self.assertTrue(job.image_file)
        response = self.client.get(f'/api/video-jobs/{job.pk}/', **self.auth)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['image']['url'])
        self.assertTrue(payload['video']['url'])
        self.assertIsNotNone(payload['timing']['total_seconds'])
        self.assertIsNotNone(payload['timing']['video_generation_seconds'])
        self.assertEqual(provider.return_value.upload_photo.call_args.args[0], image_bytes())
        self.assertEqual(provider.return_value.submit.call_args.args[0], job.source_photo_url)
        for key in ('inputs', 'payload', 'polling_url', 'provider_video_url'):
            self.assertNotIn(key, payload)

    def test_retry_resumes_same_provider_job_without_generating_or_submitting(self):
        job = self.job()
        job.image = {'url': 'https://res.cloudinary.com/test/image.png'}
        job.polling_url = 'https://gimmeclip.com/api/v0/edits/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
        job.status = 'failed'
        job.retryable = True
        job.save()
        response = self.client.post(f'/api/video-jobs/{job.pk}/retry/', {'wait': False}, **self.auth)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(self.client.post(f'/api/video-jobs/{job.pk}/retry/', {'wait': False}, **self.auth).status_code, 409)
        job.refresh_from_db()
        with patch('fabricapp.video.service.generate_image') as generate, \
             patch('fabricapp.video.service.GimmeclipClient') as provider, \
             patch('fabricapp.video.service.store_video', return_value={'url': 'https://cdn.example/final.mp4'}):
            provider.return_value.poll.return_value = 'https://cdn.example/video.mp4'
            process_job(job)
        generate.assert_not_called()
        provider.return_value.submit.assert_not_called()
        self.assertEqual(job.status, 'completed')

    def test_restart_during_submission_requires_reconciliation(self):
        job = self.job()
        job.status = 'video_submitting'
        job.save()
        with patch('fabricapp.video.service.GimmeclipClient') as provider:
            process_job(job)
        provider.assert_not_called()
        self.assertEqual(job.error_code, 'submission_unknown')
        self.assertFalse(job.retryable)
        self.assertEqual(self.client.post(f'/api/video-jobs/{job.pk}/retry/', {'wait': False}, **self.auth).status_code, 409)

    def test_storage_retry_reuses_completed_provider_output(self):
        job = self.job()
        job.image = {'url': 'https://res.cloudinary.com/test/image.png'}
        job.polling_url = 'https://gimmeclip.com/api/v0/edits/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
        job.provider_video_url = 'https://cdn.example/video.mp4'
        job.status = 'video_storing'
        job.save()
        with patch('fabricapp.video.service.GimmeclipClient') as provider, \
             patch('fabricapp.video.service.store_video', side_effect=VideoError('video_storage_failed', 'Storage unavailable', True)):
            process_job(job)
        provider.return_value.poll.assert_not_called()
        provider.return_value.submit.assert_not_called()
        self.assertEqual(job.status, 'failed')
        self.assertTrue(job.retryable)
        self.assertEqual(job.provider_video_url, 'https://cdn.example/video.mp4')

    def test_image_upload_retry_reuses_saved_generated_bytes(self):
        job = self.job()
        with patch('fabricapp.video.service.generate_image', return_value=GenerationResult(image_bytes(), 9)) as generate, \
             patch('fabricapp.video.service.upload_generated_image', side_effect=RuntimeError('Upload unavailable')):
            process_job(job)
        self.assertTrue(job.image_file)
        self.assertTrue(job.retryable)
        with patch('fabricapp.video.service.generate_image') as generate_again, \
             patch('fabricapp.video.service.upload_generated_image', return_value={'url': 'https://cdn.example/image.png'}), \
             patch('fabricapp.video.service.GimmeclipClient') as provider:
            provider.return_value.upload_photo.return_value = 'https://gimmeclip.com/api/v0/photos/' + 'a' * 32
            provider.return_value.submit.side_effect = VideoError('submission_unknown', 'Unknown')
            process_job(job)
        generate_again.assert_not_called()
        self.assertEqual(provider.return_value.upload_photo.call_args.args[0], image_bytes())
        self.assertTrue(job.source_photo_url)
        self.assertEqual(job.error_code, 'submission_unknown')
        self.assertFalse(job.retryable)

    @override_settings(VIDEO_POLL_TIMEOUT=0)
    def test_poll_timeout_keeps_the_provider_reference(self):
        job = self.job()
        job.image = {'url': 'https://cdn.example/image.png'}
        job.polling_url = 'https://gimmeclip.com/api/v0/edits/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
        job.save()
        process_job(job)
        self.assertEqual(job.error_code, 'poll_timeout')
        self.assertTrue(job.retryable)
        self.assertTrue(job.polling_url)

    def test_only_one_local_worker_can_hold_the_lock(self):
        with exclusive_worker():
            with self.assertRaises(CommandError):
                with exclusive_worker():
                    self.fail('Second worker acquired the lock')
        with exclusive_worker():
            pass

    def test_worker_once_recovers_interrupted_job(self):
        job = self.job()
        job.status = 'image_generating'
        job.save()
        with patch('fabricapp.management.commands.run_video_worker.process_job') as process:
            call_command('run_video_worker', once=True, stdout=io.StringIO())
        self.assertEqual(process.call_args.args[0].pk, job.pk)

    def test_legacy_provider_job_is_preserved_without_gimmeclip_calls(self):
        job = self.job()
        job.polling_url = 'https://gateway.pixazo.ai/v2/requests/status/old'
        job.save()
        with patch('fabricapp.video.service.GimmeclipClient') as provider:
            process_job(job)
        provider.assert_not_called()
        self.assertEqual(job.error_code, 'legacy_provider_job')
        self.assertFalse(job.retryable)
        self.assertIn('gateway.pixazo.ai', job.polling_url)

    def test_photo_upload_failure_is_retryable_before_video_submission(self):
        job = self.job()
        with patch('fabricapp.video.service.generate_image', return_value=GenerationResult(image_bytes(), 9)), \
             patch('fabricapp.video.service.upload_generated_image', return_value={'url': 'https://cdn.example/image.png'}), \
             patch('fabricapp.video.service.GimmeclipClient') as provider:
            provider.return_value.upload_photo.side_effect = VideoError('provider_unavailable', 'Upload unavailable', True)
            process_job(job)
        self.assertTrue(job.retryable)
        self.assertEqual(job.status, 'failed')
        provider.return_value.submit.assert_not_called()

    def test_submission_retry_reuses_uploaded_generated_photo(self):
        job = self.job()
        with patch('fabricapp.video.service.generate_image', return_value=GenerationResult(image_bytes(), 9)) as generate, \
             patch('fabricapp.video.service.upload_generated_image', return_value={'url': 'https://cdn.example/image.png'}), \
             patch('fabricapp.video.service.GimmeclipClient') as provider, \
             patch('fabricapp.video.service.store_video', return_value={'url': 'https://cdn.example/video.mp4'}):
            provider.return_value.upload_photo.return_value = 'https://gimmeclip.com/api/v0/photos/' + 'a' * 32
            provider.return_value.submit.side_effect = VideoError('quota_exceeded', 'Quota exhausted', True)
            process_job(job)
            self.assertTrue(job.retryable)
            self.assertTrue(job.source_photo_url)
            response = self.client.post(f'/api/video-jobs/{job.pk}/retry/', {'wait': False}, **self.auth)
            self.assertEqual(response.status_code, 202)
            job.refresh_from_db()
            provider.return_value.submit.side_effect = None
            provider.return_value.submit.return_value = 'https://gimmeclip.com/api/v0/edits/' + 'b' * 64
            provider.return_value.poll.return_value = 'https://gimmeclip.com/api/v0/clips/' + 'c' * 64 + '/file'
            process_job(job)
            self.assertEqual(job.status, 'completed')
            self.assertEqual(generate.call_count, 1)
            self.assertEqual(provider.return_value.upload_photo.call_count, 1)

    def test_worker_preserves_image_settings_and_saved_motion(self):
        response = self.create(garment_type='kurta', garment_style='plain', fabric_type='silk',
                               face_choice='raghav', body_type='plus', camera_view='close_up',
                               seed=19, guidance=4.5, additional_style_note='Keep the selected fabric',
                               options='{"draft_mode": false, "fabric_crop_box": [0, 0, 32, 64]}')
        self.assertEqual(response.status_code,202,response.content)
        job = VideoJob.objects.get(pk=response.json()['job_id'])
        profile = dict(job.motion_profile)
        self.assertEqual(profile['motion'],'mirror_check')
        with patch('fabricapp.video.service.generate_image', return_value=GenerationResult(image_bytes(),19)) as generate, \
             patch('fabricapp.video.service.upload_generated_image', return_value={'url':'https://cdn.example/photo.png'}), \
             patch('fabricapp.video.service.select_profile', side_effect=AssertionError('Do not change saved motion')), \
             patch('fabricapp.video.service.GimmeclipClient') as provider, \
             patch('fabricapp.video.service.store_video', return_value={'url':'https://cdn.example/video.mp4'}):
            provider.return_value.upload_photo.return_value='https://gimmeclip.com/api/v0/photos/'+'a'*32
            provider.return_value.submit.return_value='https://gimmeclip.com/api/v0/edits/'+'b'*64
            provider.return_value.poll.return_value='https://gimmeclip.com/api/v0/clips/'+'c'*64+'/file'
            process_job(job)
        data=generate.call_args.args[0]
        for key,value in {'garment_type':'kurta','garment_style':'plain','fabric_type':'silk',
                          'face_choice':'raghav','body_type':'plus','camera_view':'close_up','seed':19,'guidance':4.5}.items():
            self.assertEqual(data[key],value)
        self.assertEqual(data['options'],{'draft_mode':False,'fabric_crop_box':[0,0,32,64]})
        self.assertEqual(provider.return_value.submit.call_args.args[1],profile)
        self.assertEqual(job.status,'completed')

    def test_legacy_motion_choices_do_not_override_the_fixed_mirror_flow(self):
        for previous_choice in ('auto', 'turn', 'subtle'):
            with self.subTest(previous_choice=previous_choice):
                response = self.create(motion=previous_choice)
                self.assertEqual(response.status_code,202,response.content)
                job = VideoJob.objects.get(pk=response.json()['job_id'])
                self.assertEqual(job.motion_profile['motion'],'mirror_check')
                self.assertNotIn('motion',job.payload)

    def test_walking_motion_is_explicit_and_saved_without_changing_image_inputs(self):
        from fabricapp.video.garments.shirt_prompts import PROMPT, WALKING_PROMPT
        default=self.job()
        self.assertEqual(default.motion_profile['prompt'],PROMPT)
        response=self.create(video_motion='walking')
        self.assertEqual(response.status_code,202,response.content)
        walking=VideoJob.objects.get(pk=response.json()['job_id'])
        self.assertEqual(walking.motion_profile['motion'],'walking')
        self.assertEqual(walking.motion_profile['prompt'],WALKING_PROMPT)
        self.assertEqual(walking.motion_profile['seconds'],8)
        self.assertNotIn('video_motion',walking.payload)
        self.assertEqual(walking.payload,default.payload)
        self.assertEqual(self.create(video_motion='unsupported').status_code,400)

    def test_existing_photo_can_use_walking_and_rejects_unknown_motion(self):
        data={'wait':False, 'source_image':SimpleUploadedFile('photo.png',image_bytes(),'image/png'),
              'video_motion':'walking','garment_type':'shirt'}
        response=self.client.post('/api/animate-image/',data,**self.auth)
        self.assertEqual(response.status_code,202,response.content)
        job=VideoJob.objects.get(pk=response.json()['job_id'])
        self.assertEqual(job.motion_profile['motion'],'walking')
        self.assertTrue(job.image_file)
        data['source_image']=SimpleUploadedFile('photo.png',image_bytes(),'image/png')
        data['video_motion']='unknown'
        self.assertEqual(self.client.post('/api/animate-image/',data,**self.auth).status_code,400)

    def test_commercial_is_shirt_only_and_keeps_the_four_shot_profile(self):
        response=self.create(video_motion='shirt_commercial')
        self.assertEqual(response.status_code,202,response.content)
        job=VideoJob.objects.get(pk=response.json()['job_id'])
        self.assertEqual(job.motion_profile['version'],'fabric-gimme-shirt-commercial-v7')
        self.assertNotIn('provider',job.motion_profile)
        self.assertLessEqual(len(job.motion_profile['prompt']),300)
        self.assertTrue(job.motion_profile['multi_shot'])
        self.assertTrue(job.motion_profile['source_collar_opening'])
        self.assertEqual(job.motion_profile['seconds'],8)
        self.assertNotIn('video_motion',job.payload)
        self.assertEqual(self.create(video_motion='shirt_commercial',garment_type='pant').status_code,400)
        response=self.client.post('/api/animate-image/',{
            'wait':False, 'source_image':SimpleUploadedFile('photo.png',image_bytes(),'image/png'),
            'garment_type':'pant','video_motion':'shirt_commercial'},**self.auth)
        self.assertEqual(response.status_code,400)
