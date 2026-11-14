import io
import json
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from rest_framework.test import APIClient

from fabricapp.test_catalog import picture
from fabricapp.ai.providers.cloudflare_engine import GenerationResult


class PlainKurtaCatalogTests(SimpleTestCase):
    def test_garment_swatch_uses_reference_plan_and_extracts_only_body_pixels(self):
        from PIL import ImageDraw
        from fabricapp.catalog import CatalogRequestSerializer
        from fabricapp.catalog_engine.registry import get_request_definition

        photo = Image.new('RGB', (100, 200), 'white')
        ImageDraw.Draw(photo).rectangle((30, 96, 70, 169), fill='navy')
        image = io.BytesIO()
        photo.save(image, 'PNG')
        for options, size in (({}, (32, 58)), ({'fabric_crop_box': [32, 100, 68, 160]}, (36, 60))):
            serializer = CatalogRequestSerializer(data={
                'garment_image': SimpleUploadedFile('garment.png', image.getvalue(), 'image/png'),
                'garment_as_swatch': True, 'garment_type': 'kurta', 'garment_style': 'plain',
                'gender': 'men', 'face_choice': 'raghav', 'options': options,
            })
            self.assertTrue(serializer.is_valid(), serializer.errors)
            data = serializer.validated_data
            self.assertEqual(data['face_choice'], 'raghav')
            self.assertNotIn('garment_image', data)
            self.assertNotIn('fabric_crop_box', data['options'])
            with Image.open(data['fabric_image']) as swatch:
                self.assertEqual(swatch.size, size)
                self.assertEqual(swatch.getcolors(), [(size[0] * size[1], (0, 0, 128))])
            self.assertEqual([shot.key for shot in get_request_definition(data).shots],
                             ['front', 'side', 'back', 'collar', 'cuff', 'side_slit'])

    def test_report_fixes_keep_detail_crops_and_plain_colour(self):
        from fabricapp.ai.garments.kurta.catalog.plain import SHOTS, build_config, layout

        image = io.BytesIO()
        Image.new('RGB', (72, 96), '#d1c0d9').save(image, 'PNG')
        data = {'fabric_image': image}
        configs = {shot.key: build_config(data, shot, 42) for shot in SHOTS}
        self.assertIn('#D1C0D9', configs['front']['prompt'])
        self.assertIn('Plain cloth stays plain', configs['back']['prompt'])
        self.assertIn('collar and the first buttons', configs['collar']['prompt'])
        self.assertIn('single diagonal sleeve', configs['cuff']['prompt'])
        self.assertIn('lateral vent', configs['side_slit']['prompt'])
        for view in ('collar', 'cuff', 'side_slit'):
            self.assertTrue(configs[view]['prompt'].startswith('Edit this existing close-up in image 0.'))
            self.assertNotIn('full-length sleeves', configs[view]['prompt'])
            self.assertNotIn('coordinating trousers', configs[view]['prompt'])
        self.assertIn('smooth, unpatterned light-grey', configs['cuff']['prompt'])
        self.assertIn('free of buttons, buttonholes, snaps and plackets', configs['side_slit']['prompt'])
        self.assertTrue(all(panel.fit == 'cover' for panel in layout({}).panels))

    def test_distinct_fabric_trim_is_excluded_from_collar_and_cuff_source(self):
        from PIL import ImageDraw
        from fabricapp.ai.garments.kurta.catalog.plain import SHOTS, build_config

        swatch = Image.new('RGB', (160, 240), '#174139')
        draw = ImageDraw.Draw(swatch)
        for x in range(160):
            draw.line((x, 180, x, 239), fill='gold' if x % 4 < 2 else 'red')
        image = io.BytesIO()
        swatch.save(image, 'PNG')
        data = {'fabric_image': image}
        configs = {shot.key: build_config(data, shot, 42) for shot in SHOTS}
        for view in ('collar', 'cuff'):
            self.assertEqual(configs[view]['fabric_region_selection'], 'detected_body_crop')
            self.assertLessEqual(configs[view]['fabric_crop_box'][3], 180)
        for view in ('front', 'side_slit'):
            self.assertNotIn('fabric_crop_box', configs[view])

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/shot.png'})
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_both_sources_generate_all_six_reference_views(self, post, upload):
        views = ['front', 'side', 'back', 'collar', 'cuff', 'side_slit']
        for source in ('fabric_image', 'garment_image'):
            with self.subTest(source=source):
                requests = []

                def provider(*args, **kwargs):
                    params, files = kwargs['data'], kwargs['files']
                    with Image.open(files['input_image_0'][1]) as reference:
                        reference_size = reference.size
                    requests.append((params, files['input_image_1'][1].read(), set(files),
                                     files['input_image_1'][2], reference_size))
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
                using_swatch = source == 'fabric_image'
                self.assertEqual(len(requests), 5 if using_swatch else 6)
                self.assertEqual(events[-1]['images'][-1]['operation'],
                                 'swatch_composite' if using_swatch else 'template_edit')
                original_count = 5 if using_swatch else 3
                self.assertTrue(all(row[1] == requests[0][1] for row in requests[:original_count]))
                if source == 'garment_image':
                    self.assertTrue(all(row[1] != requests[0][1] for row in requests[3:]))
                self.assertTrue(requests[0][1])
                for index, (params, _, files, mime, reference_size) in enumerate(requests):
                    self.assertEqual(int(params['seed']), 73)
                    self.assertEqual(float(params['guidance']), 5.5)
                    self.assertEqual('input_image_2' in files, index < 2)
                    self.assertEqual(max(params['width'], params['height']), 768)
                    if index >= 3:
                        self.assertTrue({'input_image_0', 'input_image_1'}.issubset(files))
                        self.assertLessEqual(max(reference_size), 511)
                        self.assertAlmostEqual(reference_size[0] / reference_size[1],
                                               params['width'] / params['height'], delta=.025)
                    if index < 3:
                        self.assertIn('palace courtyard', params['prompt'])
                        self.assertIn('simple shoes', params['prompt'])
                    if source == 'fabric_image':
                        self.assertEqual(mime, 'image/png')
                        self.assertIn('cotton', params['prompt'].lower())
                    else:
                        self.assertEqual(mime, 'image/jpeg')
                        if index >= 3:
                            self.assertEqual(files, {'input_image_0', 'input_image_1'})
                            self.assertIn('exact zoom, angle and crop', params['prompt'])
                            self.assertIn('garment detail from this catalog', params['prompt'])
                        else:
                            self.assertIn('finished kurta', params['prompt'])
                if source == 'fabric_image':
                    self.assertIn('plus-size', requests[0][0]['prompt'])
                    self.assertIn('dupatt', requests[0][0]['prompt'].lower())
                    self.assertIn('folded back cuff', requests[4][0]['prompt'])
                else:
                    self.assertIn('face, hairstyle and body build', requests[0][0]['prompt'])

        self.assertEqual(upload.call_count, 14)

    def test_ready_detail_uses_the_side_sleeve_and_reference_framing(self):
        from fabricapp.ai.garments.kurta.catalog.plain import READY_MADE_DEFINITION

        collar, cuff, slit = READY_MADE_DEFINITION.shots[3:]
        self.assertEqual([shot.garment_from for shot in (collar, cuff, slit)], ['front', 'side', 'side'])
        prompts = [READY_MADE_DEFINITION.build_config({'garment_image': io.BytesIO(picture())}, shot, 42)['prompt']
                   for shot in (collar, cuff, slit)]
        self.assertIn('top of the placket', prompts[0])
        self.assertIn('one sleeve and wrist', prompts[1])
        self.assertIn('free of added fasteners', prompts[2])

    def test_other_styles_keep_classic_and_cannot_select_plain_edition(self):
        from fabricapp.catalog_engine.registry import get_request_definition

        for style in ('pathani', 'jodhpuri'):
            data = {'garment_type': 'kurta', 'garment_style': style}
            self.assertEqual(get_request_definition(data).edition, 'classic-v1')
            with self.assertRaises(ValueError):
                get_request_definition({**data, 'catalog_edition': 'plain-v1'})
            with self.assertRaises(ValueError):
                get_request_definition({**data, 'garment_image': object()})


class SherwaniCatalogTests(SimpleTestCase):
    def test_colour_alignment_changes_cloth_and_leaves_disconnected_background(self):
        import numpy as np
        from PIL import ImageDraw
        from fabricapp.ai.garments.kurta.catalog.sherwani_colour import match_solid_cloth

        image = Image.new('RGB', (160, 240), '#eeeeee')
        draw = ImageDraw.Draw(image)
        draw.rectangle((48, 46, 113, 172), fill='#4e8b4a')
        draw.rectangle((16, 68, 26, 156), fill='#4e8b4a')
        buffer = io.BytesIO()
        image.save(buffer, 'PNG')
        original = GenerationResult(buffer.getvalue(), 42)
        result = match_solid_cloth(original, 'back', np.array([122, 138, 31]))
        with Image.open(io.BytesIO(result.image_bytes)) as corrected:
            self.assertEqual(corrected.getpixel((80, 100)), (122, 138, 31))
            self.assertEqual(corrected.getpixel((21, 100)), (78, 139, 74))

    def test_swatch_side_slit_preserves_reference_gap_and_background_pixels(self):
        from PIL import ImageChops, ImageFilter
        from fabricapp.ai.garments.kurta.catalog import plain, sherwani
        from fabricapp.catalog_engine.swatch_composite import render_swatch_shot

        for definition in (plain.DEFINITION, sherwani.DEFINITION):
            shot = definition.shots[-1]
            result = render_swatch_shot({'fabric_image': io.BytesIO(picture())}, shot)
            with Image.open(io.BytesIO(result.image_bytes)) as output, Image.open(shot.reference) as reference, \
                    Image.open(shot.reference_mask) as mask:
                self.assertEqual(output.size, reference.size)
                difference = ImageChops.difference(output, reference.convert('RGB'))
                protected = mask
                if shot.natural_swatch_shading:
                    protected = mask.filter(ImageFilter.GaussianBlur(reference.width / 90))
                outside = protected.point(lambda pixel: 255 if pixel == 0 else 0)
                self.assertIsNone(Image.composite(difference, Image.new('RGB', output.size), outside).getbbox())
                self.assertNotEqual(output.getpixel((100, 100)), reference.convert('RGB').getpixel((100, 100)))

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/shot.png'})
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 42))
    def test_sherwani_uses_six_references_for_each_source_mode(self, edit, upload):
        for source, extract in (('fabric_image', False), ('garment_image', False), ('garment_image', True)):
            with self.subTest(source=source, extract=extract):
                edit.reset_mock()
                upload.reset_mock()
                response = APIClient().post('/api/generate-catalog/', {
                    source: SimpleUploadedFile('source.png', picture(), 'image/png'),
                    'garment_as_swatch': extract, 'garment_type': 'kurta', 'garment_style': 'sherwani',
                    'gender': 'men', 'face_choice': 'raghav',
                    'background': 'white_marble_terrace', 'options': json.dumps({'draft_mode': True}),
                }, format='multipart')
                self.assertEqual(response.status_code, 200, getattr(response, 'data', None))
                events = [json.loads(line) for line in response.streaming_content]
                self.assertEqual(events[0]['catalog_edition'], 'sherwani-v1')
                self.assertEqual(events[-1]['status'], 'completed')
                self.assertEqual(events[-1]['collage']['aspect_ratio'], '3:4')
                ready = source == 'garment_image' and not extract
                self.assertEqual(edit.call_count, 6 if ready else 4)
                self.assertEqual(upload.call_count, 7)
                views = events[-1]['images']
                self.assertEqual([image['reference_template'] for image in views], [
                    '01_front.png', '02_side.png', '03_back.png', '04_collar.png', '05_cuff.png', '06_side_slit.png',
                ])
                self.assertEqual(views[-1]['operation'], 'template_edit' if ready else 'swatch_composite')
                self.assertEqual(views[4]['operation'], 'template_edit' if ready else 'swatch_composite')
                for index, call in enumerate(edit.call_args_list):
                    args = call.kwargs
                    prompt = args['prompt_config']['prompt']
                    self.assertIn('garment_image' if ready else 'fabric_image', args)
                    self.assertEqual(args.get('face_choice'), 'raghav' if index < 2 else None)
                    self.assertIn('only with broad, diffused neutral white light', prompt)
                    self.assertNotIn('sunlit white marble terrace', prompt)
                    self.assertNotIn('soft warm daylight', prompt)
                    if index == 2:
                        self.assertIn('back and rear collar free of buttons', prompt)
                        self.assertNotIn('Keep the reference front closure', prompt)
                    if index == 1 and not ready:
                        self.assertIn('A solid swatch stays solid', prompt)
                    if index >= 3:
                        self.assertNotIn('marble terrace', prompt)
                        if ready:
                            self.assertNotEqual(args['garment_image'].getvalue(), picture())
                    else:
                        self.assertIn('carved white marble terrace', prompt)
                prompts = [call.kwargs['prompt_config']['prompt'] for call in edit.call_args_list[3:]]
                self.assertIn('stand collar', prompts[0])
                if ready:
                    self.assertIn('one sleeve and its wrist', prompts[1])
                    self.assertIn('lower side seam, hem and vent', prompts[2])
