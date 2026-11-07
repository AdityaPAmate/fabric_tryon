"""Verify selected product pixels reach the real provider request, without paid calls."""
import io
import json
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from rest_framework import serializers
from fabricapp.catalog_engine.registry import get_definition
from fabricapp.serializers import FabricTryOnRequestSerializer
from fabricapp.test_catalog_engine import data, picture, post


class SareeCatalogRegionTests(SimpleTestCase):
    def test_body_and_border_have_distinct_tasks_and_crop_precedence(self):
        definition = get_definition('saree')
        request = data(options={'fabric_crop_box': [0, 0, 40, 80]})
        configs = {s.key: definition.build_config(request, s, 42)
                   for s in definition.shots if s.key in ('fabric_texture', 'border')}
        self.assertEqual(configs['fabric_texture']['fabric_crop_box'], [0, 0, 40, 80])
        self.assertIsNone(configs['border']['fabric_crop_box'])
        self.assertIn('MAIN BODY FABRIC', configs['fabric_texture']['prompt'])
        self.assertIn('not the main body print', configs['border']['prompt'])
        self.assertNotEqual(configs['fabric_texture']['prompt_version'], configs['border']['prompt_version'])
        self.assertEqual(request['options'], {'fabric_crop_box': [0, 0, 40, 80]})

    def test_reject_bad_or_out_of_bounds_regions_before_generation(self):
        for box in ([True, 0, 20, 20], [0, 0, 0, 20], [0, 0, 97, 128], [0, 0, 96, 129], '0,0,20,20'):
            with self.subTest(box=box), patch('fabricapp.catalog.generate_edit') as edit:
                response = post(options=json.dumps({'fabric_border_crop_box': box}))
                self.assertEqual(response.status_code, 400)
                edit.assert_not_called()

    def test_crop_options_are_catalog_saree_only(self):
        with self.assertRaises(serializers.ValidationError):
            FabricTryOnRequestSerializer().validate_options({'fabric_body_crop_box': [0, 0, 20, 20]})
        response = post(garment_type='shirt', gender='men',
                        options=json.dumps({'fabric_body_crop_box': [0, 0, 20, 20]}))
        self.assertEqual(response.status_code, 400)

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.test/a.png'})
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_actual_request_crops_body_and_border_pixels_independently(self, provider, upload):
        source = Image.new('RGB', (96, 128), 'red')
        source.paste('blue', (64, 0, 96, 128))
        buffer = io.BytesIO()
        source.save(buffer, 'PNG')
        seen = []
        def answer(url, **kwargs):
            image = Image.open(kwargs['files']['input_image_1'][1])
            seen.append(image.convert('RGB').getpixel((image.width//2, image.height//2)))
            fields = kwargs['data']
            return Mock(status_code=200, headers={'Content-Type': 'image/png'},
                        content=picture(size=(fields['width'], fields['height'])))
        provider.side_effect = answer
        with patch('django.conf.settings.SAVE_DEBUG_FILES', False):
            response = post(fabric_image=SimpleUploadedFile('regions.png', buffer.getvalue(), content_type='image/png'),
                options=json.dumps({'draft_mode': True, 'fabric_crop_box': [0, 0, 32, 128],
                    'fabric_body_crop_box': [0, 0, 64, 128], 'fabric_border_crop_box': [64, 0, 96, 128]}))
            events = [json.loads(chunk) for chunk in response.streaming_content]
            response.close()
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(len(seen), 6)
        self.assertEqual(seen[3], (255, 0, 0))
        self.assertEqual(seen[4], (0, 0, 255))
        border = next(e['image'] for e in events if e['event'] == 'image_ready' and e['image']['view'] == 'border')
        self.assertEqual(border['generation']['fabric_crop_box'], [64, 0, 96, 128])
        self.assertEqual(border['generation']['fabric_region'], 'border')
