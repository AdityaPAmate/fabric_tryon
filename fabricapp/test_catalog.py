import io
import json
import threading
from unittest.mock import patch

from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from .ai.cloudflare_engine import GenerationResult, CloudflareGenerationError
from .catalog import generate_catalog, catalog_plan, edit_config, CATALOG_SLOTS


def picture():
    out = io.BytesIO()
    Image.new('RGB', (64, 96), '#822330').save(out, 'PNG')
    return out.getvalue()


class CatalogTests(SimpleTestCase):
    def data(self):
        return {'garment_type': 'shirt', 'gender': 'men', 'fabric_type': 'velvet',
                'fabric_image': io.BytesIO(picture()), 'options': {'draft_mode': True}}

    def test_plan_for_every_garment(self):
        for garment in ('shirt', 'blazer', 'kurta', 'kurti_pant', 'pant', 'saree'):
            plan = catalog_plan(garment)
            self.assertEqual(len(plan), 6)
            self.assertEqual(len({key for key, _ in plan}), 6)
            self.assertEqual([key for key, _ in plan[:3]], ['front', 'three_quarter', 'back'])
        self.assertEqual([key for key, _ in catalog_plan('pant')[3:]], ['waistband', 'pocket', 'hem'])

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/photo.png'})
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 42))
    @patch('fabricapp.catalog.generate_tryon_image', return_value=GenerationResult(picture(), 42))
    def test_single_request_streams_six_images(self, front, edit, upload):
        response = APIClient().post('/api/generate-catalog/', {
            'fabric_image': SimpleUploadedFile('swatch.png', picture(), content_type='image/png'),
            'garment_type': 'shirt', 'gender': 'men', 'fabric_type': 'velvet',
        }, format='multipart')
        self.assertEqual(response.status_code, 200)
        events = [json.loads(chunk) for chunk in response.streaming_content]
        response.close()
        self.assertEqual([e['image']['view'] for e in events if e['event'] == 'image_ready'],
                         ['front', 'three_quarter', 'back', 'collar', 'cuff', 'hem'])
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(events[0]['catalog_id'], events[-1]['catalog_id'])
        self.assertTrue(events[0]['catalog_id'])
        self.assertTrue(all(event['image']['generation_seed'] == 42
                            for event in events if event['event'] == 'image_ready'))
        self.assertEqual(front.call_count, 1)
        self.assertEqual(edit.call_count, 5)
        self.assertEqual(upload.call_count, 6)
        self.assertFalse(front.call_args.kwargs['options']['draft_mode'])
        for call in edit.call_args_list:
            self.assertEqual(call.kwargs['person_image'].getvalue(), picture())
            self.assertEqual(call.kwargs['scenario'], 'person_photo')
            self.assertIn('SAME person', call.kwargs['prompt_config']['prompt'])
            self.assertIn('velvet', call.kwargs['prompt_config']['prompt'])

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/photo.png'})
    @patch('fabricapp.catalog.generate_edit')
    @patch('fabricapp.catalog.generate_tryon_image', return_value=GenerationResult(picture(), 42))
    def test_failed_detail_does_not_discard_other_images(self, front, edit, upload):
        edit.side_effect = [GenerationResult(picture(), 42), CloudflareGenerationError('rejected'),
                            *[GenerationResult(picture(), 42)] * 3]
        events = list(generate_catalog(self.data(), threading.Event()))
        self.assertEqual(events[-1]['status'], 'partial')
        self.assertEqual(events[-1]['failed_views'], ['back'])
        self.assertEqual(len(events[-1]['images']), 5)

    @patch('fabricapp.catalog.generate_edit')
    @patch('fabricapp.catalog.generate_tryon_image', side_effect=CloudflareGenerationError('quota', status_code=429))
    def test_quota_stops_further_provider_calls(self, front, edit):
        events = list(generate_catalog(self.data(), threading.Event()))
        self.assertEqual(events[-1]['status'], 'failed')
        self.assertEqual(len(events[-1]['failed_views']), 6)
        edit.assert_not_called()

    @patch('fabricapp.catalog.generate_tryon_image')
    def test_cancel_before_start(self, front):
        stop = threading.Event()
        stop.set()
        list(generate_catalog(self.data(), stop))
        front.assert_not_called()

    @patch('fabricapp.catalog.generate_tryon_image')
    def test_validation_before_generation(self, front):
        for extras in ({'camera_view': 'front'}, {'pose': 'invalid'}, {'fabric_type': 'wool'}):
            response = APIClient().post('/api/generate-catalog/', {
                'fabric_image': SimpleUploadedFile('fabric.png', picture(), content_type='image/png'),
                'garment_type': 'shirt', 'gender': 'men', **extras,
            }, format='multipart')
            self.assertEqual(response.status_code, 400)
        front.assert_not_called()

    def test_busy_response(self):
        self.assertTrue(CATALOG_SLOTS.acquire(blocking=False))
        try:
            response = APIClient().post('/api/generate-catalog/', {
                'fabric_image': SimpleUploadedFile('fabric.png', picture(), content_type='image/png'),
                'garment_type': 'shirt', 'gender': 'men',
            }, format='multipart')
            self.assertEqual(response.status_code, 429)
        finally:
            CATALOG_SLOTS.release()

    def test_page_and_targeted_detail_prompt(self):
        response = APIClient().get('/api/catalog/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Generate Catalog')
        config = edit_config(self.data(), catalog_plan('shirt')[3][1], 43)
        self.assertIn('extreme close-up', config['prompt'])
        self.assertNotIn('shown fully from head to feet', config['prompt'])
        self.assertEqual(config['seed'], 43)
