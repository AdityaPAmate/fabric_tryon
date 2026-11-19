import io
import json
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from rest_framework.test import APIClient

from fabricapp.test_catalog import picture
from fabricapp.ai.providers.cloudflare_engine import GenerationResult


class KurtaOutfitPolicyTests(SimpleTestCase):
    def test_white_trousers_are_required_in_all_three_styles_and_both_source_modes(self):
        from fabricapp.ai.garments.kurta.catalog import plain, sherwani, jodhpuri

        for edition in (plain, sherwani, jodhpuri):
            for key in ('fabric_image', 'garment_image'):
                data = {key: io.BytesIO(picture())}
                for shot in edition.SHOTS[:3]:
                    prompt = edition.build_config(data, shot, 42)['prompt']
                    with self.subTest(edition=edition.__name__, source=key, shot=shot.key):
                        self.assertIn('same solid white trousers in every view', prompt)
                        self.assertNotIn('plain coordinating trousers', prompt)

    def test_pathani_main_colour_excludes_print_and_preserves_source_stream(self):
        import numpy as np
        from PIL import ImageDraw
        from fabricapp.ai.garments.kurta.catalog.pathani_trousers import trouser_colour

        for colour in ('#244c93', '#38834c', '#803848', '#d1c1d9'):
            swatch = Image.new('RGB', (120, 160), colour)
            ImageDraw.Draw(swatch).rectangle((10, 10, 29, 159), fill='#f6cf32')
            stream = io.BytesIO()
            swatch.save(stream, 'PNG')
            stream.seek(9)
            target = trouser_colour({'fabric_image': stream})
            self.assertLess(np.linalg.norm(target - Image.new('RGB', (1, 1), colour).getpixel((0, 0))), 3)
            self.assertEqual(stream.tell(), 9)

    def test_sherwani_corrects_greyed_brown_and_neutral_cloth(self):
        import numpy as np
        from PIL import ImageDraw
        from fabricapp.ai.garments.kurta.catalog.sherwani_colour import match_solid_cloth

        for observed, target in (((66, 55, 49), (62, 40, 27)), ((155, 155, 155), (180, 180, 180))):
            image = Image.new('RGB', (160, 240), 'white')
            ImageDraw.Draw(image).rectangle((45, 45, 115, 180), fill=observed)
            source = io.BytesIO()
            image.save(source, 'PNG')
            result = match_solid_cloth(GenerationResult(source.getvalue(), 42), 'back', np.array(target))
            with Image.open(io.BytesIO(result.image_bytes)) as output:
                self.assertLess(np.linalg.norm(np.asarray(output.getpixel((80, 100))) - target), 5)
                self.assertEqual(output.getpixel((10, 100)), (255, 255, 255))


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

    def test_pathani_defaults_to_its_own_edition(self):
        from fabricapp.catalog_engine.registry import get_request_definition

        data = {'garment_type': 'kurta', 'garment_style': 'pathani'}
        self.assertEqual(get_request_definition(data).edition, 'pathani-v1')
        self.assertEqual(get_request_definition({**data, 'catalog_edition': 'classic-v1'}).edition, 'classic-v1')
        with self.assertRaises(ValueError):
            get_request_definition({**data, 'catalog_edition': 'plain-v1'})


class PathaniCatalogTests(SimpleTestCase):
    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/shot.png'})
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 42))
    def test_trouser_review_does_not_abort_or_retry_a_successful_catalog(self, edit, upload):
        source = io.BytesIO()
        Image.new('RGB', (96, 128), '#d1c1d9').save(source, 'PNG')
        response = APIClient().post('/api/generate-catalog/', {
            'fabric_image': SimpleUploadedFile('source.png', source.getvalue(), 'image/png'),
            'garment_type': 'kurta', 'garment_style': 'pathani', 'gender': 'men',
            'options': json.dumps({'draft_mode': True}),
        }, format='multipart')
        self.assertEqual(response.status_code, 200)
        events = [json.loads(line) for line in response.streaming_content]
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(events[-1]['failed_views'], [])
        self.assertEqual(edit.call_count, 4)
        self.assertEqual(upload.call_count, 7)
        portraits = events[-1]['images'][:3]
        self.assertTrue(all(image['generation']['pathani_trouser_colour_review'] == 'review_recommended'
                            for image in portraits))

    def test_local_collar_keeps_reference_skin_background_and_exact_crop(self):
        from PIL import ImageChops
        from fabricapp.ai.garments.kurta.catalog import pathani
        from fabricapp.catalog_engine.runner import Services, generate_shot

        shot = next(shot for shot in pathani.DEFINITION.shots if shot.key == 'collar')
        self.assertEqual(shot.operation, 'swatch_composite')
        for colour in ((62, 40, 27), (209, 193, 217), (122, 138, 31)):
            source = io.BytesIO()
            Image.new('RGB', (96, 128), colour).save(source, 'PNG')
            provider = Mock(side_effect=AssertionError('Collar must keep the existing photograph.'))
            result = generate_shot({'fabric_image': source}, shot, pathani.DEFINITION, {}, {},
                                   Services(provider, provider, Mock()))
            provider.assert_not_called()
            with Image.open(io.BytesIO(result.image_bytes)) as output, Image.open(shot.reference) as reference, \
                    Image.open(shot.reference_mask) as mask:
                self.assertEqual(output.size, reference.size)
                difference = ImageChops.difference(output, reference.convert('RGB'))
                protected = mask.point(lambda value: 255 if value == 0 else 0)
                self.assertIsNone(Image.composite(difference, Image.new('RGB', output.size), protected).getbbox())
                self.assertIsNotNone(difference.getbbox())

    def test_trouser_check_rejects_broad_darkening_without_repainting_pixels(self):
        import numpy as np
        from fabricapp.ai.garments.kurta.catalog.pathani_trousers import trousers_match

        target = np.array([209, 193, 217])
        for colour, accepted in (((209, 193, 217), True), ((105, 88, 117), False)):
            output = io.BytesIO()
            Image.new('RGB', (100, 240), colour).save(output, 'PNG')
            original = output.getvalue()
            self.assertEqual(trousers_match(original, target), accepted)
            self.assertEqual(output.getvalue(), original)

    def test_pathani_exposure_reaches_full_length_side_hem(self):
        import numpy as np
        from PIL import ImageDraw
        from fabricapp.ai.garments.kurta.catalog.pathani_colour import match_cloth_exposure

        image = Image.new('RGB', (160, 480), '#eeeeee')
        draw = ImageDraw.Draw(image)
        draw.rectangle((55, 96, 118, 360), fill='#3e281b')
        draw.rectangle((55, 325, 118, 360), fill='#8a5237')
        draw.rectangle((40, 180, 65, 211), fill='#d69a7e')
        payload = io.BytesIO()
        image.save(payload, 'PNG')
        target = np.array([62, 40, 27])
        result = match_cloth_exposure(GenerationResult(payload.getvalue(), 42), 'side', target)
        with Image.open(io.BytesIO(result.image_bytes)) as output:
            self.assertLess(np.linalg.norm(np.array(output.getpixel((85, 349))) - target), 18)
            self.assertEqual(output.getpixel((57, 197)), image.getpixel((57, 197)))

    def test_pathani_exposure_reduces_cast_and_broad_shadows_without_recolouring_skin(self):
        import numpy as np
        from PIL import ImageDraw
        from fabricapp.ai.garments.kurta.catalog.pathani_colour import match_cloth_exposure

        image = Image.new('RGB', (180, 240), '#eeeeee')
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 85, 179, 239), fill='#7a4738')
        draw.rectangle((0, 178, 179, 239), fill='#40261e')
        draw.rectangle((20, 146, 48, 172), fill='#e5dfd5')
        draw.rectangle((70, 0, 110, 105), fill='#d69a7e')
        source = io.BytesIO()
        image.save(source, 'PNG')
        generation = GenerationResult(source.getvalue(), 42)
        target = np.array([81, 57, 45])
        result = match_cloth_exposure(generation, 'collar', target)
        with Image.open(io.BytesIO(result.image_bytes)) as output:
            self.assertEqual(output.getpixel((90, 96)), image.getpixel((90, 96)))
            self.assertEqual(output.getpixel((13, 40)), image.getpixel((13, 40)))
            bright, dark = (np.array(output.getpixel((45, y))) for y in (130, 210))
            self.assertLess(np.linalg.norm(bright - target), 10)
            self.assertLess(np.linalg.norm(bright - dark), 18)
            self.assertLess(np.linalg.norm(np.array(output.getpixel((135, 130))) - target), 10)
            self.assertLess(np.linalg.norm(np.array(output.getpixel((34, 160))) - target), 22)

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/shot.png'})
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 42))
    def test_pathani_uses_six_references_in_each_source_mode(self, edit, upload):
        for source, extract in (('fabric_image', False), ('garment_image', False), ('garment_image', True)):
            with self.subTest(source=source, extract=extract):
                edit.reset_mock()
                upload.reset_mock()
                response = APIClient().post('/api/generate-catalog/', {
                    source: SimpleUploadedFile('source.png', picture(), 'image/png'),
                    'garment_as_swatch': extract, 'garment_type': 'kurta', 'garment_style': 'pathani',
                    'face_choice': 'raghav', 'gender': 'men', 'background': 'royal_courtyard',
                    'options': json.dumps({'draft_mode': True}),
                }, format='multipart')
                self.assertEqual(response.status_code, 200, getattr(response, 'data', None))
                events = [json.loads(line) for line in response.streaming_content]
                self.assertEqual(events[0]['catalog_edition'], 'pathani-v1')
                self.assertEqual(events[-1]['status'], 'completed')
                self.assertEqual(events[-1]['collage']['aspect_ratio'], '3:4')
                self.assertEqual([view['reference_template'] for view in events[-1]['images']], [
                    '01_front.png', '02_side.png', '03_back.png', '04_collar.png', '05_cuff.png', '06_pocket.png',
                ])
                ready = source == 'garment_image' and not extract
                self.assertEqual(edit.call_count, 6 if ready else 4)
                self.assertEqual(upload.call_count, 7)
                self.assertEqual(events[-1]['images'][-1]['operation'], 'template_edit' if ready else 'swatch_composite')
                for index, call in enumerate(edit.call_args_list):
                    args = call.kwargs
                    prompt = args['prompt_config']['prompt']
                    self.assertEqual(args.get('face_choice'), 'raghav' if index < 2 else None)
                    if index >= 2:
                        self.assertNotIn('face_image', args)
                    self.assertIn('Use even neutral white light', prompt)
                    self.assertIn('including the hem, side vent, pockets and cuffs', prompt)
                    self.assertIn('garment_image' if ready else 'fabric_image', args)
                    self.assertEqual('palace courtyard' in prompt, index < 3)
                    if index == 2:
                        self.assertIn('free of front closures, chest pockets and buttons', prompt)
                    if ready and index >= 3:
                        self.assertNotEqual(args['garment_image'].getvalue(), picture())
                from fabricapp.ai.garments.kurta.catalog import pathani
                collar = next(shot for shot in pathani.SHOTS if shot.key == 'collar')
                collar_prompt = pathani.build_config({
                    'garment_image' if ready else 'fabric_image': io.BytesIO(picture()),
                }, collar, 42)['prompt']
                self.assertIn('only the lower chin', collar_prompt)
                self.assertIn('CLOSE-UP CAMERA LOCK', collar_prompt)
                self.assertNotIn('shoulders, sleeves and lower body', collar_prompt)
                self.assertIn('waistband', collar_prompt)
                prompts = [call.kwargs['prompt_config']['prompt'] for call in edit.call_args_list[3:]]
                self.assertIn('smooth light-grey studio background', prompts[1 if ready else 0])
                if ready:
                    self.assertIn('one chest pocket in close-up', prompts[2])


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


class JodhpuriCatalogTests(SimpleTestCase):
    def test_collar_correction_has_no_horizontal_step_at_the_old_crop_boundary(self):
        import numpy as np
        from fabricapp.ai.garments.kurta.catalog.jodhpuri_colour import align_jacket_colour

        source = io.BytesIO()
        Image.new('RGB', (200, 300), (100, 70, 50)).save(source, 'PNG')
        result = align_jacket_colour(GenerationResult(source.getvalue(), 42), 'collar',
                                     np.array([62, 40, 27]))
        with Image.open(io.BytesIO(result.image_bytes)) as output:
            above, below = (np.asarray(output.getpixel((30, y)), dtype=float) for y in (81, 87))
            self.assertLess(np.max(np.abs(above - below)), 3)
            self.assertLess(np.linalg.norm(below - (62, 40, 27)), 6)

    def test_back_highlight_correction_stays_above_the_white_trousers(self):
        import numpy as np
        from PIL import ImageDraw
        from fabricapp.ai.garments.kurta.catalog.jodhpuri_colour import align_jacket_colour

        image = Image.new('RGB', (160, 320), '#eeeeee')
        draw = ImageDraw.Draw(image)
        draw.rectangle((32, 55, 130, 170), fill=(100, 70, 50))
        # A warm reflection on the white trousers used to be pulled into the
        # expanded jacket mask and recoloured as a brown patch.
        draw.rectangle((67, 171, 93, 200), fill=(225, 205, 195))
        source = io.BytesIO()
        image.save(source, 'PNG')
        result = align_jacket_colour(GenerationResult(source.getvalue(), 42), 'back',
                                     np.array([62, 40, 27]))
        with Image.open(io.BytesIO(result.image_bytes)) as output:
            self.assertEqual(output.getpixel((80, 190)), image.getpixel((80, 190)))

    def test_wrong_back_fabric_is_retried_once_and_never_uploaded_on_second_failure(self):
        import threading
        from dataclasses import replace
        from fabricapp.ai.garments.kurta.catalog import jodhpuri
        from fabricapp.catalog_engine.contracts import Layout, Panel
        from fabricapp.catalog_engine.runner import Services, generate_catalog

        source = io.BytesIO()
        Image.new('RGB', (64, 96), '#d1c1d9').save(source, 'PNG')
        correct = GenerationResult(source.getvalue(), 43)
        wrong = GenerationResult(picture(), 42)
        shot = next(shot for shot in jodhpuri.DEFINITION.shots if shot.key == 'back')
        definition = replace(jodhpuri.DEFINITION, shots=(shot,), layout=lambda product: Layout(
            'retry-check', (64, 96), (Panel('back', (0, 0, 64, 96)),)))
        for outputs, expected_status in (([wrong, correct], 'completed'), ([wrong, wrong], 'failed')):
            edit = Mock(side_effect=outputs)
            upload = Mock(return_value={'url': 'https://example.com/output.png'})
            with patch('fabricapp.catalog_engine.runner.get_request_definition', return_value=definition):
                events = list(generate_catalog({'fabric_image': io.BytesIO(source.getvalue()),
                                                'garment_type': 'kurta', 'garment_style': 'jodhpuri'},
                                               threading.Event(), Services(Mock(), edit, upload)))
            self.assertEqual(edit.call_count, 2)
            self.assertEqual(events[-1]['status'], expected_status)
            self.assertEqual(edit.call_args.kwargs['prompt_config']['seed'], 43)
            self.assertIn('FABRIC CORRECTION', edit.call_args.kwargs['prompt_config']['prompt'])
            if expected_status == 'failed':
                upload.assert_not_called()
                self.assertEqual(next(e for e in events if e['event'] == 'image_failed')['error'], 'fabric_mismatch')
            else:
                self.assertEqual(events[-1]['images'][0]['generation']['catalog_fabric_retry_count'], 1)

    def test_pale_jodhpuri_back_matches_body_shade_without_recolouring_print(self):
        import numpy as np
        from PIL import ImageDraw
        from fabricapp.ai.garments.kurta.catalog.jodhpuri_colour import align_jacket_colour

        image = Image.new('RGB', (120, 240), '#c7b9aa')
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 56, 99, 151), fill='#c0c9bc')
        draw.rectangle((49, 89, 61, 101), fill='#ad3147')
        draw.rectangle((75, 75, 88, 90), fill='#ececec')
        source = io.BytesIO()
        image.save(source, 'PNG')
        result = align_jacket_colour(GenerationResult(source.getvalue(), 42), 'back', np.array([124, 164, 128]))
        with Image.open(io.BytesIO(result.image_bytes)) as corrected:
            target = np.array([124, 164, 128])
            corrected_cloth = np.array(corrected.getpixel((70, 110)))
            self.assertLess(np.linalg.norm(corrected_cloth - target),
                            .25 * np.linalg.norm(np.array([192, 201, 188]) - target))
            self.assertEqual(corrected.getpixel((54, 95)), (173, 49, 71))
            highlight = np.array(corrected.getpixel((81, 82)))
            self.assertLess(np.linalg.norm(highlight - target), 55)
            self.assertGreater(highlight[1] - highlight[0], 20)
            self.assertEqual(corrected.getpixel((10, 170)), (199, 185, 170))

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/shot.png'})
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 42))
    def test_jacket_catalog_routes_all_sources_to_the_six_jodhpuri_references(self, edit, upload):
        from PIL import ImageDraw

        jacket = Image.new('RGB', (100, 200), 'white')
        ImageDraw.Draw(jacket).rectangle((50, 58, 74, 88), fill='navy')
        source_image = io.BytesIO()
        jacket.save(source_image, 'PNG')
        navy_output = io.BytesIO()
        Image.new('RGB', (64, 96), 'navy').save(navy_output, 'PNG')
        for source, extract in (('fabric_image', False), ('garment_image', False), ('garment_image', True)):
            with self.subTest(source=source, extract=extract):
                edit.reset_mock()
                upload.reset_mock()
                # Extraction selects the navy chest. The provider mock must
                # return that fabric to pass the back-view fidelity check.
                edit.return_value = GenerationResult(navy_output.getvalue() if extract else picture(), 42)
                response = APIClient().post('/api/generate-catalog/', {
                    source: SimpleUploadedFile('sample.png', source_image.getvalue(), 'image/png'),
                    'garment_as_swatch': extract, 'garment_type': 'kurta', 'garment_style': 'jodhpuri',
                    'gender': 'men', 'face_choice': 'raghav', 'background': 'white_marble_terrace',
                    'options': json.dumps({'draft_mode': True}),
                }, format='multipart')
                self.assertEqual(response.status_code, 200, getattr(response, 'data', None))
                events = [json.loads(line) for line in response.streaming_content]
                self.assertEqual(events[0]['catalog_edition'], 'jodhpuri-v1')
                self.assertEqual(events[-1]['status'], 'completed')
                self.assertEqual(events[-1]['collage']['aspect_ratio'], '3:4')
                self.assertEqual([view['view'] for view in events[-1]['images']],
                                 ['front', 'side', 'back', 'collar', 'cuff', 'pocket'])
                self.assertEqual(upload.call_count, 7)
                ready = source == 'garment_image' and not extract
                self.assertEqual(edit.call_count, 6 if ready else 5)
                self.assertEqual(events[-1]['images'][-1]['operation'],
                                 'template_edit' if ready else 'swatch_composite')
                for index, call in enumerate(edit.call_args_list):
                    args = call.kwargs
                    self.assertEqual(args.get('face_choice'), 'raghav' if index < 2 else None)
                    prompt = args['prompt_config']['prompt']
                    self.assertIn('diffused neutral white light', prompt)
                    if index >= 3:
                        self.assertNotIn('marble terrace', prompt)
                        if ready:
                            with Image.open(io.BytesIO(args['garment_image'].getvalue())) as cropped:
                                self.assertLess(cropped.height, 96)
                if ready:
                    self.assertIn('breast welt pocket', edit.call_args.kwargs['prompt_config']['prompt'])
                if extract:
                    with Image.open(io.BytesIO(edit.call_args.kwargs['fabric_image'].getvalue())) as swatch:
                        self.assertEqual(swatch.getpixel((5, 5)), (0, 0, 128))
