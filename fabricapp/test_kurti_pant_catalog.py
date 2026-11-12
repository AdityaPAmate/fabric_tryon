import io
import json
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.runner import Services, generate_shot
from fabricapp.ai.providers.cloudflare_engine import generate_tryon_image
from fabricapp.test_catalog_engine import picture, post


class KurtiPantCatalogTests(SimpleTestCase):
    @override_settings(SAVE_DEBUG_FILES=False)
    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.test/image.png'})
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_default_catalog_streams_six_reference_edits_and_a_3x4_export(self, provider, upload):
        swatch = Image.new('RGB', (160, 300), 'green')
        swatch.paste('red', (0, 210, 160, 300))
        for x in range(0, swatch.width, 8):
            swatch.paste('yellow', (x, 210, x + 4, swatch.height))
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
        generated = ready[:-1]
        self.assertEqual(len({image['generation']['input_hashes']['input_image_0'] for image in generated}), 5)
        for image, (size, pixel) in zip(generated, input_pixels):
            if image['view'] in ('neckline', 'sleeve'):
                self.assertEqual(image['generation']['fabric_region_selection'], 'detected_body_crop')
                self.assertLessEqual(image['generation']['fabric_crop_box'][3], 210)
                self.assertLess(size[1], 210)
                self.assertEqual(pixel, (0, 128, 0))
            else:
                self.assertEqual(size, (160, 300))
                self.assertEqual(pixel, (255, 0, 0))
        for image in generated:
            self.assertEqual('input_image_2' in image['generation']['input_hashes'], image['view'] in ('front', 'side'))
        self.assertIn('full-length sleeves', provider.call_args_list[0].kwargs['data']['prompt'])
        self.assertIn('Add a dupatta', provider.call_args_list[2].kwargs['data']['prompt'])
        for call in provider.call_args_list[:3]:
            prompt = call.kwargs['data']['prompt']
            self.assertIn('dominant cloth midtone', prompt)
            self.assertIn('#008000', prompt)
            self.assertNotIn('#FF0000', prompt)
            self.assertIn('neutral-white studio', prompt)
        neckline = provider.call_args_list[3].kwargs['data']['prompt']
        sleeve = provider.call_args_list[4].kwargs['data']['prompt']
        self.assertIn('continues past the bottom edge', neckline)
        self.assertIn('single narrow floral vine', neckline)
        self.assertIn('single cuff opening', sleeve)
        self.assertIn('reverse of the same fabric', sleeve)
        self.assertIn('outer sleeve, cuff, button placket, inner fold', sleeve)
        self.assertIn('uninterrupted upper back', provider.call_args_list[2].kwargs['data']['prompt'])
        for prompt in (neckline, sleeve):
            self.assertNotIn('solid white', prompt)
            self.assertNotIn('full-length sleeves', prompt)
        for prompt in (neckline, sleeve):
            self.assertNotIn('#FF0000', prompt)
            self.assertIn('neutral-white studio', prompt)
        self.assertEqual(ready[-1]['generation']['kind'], 'original_reference')
        pant = get_definition('kurti_pant').shots[-1]
        self.assertEqual(upload.call_args_list[-2].args[0], pant.reference.read_bytes())
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(events[-1]['collage']['aspect_ratio'], '3:4')
        self.assertFalse(events[-1]['collage']['includes_original_swatch'])
        self.assertEqual(provider.call_count, 5)
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

    def test_sleeve_uses_body_above_a_dense_hem_in_a_near_square_swatch(self):
        definition = get_definition('kurti_pant')
        sleeve = next(shot for shot in definition.shots if shot.key == 'sleeve')
        swatch = Image.new('RGB', (320, 380), '#114488')
        for x in range(0, swatch.width, 8):
            swatch.paste('#FEC044', (x, 195, x + 4, swatch.height))
        cases = [(swatch, 3, 195, self.assertLess),
                 (swatch.transpose(Image.Transpose.FLIP_TOP_BOTTOM), 1, 185, self.assertGreater),
                 (swatch.transpose(Image.Transpose.TRANSPOSE), 2, 195, self.assertLess)]
        for image, edge, limit, compare in cases:
            with self.subTest(edge=edge):
                source = io.BytesIO()
                image.save(source, 'PNG')
                config = definition.build_config({'fabric_image': source}, sleeve, 42)
                self.assertEqual(config['fabric_region_selection'], 'detected_body_crop')
                compare(config['fabric_crop_box'][edge], limit)
                self.assertIn('#114488', config['prompt'])
                self.assertNotIn('#FEC044', config['prompt'])

    def test_sleeve_preserves_plain_tall_swatches_and_regular_checks(self):
        definition = get_definition('kurti_pant')
        sleeve = next(shot for shot in definition.shots if shot.key == 'sleeve')
        swatch = Image.new('RGB', (320, 640), '#114488')
        for checked in (False, True):
            if checked:
                for x in range(0, 320, 20):
                    for y in range(0, 640, 20):
                        if (x // 20 + y // 20) % 2:
                            swatch.paste('#FEC044', (x, y, x + 20, y + 20))
            source = io.BytesIO()
            swatch.save(source, 'PNG')
            config = definition.build_config({'fabric_image': source}, sleeve, 42)
            self.assertIsNone(config['fabric_crop_box'])

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

    @override_settings(SAVE_DEBUG_FILES=False)
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_selected_scene_changes_only_pant_background_and_stays_out_of_detail_prompts(self, provider):
        definition = get_definition('kurti_pant')
        shots = {shot.key: shot for shot in definition.shots}
        data = {'garment_type': 'kurti_pant', 'background': 'white_marble_terrace'}
        for key in ('neckline', 'sleeve'):
            self.assertNotIn('marble terrace', definition.build_config(data, shots[key], 42)['prompt'])
        for key in ('front', 'side', 'back'):
            prompt = definition.build_config(data, shots[key], 42)['prompt']
            self.assertIn('marble terrace', prompt)
            self.assertIn('neutral-white studio', prompt)
            self.assertNotIn('sunlit white marble terrace', prompt)

        def answer(url, **request):
            fields = request['data']
            return Mock(status_code=200, headers={'Content-Type': 'image/png'},
                        content=picture('blue', (fields['width'], fields['height'])))

        provider.side_effect = answer
        pant = shots['pant']
        result = generate_shot(data, pant, definition, {}, {}, Services(None, generate_tryon_image, None))
        provider.assert_called_once()
        self.assertIn('marble terrace', provider.call_args.kwargs['data']['prompt'])
        self.assertEqual(set(provider.call_args.kwargs['files']), {'input_image_0', 'input_image_1'})
        with Image.open(pant.reference) as reference, Image.open(pant.reference_mask) as mask, \
                Image.open(io.BytesIO(result.image_bytes)) as output:
            self.assertEqual(output.size, reference.size)
            foreground = mask.point(lambda value: 255 if value == 255 else 0)
            self.assertEqual(Image.composite(output, reference, foreground).tobytes(), reference.tobytes())
            self.assertEqual(output.getpixel((0, 0)), (0, 0, 255))
