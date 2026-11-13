import io
import json
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from rest_framework.test import APIClient

from fabricapp.test_catalog import picture


class PlainKurtaCatalogTests(SimpleTestCase):
    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/shot.png'})
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_both_sources_generate_all_six_reference_views(self, post, upload):
        views = ['front', 'side', 'back', 'collar', 'cuff', 'side_slit']
        for source in ('fabric_image', 'garment_image'):
            with self.subTest(source=source):
                requests = []

                def provider(*args, **kwargs):
                    params, files = kwargs['data'], kwargs['files']
                    requests.append((params, files['input_image_1'][1].read(), set(files), files['input_image_1'][2]))
                    result = io.BytesIO()
                    Image.new('RGB', (params['width'], params['height']), 'blue').save(result, 'PNG')
                    return Mock(status_code=200, headers={'Content-Type': 'image/png'}, content=result.getvalue())

                post.side_effect = provider
                options = {'draft_mode': True}
                fields = {'gender': 'men', 'body_type': 'plus', 'face_choice': 'raghav'}
                if source == 'fabric_image':
                    fields.update(fabric_type='cotton', garment_details=['folded_sleeves', 'with_dupatta'])
                    options['fabric_crop_box'] = [0, 0, 32, 48]
                else:
                    fields = {'person_image': SimpleUploadedFile('person.png', picture(), 'image/png')}
                response = APIClient().post('/api/generate-catalog/', {
                    source: SimpleUploadedFile('source.png', picture(), 'image/png'),
                    'garment_type': 'kurta', 'garment_style': 'plain', 'seed': 73, 'guidance': 5.5,
                    'background': 'royal_courtyard', 'additional_style_note': 'simple shoes',
                    'options': json.dumps(options), **fields,
                }, format='multipart')
                self.assertEqual(response.status_code, 200, getattr(response, 'data', None))
                events = [json.loads(line) for line in response.streaming_content]
                self.assertEqual(events[0]['catalog_edition'], 'plain-v1')
                self.assertEqual(events[-1]['status'], 'completed')
                collage = events[-1]['collage']
                self.assertEqual(collage['source_views'], views)
                self.assertEqual(collage['aspect_ratio'], '3:4')
                self.assertEqual(len(requests), 6)
                self.assertTrue(all(row[1] == requests[0][1] for row in requests))
                self.assertTrue(requests[0][1])
                for index, (params, _, files, mime) in enumerate(requests):
                    self.assertEqual(int(params['seed']), 73)
                    self.assertEqual(float(params['guidance']), 5.5)
                    self.assertEqual('input_image_2' in files, index < 2)
                    self.assertEqual(max(params['width'], params['height']), 768)
                    if index < 3:
                        self.assertIn('palace courtyard', params['prompt'])
                        self.assertIn('simple shoes', params['prompt'])
                    if source == 'fabric_image':
                        self.assertEqual(mime, 'image/png')
                        self.assertIn('cotton', params['prompt'].lower())
                    else:
                        self.assertEqual(mime, 'image/jpeg')
                        self.assertIn('finished kurta', params['prompt'])
                if source == 'fabric_image':
                    self.assertIn('plus-size', requests[0][0]['prompt'])
                    self.assertIn('dupatt', requests[0][0]['prompt'].lower())
                    self.assertIn('folded back', requests[4][0]['prompt'])
                else:
                    self.assertIn('face, hairstyle and body build', requests[0][0]['prompt'])

        self.assertEqual(upload.call_count, 14)

    def test_other_styles_keep_classic_and_cannot_select_plain_edition(self):
        from fabricapp.catalog_engine.registry import get_request_definition

        for style in ('pathani', 'jodhpuri', 'sherwani'):
            data = {'garment_type': 'kurta', 'garment_style': style}
            self.assertEqual(get_request_definition(data).edition, 'classic-v1')
            with self.assertRaises(ValueError):
                get_request_definition({**data, 'catalog_edition': 'plain-v1'})
            with self.assertRaises(ValueError):
                get_request_definition({**data, 'garment_image': object()})
