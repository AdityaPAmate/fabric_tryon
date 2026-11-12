import io
import json
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from fabricapp.catalog_engine.registry import get_definition
from fabricapp.test_catalog_engine import picture, post


class KurtiPantCatalogTests(SimpleTestCase):
    @override_settings(SAVE_DEBUG_FILES=False)
    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.test/image.png'})
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_default_catalog_streams_six_reference_edits_and_a_3x4_export(self, provider, upload):
        swatch = Image.new('RGB', (160, 300), 'green')
        swatch.paste('red', (0, 210, 160, 300))
        source = io.BytesIO()
        swatch.save(source, 'PNG')
        input_pixels = []

        def answer(url, **request):
            fields = request['data']
            fabric_bytes = request['files']['input_image_1'][1].getvalue()
            with Image.open(io.BytesIO(fabric_bytes)) as prepared:
                input_pixels.append((prepared.size, prepared.getpixel((20, prepared.height - 5))))
            return Mock(status_code=200, headers={'Content-Type': 'image/png'},
                        content=picture(size=(fields['width'], fields['height'])))

        provider.side_effect = answer
        response = post(garment_type='kurti_pant',
                        fabric_image=SimpleUploadedFile('panel.png', source.getvalue(), content_type='image/png'),
                        face_image=SimpleUploadedFile('face.png', picture('orange'), content_type='image/png'),
                        garment_details=['full_sleeves', 'with_dupatta'], options='{"draft_mode": true}')
        self.assertEqual(response.status_code, 200)
        try:
            events = [json.loads(chunk) for chunk in response.streaming_content]
        finally:
            response.close()

        expected = {
            'front': 'kurti_front_1.png', 'side': 'kurti_side_2.png', 'back': 'kurti_back_3.png',
            'neckline': 'kurti_closeup_4.png', 'sleeve': 'kurti_sleves_5.png', 'pant': 'kurti_pant_6.png',
        }
        self.assertEqual(events[0]['views'], list(expected))
        ready = [event['image'] for event in events if event['event'] == 'image_ready']
        self.assertEqual({image['view']: image['reference_template'] for image in ready}, expected)
        self.assertEqual(len({image['generation']['input_hashes']['input_image_0'] for image in ready}), 6)
        for image, (size, pixel) in zip(ready, input_pixels):
            if image['view'] == 'sleeve':
                self.assertEqual(image['generation']['fabric_crop_box'], [0, 90, 160, 180])
                self.assertEqual(size, (160, 90))
                self.assertEqual(pixel, (0, 128, 0))
            else:
                self.assertEqual(size, (160, 300))
                self.assertEqual(pixel, (255, 0, 0))
        for image in ready:
            self.assertEqual('input_image_2' in image['generation']['input_hashes'], image['view'] in ('front', 'side'))
        self.assertIn('full-length sleeves', provider.call_args_list[0].kwargs['data']['prompt'])
        self.assertIn('Add a dupatta', provider.call_args_list[2].kwargs['data']['prompt'])
        for call in provider.call_args_list[:3]:
            prompt = call.kwargs['data']['prompt']
            self.assertIn('dominant cloth midtone', prompt)
            self.assertIn('#008000', prompt)
            self.assertIn('#FF0000', prompt)
        neckline = provider.call_args_list[3].kwargs['data']['prompt']
        sleeve = provider.call_args_list[4].kwargs['data']['prompt']
        self.assertIn('continues past the bottom edge', neckline)
        self.assertIn('curved floral stitch rows', neckline)
        self.assertIn('single cuff opening', sleeve)
        self.assertIn('reverse of the same fabric', sleeve)
        for prompt in (neckline, sleeve):
            self.assertNotIn('solid white', prompt)
            self.assertNotIn('full-length sleeves', prompt)
        self.assertNotIn('#FF0000', sleeve)
        self.assertIn('Keep the pants solid white', provider.call_args_list[-1].kwargs['data']['prompt'])
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(events[-1]['collage']['aspect_ratio'], '3:4')
        self.assertFalse(events[-1]['collage']['includes_original_swatch'])
        self.assertEqual(provider.call_count, 6)
        self.assertEqual(upload.call_count, 7)
        with Image.open(io.BytesIO(upload.call_args.args[0])) as collage:
            self.assertEqual(collage.size, (1800, 2400))

    def test_sleeve_uses_a_selected_crop_even_for_tall_fabric(self):
        definition = get_definition('kurti_pant')
        shot = next(shot for shot in definition.shots if shot.key == 'sleeve')
        source = io.BytesIO(picture(size=(160, 300)))
        crop = [10, 50, 110, 130]
        config = definition.build_config({'fabric_image': source, 'options': {'fabric_crop_box': crop}}, shot, 42)
        self.assertEqual(config['fabric_crop_box'], crop)
        self.assertEqual(config['fabric_region_selection'], 'explicit_crop')

    def test_colour_guidance_handles_tonal_variation_and_balanced_patterns(self):
        definition = get_definition('kurti_pant')
        back = next(shot for shot in definition.shots if shot.key == 'back')
        swatch = Image.new('RGB', (100, 100), '#24365A')
        swatch.paste('#2C3E62', (0, 35, 100, 70))
        swatch.paste('#942C43', (0, 70, 100, 100))
        source = io.BytesIO()
        swatch.save(source, 'PNG')
        prompt = definition.build_config({'fabric_image': source}, back, 42)['prompt']
        self.assertIn('dominant cloth midtone to deep blue (#283A5E)', prompt)
        self.assertIn('#942C43', prompt)

        swatch.paste('#942C43', (0, 50, 100, 100))
        source = io.BytesIO()
        swatch.save(source, 'PNG')
        prompt = definition.build_config({'fabric_image': source}, back, 42)['prompt']
        self.assertIn('Keep all the fabric colours distinct', prompt)
        self.assertIn('#942C43', prompt)
        self.assertIn('#24365A', prompt)
        self.assertNotIn('dominant cloth midtone', prompt)

    def test_classic_edition_still_resolves_to_the_legacy_catalog(self):
        classic = get_definition('kurti_pant', 'classic-v1')
        self.assertEqual(classic.layout({}).size, (1800, 3200))
        self.assertEqual(classic.shots[0].operation, 'pipeline')
