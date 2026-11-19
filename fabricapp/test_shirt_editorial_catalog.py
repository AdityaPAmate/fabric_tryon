"""Verify the Shirt reference layout through the catalog HTTP entry point."""
import io
import json
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from fabricapp.ai.garments.shirt.catalog.editorial import DEFINITION, build_config
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.validation import validate_definition


def image_bytes(size=(96, 128)):
    image = Image.new('RGB', size, '#315b7d')
    image.paste('#c3b85e', (0, 0, max(1, size[0] // 4), size[1]))
    output = io.BytesIO()
    image.save(output, 'PNG')
    return output.getvalue()


def request_catalog():
    return APIClient().post('/api/generate-catalog/', {
        'fabric_image': SimpleUploadedFile('fabric.png', image_bytes(), 'image/png'),
        'garment_type': 'shirt', 'gender': 'men', 'body_type': 'trim',
        'face_choice': 'raghav', 'guidance': 6, 'seed': 71,
        'background': 'royal_courtyard',
    }, format='multipart')


class ShirtEditorialCatalogTests(SimpleTestCase):
    def test_detail_edits_stay_local_and_selected_options_replace_reference_treatments(self):
        def config(view, details=()):
            data = {'fabric_image': io.BytesIO(image_bytes()), 'garment_type': 'shirt',
                    'garment_details': details, 'options': {}}
            shot = next(shot for shot in DEFINITION.shots if shot.key == view)
            return build_config(data, shot, 71)['prompt']

        cuff = config('cuff')
        self.assertIn('isolated wrist-level close-up', cuff)
        self.assertNotIn('collar', cuff)
        self.assertNotIn('hem', cuff)
        self.assertNotIn('trousers', cuff)
        self.assertNotIn('Image 2', cuff)
        folded = config('cuff', ['folded_sleeves'])
        self.assertIn('rolled fabric cuff', folded)
        self.assertNotIn('broad horizontal buttoned cuff', folded)
        tucked = config('hem', ['tucked'])
        self.assertIn('bottom hem concealed', tucked)
        self.assertNotIn('curved stitched hem', tucked)
        front = config('front')
        self.assertIn('covers both forearms continuously down to the wrists', front)
        self.assertNotIn('covers both forearms continuously down to the wrists',
                         config('front', ['folded_sleeves']))

    def test_all_views_measure_the_requested_fabric_crop_without_a_named_colour_override(self):
        for rgb in ('#233d7b', '#8d2463', '#71811e'):
            # The contrasting half lies outside the crop and must never anchor colour.
            source = Image.new('RGB', (96, 128), '#f5ca26')
            source.paste(rgb, (48, 0, 96, 128))
            payload = io.BytesIO()
            source.save(payload, 'PNG')
            data = {'garment_type': 'shirt', 'fabric_image': payload,
                    'options': {'fabric_crop_box': [48, 0, 96, 128]}}
            for shot in DEFINITION.shots:
                config = build_config(data, shot, 71)
                self.assertEqual(config['fabric_colour_reference']['colours'][0]['hex'], rgb.upper())
                self.assertIn(rgb.upper(), config['prompt'])
                self.assertNotIn('yellow', config['prompt'])
                self.assertEqual(config['fabric_colour_reference']['crop_box'], [48, 0, 96, 128])

    def test_default_layout_and_dimensions_keep_all_six_references(self):
        self.assertEqual(get_definition('shirt').edition, 'editorial-v1')
        layout = validate_definition(DEFINITION)
        self.assertEqual(layout.size, (1800, 2400))
        self.assertFalse(layout.swatch_box or layout.texts)
        self.assertEqual([p.shot for p in layout.panels[-3:]], ['collar', 'cuff', 'hem'])
        self.assertEqual(len({p.box[0] for p in layout.panels[-3:]}), 1)
        for shot in DEFINITION.shots:
            self.assertEqual(shot.operation, 'template_edit')
            self.assertEqual(shot.dependencies, ())
            for draft in (False, True):
                data = {'fabric_image': io.BytesIO(image_bytes()), 'garment_type': 'shirt',
                        'options': {'draft_mode': draft}}
                config = build_config(data, shot, 71)
                limit = 768 if draft else 1536 if shot.key == 'front' else 1024
                self.assertLessEqual(max(config['output_dimensions']), limit)
                self.assertTrue(all(side % 32 == 0 for side in config['output_dimensions']))
        self.assertEqual(get_definition('shirt', 'classic-v1').layout({}).size, (1296, 2304))

    @patch('fabricapp.catalog.generate_tryon_image')
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(image_bytes(), 71))
    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/photo.png'})
    def test_stream_uses_each_template_once_and_preserves_identity_and_parameters(self, upload, edit, pipeline):
        response = request_catalog()
        self.assertEqual(response.status_code, 200)
        events = [json.loads(line) for line in response.streaming_content]
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(events[-1]['collage']['aspect_ratio'], '3:4')
        self.assertFalse(events[-1]['collage']['includes_original_swatch'])
        self.assertEqual(edit.call_count, 6)
        pipeline.assert_not_called()
        self.assertEqual(upload.call_count, 7)
        for index, (shot, call) in enumerate(zip(DEFINITION.shots, edit.call_args_list)):
            args = call.kwargs
            self.assertEqual(args['person_image'].getvalue(), shot.reference.read_bytes())
            self.assertEqual(args['prompt_config']['seed'], 71)
            self.assertEqual(args['prompt_config']['guidance'], 6)
            self.assertEqual(args.get('face_choice'), 'raghav' if index < 3 else None)
            if index >= 3:
                self.assertNotIn('face_image', args)
                self.assertNotIn('Image 2', args['prompt_config']['prompt'])
            if shot.key == 'back':
                self.assertIn('Keep the face hidden', args['prompt_config']['prompt'])
        for call in upload.call_args_list[:6]:
            self.assertEqual(call.args[0], image_bytes())

    @override_settings(SAVE_DEBUG_FILES=False)
    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/photo.png'})
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_actual_provider_preparation_sends_pose_and_fabric_for_all_six_shots(self, post, upload):
        inputs = []

        def reply(url, **kwargs):
            files, parameters = kwargs['files'], kwargs['data']
            inputs.append(set(files))
            return Mock(status_code=200, headers={'Content-Type': 'image/png'},
                        content=image_bytes((parameters['width'], parameters['height'])))

        post.side_effect = reply
        response = request_catalog()
        events = [json.loads(line) for line in response.streaming_content]
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(post.call_count, 6)
        self.assertEqual(inputs[:3], [{'input_image_0', 'input_image_1', 'input_image_2'}] * 3)
        self.assertEqual(inputs[3:], [{'input_image_0', 'input_image_1'}] * 3)
