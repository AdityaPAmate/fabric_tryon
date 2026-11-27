"""Video-only contracts and recovery; never call paid providers."""
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from unittest.mock import patch
from importlib import import_module
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from fabricapp.models import VideoJob
from fabricapp.test_video_jobs import image_bytes
from django.core.files.uploadedfile import SimpleUploadedFile
from fabricapp.video.registry import GARMENT_MODULES, get_definition, select_profile
from fabricapp.video.rendering import preflight, render
from fabricapp.video.service import fail_stale_preparing, timing_response, process_job


class VideoRegistryTests(SimpleTestCase):
    def test_each_garment_is_independent_and_style_count_is_bounded(self):
        self.assertEqual(set(GARMENT_MODULES), {'shirt', 'saree', 'kurta', 'kurti_pant', 'pant', 'blazer'})
        profiles = []
        for garment in GARMENT_MODULES:
            definition = get_definition(garment)
            with self.subTest(garment=garment):
                self.assertLessEqual(len(definition.styles), 2)
                self.assertTrue(definition.resolve())
                for style in definition.all_styles:
                    profile = select_profile({'garment_type': garment, 'video_motion': style.id})
                    self.assertEqual(profile['garment_type'], garment)
                    self.assertLessEqual(len(profile['prompt']), 300)
                    if garment != 'shirt':
                        self.assertEqual(profile['renderer'], 'passthrough')
                        self.assertNotIn('source_collar_opening', profile)
                profiles.append(definition.resolve().prompt)
        self.assertEqual(len(set(profiles)), 6)
        self.assertEqual([s.id for s in get_definition('shirt').all_styles],
                         ['mirror_check', 'walking', 'shirt_commercial'])

    def test_kurta_has_one_independent_cinematic_style_with_full_hem_framing(self):
        kurta = get_definition('kurta')
        shirt = get_definition('shirt')
        self.assertEqual([s.id for s in kurta.all_styles], ['kurta_commercial'])
        self.assertNotEqual(kurta.resolve().prompt, shirt.resolve('mirror_check').prompt)
        self.assertNotEqual(kurta.resolve().prompt, shirt.resolve('shirt_commercial').prompt)
        for phrase in ('Single take.', '0-2s chest fabric close-up', '2-4s pull back', 'turn only 30deg, front visible',
                       '4-6s two slow forward steps', 'camera backs in sync', '6-8s hold front pose',
                       'Full kurta/hem after reveal', 'print scale', 'No back view'):
            self.assertIn(phrase, kurta.resolve().prompt)
        self.assertEqual(kurta.resolve().seconds, 8)
        with self.assertRaises(ValueError):
            kurta.resolve('walking')
        saved = select_profile({'garment_type': 'kurta'})
        self.assertNotIn('multi_shot', saved)
        self.assertEqual(saved['camera_motion'], 'zoom_out')
        self.assertEqual(saved['renderer'], 'passthrough')
        self.assertNotIn('source_collar_opening', saved)
        changed = replace(shirt, styles=(replace(shirt.styles[0], prompt='A different shirt action'), shirt.styles[1]))
        with patch('fabricapp.video.garments.shirt.DEFINITION', changed):
            self.assertEqual(select_profile({'garment_type': 'kurta'}), saved)

    def test_limits_and_cross_garment_styles_fail_without_fallback(self):
        shirt = get_definition('shirt')
        with self.assertRaises(ValueError):
            replace(shirt, styles=shirt.all_styles)
        with self.assertRaises(ValueError):
            replace(shirt, garment_type='pant')
        for data in ({}, {'garment_type': 'unknown'},
                     {'garment_type': 'saree', 'video_motion': 'shirt_commercial'},
                     {'garment_type': 'shirt', 'video_motion': 'unknown'}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                select_profile(data)

    def test_definition_changes_cannot_mutate_other_or_saved_plans(self):
        shirt = get_definition('shirt')
        saved = select_profile({'garment_type': 'shirt'})
        pant = select_profile({'garment_type': 'pant'})
        with self.assertRaises(FrozenInstanceError):
            shirt.styles[0].prompt = 'Changed'
        changed = replace(shirt, styles=(replace(shirt.styles[0], prompt='Different shirt motion'), shirt.styles[1]))
        with patch('fabricapp.video.garments.shirt.DEFINITION', changed):
            self.assertNotEqual(select_profile({'garment_type': 'shirt'}), saved)
            self.assertEqual(select_profile({'garment_type': 'pant'}), pant)
        self.assertEqual(saved, select_profile({'garment_type': 'shirt'}))

    def test_non_shirt_render_never_needs_a_face_or_ffmpeg(self):
        profile = select_profile({'garment_type': 'pant'})
        with patch('fabricapp.video.collar.prepare_collar') as crop, \
             patch('fabricapp.video.collar.ffmpeg_path') as ffmpeg:
            preflight(profile, b'no face is needed')
            self.assertEqual(render(profile, 'raw.mp4', None, '/tmp'), ('raw.mp4', None))
        crop.assert_not_called()
        ffmpeg.assert_not_called()

    def test_options_are_public_metadata_without_provider_calls(self):
        with patch('fabricapp.video.service.GimmeclipClient') as provider:
            for garment in GARMENT_MODULES:
                definition = get_definition(garment)
                response = self.client.get('/api/video-options/', {'garment_type': garment})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), definition.options())
                self.assertNotIn('prompt', str(response.json()))
            self.assertEqual(self.client.get('/api/video-options/').status_code, 400)
        provider.assert_not_called()

    def test_broken_garment_configuration_is_isolated_from_other_routes(self):
        def load(module):
            if module == GARMENT_MODULES['saree']:
                raise ValueError('Invalid saree prompt configuration')
            return import_module(module)
        with patch('fabricapp.video.registry.import_module', side_effect=load):
            self.assertEqual(self.client.get('/api/video-options/', {'garment_type': 'saree'}).status_code, 503)
            self.assertEqual(self.client.get('/api/video-options/', {'garment_type': 'shirt'}).status_code, 200)
            self.assertEqual(self.client.get('/api/health/').status_code, 200)
            # The unchanged image/catalog validators still handle these requests.
            self.assertEqual(self.client.post('/api/replace-fabric/', {}).status_code, 400)
            self.assertEqual(self.client.post('/api/generate-catalog/', {}).status_code, 400)


@override_settings(GIMMECLIP_API_KEY='test-key', VIDEO_API_TOKEN='test-token')
class VideoArchitectureTests(TestCase):
    def test_all_kurta_image_styles_use_the_same_video_plan(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        plans = []
        with TemporaryDirectory(dir=Path.cwd()) as directory, override_settings(MEDIA_ROOT=Path(directory)):
            for style in ('plain', 'sherwani', 'pathani', 'jodhpuri'):
                response = self.client.post('/api/generate-tryon-video/', {
                    'fabric_image': SimpleUploadedFile('fabric.png', image_bytes(), 'image/png'),
                    'garment_type': 'kurta', 'garment_style': style, 'gender': 'men', 'wait': False})
                self.assertEqual(response.status_code, 202, response.content)
                job = VideoJob.objects.get(pk=response.json()['job_id'])
                self.assertEqual(job.payload['garment_style'], style)
                plans.append(job.motion_profile)
        self.assertTrue(all(plan == plans[0] for plan in plans))

    def test_missing_type_is_rejected_before_any_image_or_provider_work(self):
        with patch('fabricapp.video.service.generate_image') as generate, \
             patch('fabricapp.video.service.GimmeclipClient') as provider:
            response = self.client.post('/api/animate-image/', {
                'source_image': SimpleUploadedFile('source.png', image_bytes(), 'image/png'),
                'video_motion': 'shirt_commercial'}, HTTP_AUTHORIZATION='Bearer test-token')
        self.assertEqual(response.status_code, 400)
        self.assertIn('garment_type', response.json())
        self.assertEqual(VideoJob.objects.count(), 0)
        generate.assert_not_called()
        provider.assert_not_called()

    def test_stale_preparing_fails_but_active_input_saving_and_queued_jobs_are_preserved(self):
        stale = VideoJob.objects.create(status='preparing', profile_version='test')
        fresh = VideoJob.objects.create(status='preparing', profile_version='test')
        queued = VideoJob.objects.create(status='queued', profile_version='test')
        VideoJob.objects.filter(pk__in=[stale.pk, queued.pk]).update(updated_at=timezone.now()-timedelta(hours=2))
        self.assertEqual(fail_stale_preparing(), 1)
        stale.refresh_from_db(); fresh.refresh_from_db(); queued.refresh_from_db()
        self.assertEqual(stale.error_code, 'inputs_incomplete')
        self.assertFalse(stale.retryable)
        self.assertEqual(fresh.status, 'preparing')
        self.assertEqual(queued.status, 'queued')

    def test_legacy_saved_plan_never_reselects_current_garment_profile(self):
        profile = {'motion': 'mirror_check', 'version': 'old-version', 'seconds': 8, 'prompt': 'Old saved motion'}
        job = VideoJob.objects.create(status='video_storing', image={'url': 'image'},
             provider_video_url='saved-clip', profile_version='old-version', motion_profile=profile)
        with patch('fabricapp.video.service.select_profile', side_effect=AssertionError('Must use saved plan')), \
             patch('fabricapp.video.service.GimmeclipClient') as provider, \
             patch('fabricapp.video.service.store_video', return_value={'url': 'final'}) as store:
            process_job(job)
        provider.return_value.submit.assert_not_called()
        self.assertEqual(store.call_args.kwargs['profile'], profile)
        self.assertEqual(job.status, 'completed')

    def test_timing_distinguishes_queue_provider_postprocessing_and_total(self):
        job = VideoJob.objects.create(profile_version='test', status='completed')
        created = job.created_at.timestamp()
        job.timing = {'started_at':created+4,'video_submitted_at':created+10,
                      'video_ready_at':created+90,'completed_at':created+100,
                      'download_seconds':2,'render_seconds':3,'final_upload_seconds':4}
        result = timing_response(job)
        self.assertEqual(result['queue_wait_seconds'],4)
        self.assertEqual(result['video_generation_seconds'],80)
        self.assertEqual(result['post_generation_seconds'],10)
        self.assertEqual(result['request_to_ready_seconds'],100)
        self.assertEqual(result['final_upload_seconds'],4)
