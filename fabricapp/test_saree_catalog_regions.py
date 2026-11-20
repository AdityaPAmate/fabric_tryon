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
    def test_front_keeps_full_product_and_separately_exposes_body_fabric(self):
        definition = get_definition('saree')
        shot = next(s for s in definition.shots if s.key == 'front')
        for identity in (None, 'poonam'):
            request = data(face_choice=identity, options={'fabric_crop_box': [0, 0, 64, 100]})
            config = definition.build_config(request, shot, 42)
            self.assertIsNone(config['fabric_crop_box'])
            self.assertEqual(config['fabric_reference_crops'], {'saree_body': [0, 0, 64, 100]})
            self.assertIn(f'Image {3 if identity else 2} is an enlarged source BODY', config['prompt'])
            self.assertIn('ALL recessed lower pleats', config['prompt'])
            self.assertIn('Preserve white or pale motifs ONLY', config['prompt'])
            self.assertEqual(request['options']['fabric_crop_box'], [0, 0, 64, 100])

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.test/a.png'})
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_face_and_border_have_separate_slots_and_back_receives_no_identity(self, provider, upload):
        source = Image.new('RGB', (96, 128), 'red')
        source.paste('blue', (64, 0, 96, 128))
        buffer = io.BytesIO()
        source.save(buffer, 'PNG')
        captured = {}
        def reply(url, **kwargs):
            files, fields = kwargs['files'], kwargs['data']
            role = 'side' if 'FINAL POSE:' in fields['prompt'] else 'back' if 'FINAL REAR GEOMETRY:' in fields['prompt'] else 'front'
            captured[role] = {key: value[1].getvalue() for key, value in files.items()}
            return Mock(status_code=200, headers={'Content-Type': 'image/png'},
                        content=picture(size=(fields['width'], fields['height'])))
        provider.side_effect = reply
        with patch('django.conf.settings.SAVE_DEBUG_FILES', False):
            response = post(face_choice='poonam', options=json.dumps({'draft_mode': True,
                'fabric_body_crop_box': [0, 0, 64, 128], 'fabric_border_crop_box': [64, 0, 96, 128]}),
                fabric_image=SimpleUploadedFile('cloth.png', buffer.getvalue(), 'image/png'))
            events = [json.loads(chunk) for chunk in response.streaming_content]
            response.close()
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(len(captured), 3)
        self.assertEqual(set(captured['side']), {'input_image_0', 'input_image_1', 'input_image_2', 'input_image_3'})
        with Image.open(io.BytesIO(captured['side']['input_image_3'])) as border:
            self.assertEqual(border.getpixel((border.width-1, border.height//2)), (0, 0, 255))
        self.assertEqual(set(captured['back']), {'input_image_0', 'input_image_1'})

    def test_body_and_border_have_distinct_tasks_and_crop_precedence(self):
        definition = get_definition('saree')
        request = data(options={'fabric_crop_box': [0, 0, 40, 80]})
        configs = {s.key: definition.build_config(request, s, 42)
                   for s in definition.shots if s.key in ('fabric_texture', 'border')}
        self.assertIsNone(configs['fabric_texture']['fabric_crop_box'])
        self.assertNotIn('fabric_crop_box', configs['border'])
        self.assertIn('COMPLETE SAREE FLAT-LAY', configs['fabric_texture']['prompt'])
        self.assertIn('BOTH long side borders', configs['fabric_texture']['prompt'])
        self.assertEqual(configs['fabric_texture']['fabric_region'], 'full_saree')
        self.assertNotIn('prompt', configs['border'])
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
        product_references = []
        def answer(url, **kwargs):
            image = Image.open(io.BytesIO(kwargs['files']['input_image_1'][1].getvalue()))
            seen.append(image.convert('RGB').getpixel((image.width//2, image.height//2)))
            if 'FINAL POSE:' in kwargs['data']['prompt']:
                extra = Image.open(io.BytesIO(kwargs['files']['input_image_2'][1].getvalue()))
                product_references.append(extra.convert('RGB').getpixel((extra.width-1, extra.height//2)))
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
        self.assertEqual(len(seen), 3)

        self.assertEqual(product_references, [(0, 0, 255)])
        border = next(e['image'] for e in events if e['event'] == 'image_ready' and e['image']['view'] == 'border')
        self.assertEqual(border['generation']['kind'], 'derived_crop')
        self.assertEqual(border['generation']['source_view'], 'front')
        self.assertTrue(border['generation']['no_new_ai_generation'])
        pleats = next(e['image'] for e in events if e['event'] == 'image_ready' and e['image']['view'] == 'pleats')
        self.assertEqual(pleats['generation']['kind'], 'derived_crop')
        self.assertEqual(pleats['generation']['source_view'], 'front')
        self.assertTrue(pleats['generation']['no_new_ai_generation'])
