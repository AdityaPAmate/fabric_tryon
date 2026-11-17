import io
import json
from itertools import product
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from rest_framework.test import APIClient

from fabricapp.ai.garments.blazer.catalog.casual import REFERENCES as CASUAL_REFERENCES
from fabricapp.ai.garments.blazer.catalog.wedding import REFERENCES as WEDDING_REFERENCES
from fabricapp.ai.garments.blazer.catalog.colour import align_portrait_colour, jacket_midtone
from fabricapp.ai.garments.kurta.catalog.sherwani import SCENERY
from fabricapp.ai.fabric.fabric_material import FABRIC_TYPES
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.catalog import CatalogRequestSerializer
from fabricapp.catalog_engine.registry import get_definition


VIEWS = ['front', 'side', 'back', 'lapel', 'cuff', 'pocket']
MIDTONE = (54, 95, 117)


def picture(colour=MIDTONE, size=(96, 128)):
    data = io.BytesIO()
    Image.new('RGB', size, colour).save(data, 'PNG')
    return data.getvalue()


def upload(colour=MIDTONE):
    return SimpleUploadedFile('input.png', picture(colour), content_type='image/png')


class BusinessBlazerCatalogTests(SimpleTestCase):
    def run_catalog(self, **payload):
        definition = get_definition('blazer', 'business-v1')
        portraits = {shot.reference: shot.reference.read_bytes() for shot in definition.shots[:3]}
        delivered = []

        def edit(**kwargs):
            return GenerationResult(portraits[kwargs['pose_reference_path']], kwargs['prompt_config']['seed'])

        def deliver(raw):
            delivered.append(raw)
            return {'url': f'https://example.com/{len(delivered)}.png', 'format': 'png'}

        with patch('fabricapp.catalog.generate_edit', side_effect=edit) as provider, \
                patch('fabricapp.catalog.upload_generated_image', side_effect=deliver):
            response = APIClient().post('/api/generate-catalog/', {
                'garment_type': 'blazer', 'garment_style': 'business', **payload,
            }, format='multipart')
            self.assertEqual(response.status_code, 200, response.content if not response.streaming else '')
            events = [json.loads(line) for line in response.streaming_content]
        self.assertEqual(events[0]['catalog_edition'], 'business-v1')
        self.assertEqual(events[0]['views'], VIEWS)
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual([event['image']['view'] for event in events if event['event'] == 'image_ready'], VIEWS)
        self.assertEqual(events[-2]['image']['aspect_ratio'], '3:4')
        with Image.open(io.BytesIO(delivered[-1])) as collage:
            self.assertEqual(collage.size, (1800, 2400))
        return provider.call_args_list, delivered, events

    def test_swatch_parameters_and_three_masked_detail_panels(self):
        calls, delivered, events = self.run_catalog(
            fabric_image=upload(), fabric_type='velvet', gender='men', body_type='plus',
            face_choice='vihaan', background='royal_courtyard', additional_style_note='Keep a formal tie',
            seed=78, guidance=5.5, options=json.dumps({'draft_mode': True, 'fabric_crop_box': [4, 6, 88, 120]}),
        )
        self.assertEqual(len(calls), 3)
        for call in calls:
            config = call.kwargs['prompt_config']
            self.assertEqual((config['seed'], config['guidance']), (78, 5.5))
            self.assertEqual(max(config['output_dimensions']), 768)
            self.assertEqual(call.kwargs['face_choice'], 'vihaan')
            self.assertIn('plus-size', config['prompt'])
            self.assertIn('dense short plush pile', config['prompt'])
            self.assertIn(SCENERY['royal_courtyard'], config['prompt'])
            self.assertIn('Keep a formal tie', config['prompt'])
            self.assertIn('Replace the original reference trousers', config['prompt'])
            self.assertIn('diffused neutral white light', config['prompt'])
        self.assertIn('plain solid tie and plain solid trousers', calls[0].kwargs['prompt_config']['prompt'])
        self.assertIn('keep the face hidden', calls[-1].kwargs['prompt_config']['prompt'])
        details = [event['image']['generation'] for event in events
                   if event['event'] == 'image_ready' and event['image']['view'] in VIEWS[3:]]
        self.assertEqual(len(details), 3)
        for item in details:
            self.assertEqual(item['kind'], 'swatch_composite')
            self.assertEqual(item['fabric_crop_box'], [4, 6, 88, 120])
        self.assertEqual(details[0]['business_tie_rgb'], list(MIDTONE))
        for raw, (x, y) in zip(delivered[3:6], ((.80, .55), (.76, .34), (.30, .55))):
            with Image.open(io.BytesIO(raw)) as image:
                sample = image.getpixel((round(image.width * x), round(image.height * y)))
                self.assertLess(max(abs(channel - target) for channel, target in zip(sample, MIDTONE)), 20)

    def test_ready_made_uses_the_uploaded_garment_and_derives_detail_pixels(self):
        calls, _, events = self.run_catalog(garment_image=upload(), person_image=upload((90, 80, 70)))
        self.assertEqual(len(calls), 3)
        for call in calls:
            self.assertIn('garment_image', call.kwargs)
            self.assertNotIn('fabric_image', call.kwargs)
            self.assertIsNotNone(call.kwargs['face_image'])
            self.assertEqual(max(call.kwargs['prompt_config']['output_dimensions']), 1536)
        for call in calls[1:]:
            self.assertIn('established wearer and outfit', call.kwargs['prompt_config']['prompt'])
            self.assertEqual(call.kwargs['face_image'].getvalue(), calls[0].kwargs['pose_reference_path'].read_bytes())
        details = [event['image']['generation'] for event in events
                   if event['event'] == 'image_ready' and event['image']['view'] in VIEWS[3:]]
        self.assertEqual([detail['source_view'] for detail in details], ['front', 'side', 'side'])
        self.assertTrue(all(detail['kind'] == 'derived_crop' for detail in details))

    def test_garment_fabric_extraction_preserves_the_swatch_path(self):
        calls, _, _ = self.run_catalog(garment_image=upload(), garment_as_swatch=True, gender='men')
        self.assertEqual(len(calls), 3)
        for call in calls:
            self.assertNotIn('garment_image', call.kwargs)
            with Image.open(call.kwargs['fabric_image']) as swatch:
                self.assertEqual(swatch.getpixel((0, 0)), MIDTONE)

    def test_out_of_bounds_swatch_crop_is_rejected_before_generation(self):
        response = APIClient().post('/api/generate-catalog/', {
            'garment_type': 'blazer', 'garment_style': 'business', 'fabric_image': upload(),
            'gender': 'men', 'options': json.dumps({'fabric_crop_box': [0, 0, 97, 128]}),
        }, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('fabric_crop_box', str(response.json()))

    def test_supported_material_background_and_uploaded_face_options(self):
        definition = get_definition('blazer', 'business-v1')
        for material, (background, scenery), gender in zip(
            FABRIC_TYPES, SCENERY.items(), ('women', 'men', 'boy', 'girl'),
        ):
            with self.subTest(material=material, background=background, gender=gender):
                serializer = CatalogRequestSerializer(data={
                    'garment_type': 'blazer', 'garment_style': 'business',
                    'fabric_image': upload(), 'face_image': upload(), 'gender': gender,
                    'fabric_type': material, 'background': background,
                })
                self.assertTrue(serializer.is_valid(), serializer.errors)
                data = serializer.validated_data
                config = definition.build_config(data, definition.shots[0], 42)
                self.assertEqual(config['fabric_type'], material)
                self.assertIn(scenery, config['prompt'])
                self.assertIn('face, hair and skin tone of image 2', config['prompt'])

    def test_portrait_correction_keeps_background_and_matches_sample(self):
        target = jacket_midtone({'fabric_image': io.BytesIO(picture())})
        generation = GenerationResult(picture((65, 112, 137)), 42)
        result = align_portrait_colour(generation, 'front', target)
        with Image.open(io.BytesIO(result.image_bytes)) as image:
            self.assertEqual(image.getpixel((32, 40)), MIDTONE)
            self.assertEqual(image.getpixel((1, 1)), (65, 112, 137))

    def test_even_exposure_reduces_a_trouser_patch_and_keeps_background(self):
        import numpy as np
        from PIL import ImageDraw
        from fabricapp.ai.garments.blazer.catalog.business_details import TROUSER_REGIONS

        image = Image.new('RGB', (160, 480), '#ebe9e3')
        draw = ImageDraw.Draw(image)
        draw.rectangle((48, 248, 113, 446), fill='#d1bfcf')
        draw.ellipse((67, 273, 101, 303), fill='#a48397')
        data = io.BytesIO()
        image.save(data, 'PNG')
        generation = GenerationResult(data.getvalue(), 42)
        target = np.array([209, 191, 207])
        result = align_portrait_colour(generation, 'trousers', target, region=TROUSER_REGIONS['back'],
                                       soft_edges=True, local_exposure=True, even_exposure=True)
        with Image.open(io.BytesIO(result.image_bytes)) as output:
            patch = np.array(output.getpixel((84, 288)))
            self.assertLess(np.linalg.norm(patch - target), 20)
            self.assertEqual(output.getpixel((20, 285)), image.getpixel((20, 285)))

    def test_shirt_cleanup_lifts_cast_shadow_without_repainting_tie_or_jacket(self):
        from PIL import ImageDraw
        from fabricapp.ai.garments.blazer.catalog.business_details import neutralize_dress_shirt

        image = Image.new('RGB', (200, 480), '#73533d')
        draw = ImageDraw.Draw(image)
        draw.polygon([(77, 95), (122, 95), (118, 130), (103, 181), (96, 181), (82, 130)],
                     fill='#f4f3f3')
        draw.rectangle((84, 120, 106, 139), fill='#a4aabd')
        draw.polygon([(97, 99), (105, 99), (106, 158), (101, 173), (96, 158)], fill='#55402d')
        encoded = io.BytesIO()
        image.save(encoded, 'PNG')
        fixed = neutralize_dress_shirt(GenerationResult(encoded.getvalue(), 42), 'front', (115, 83, 61))
        with Image.open(io.BytesIO(fixed.image_bytes)) as result:
            self.assertGreater(result.getpixel((91, 130))[0], 196)
            self.assertEqual(result.getpixel((101, 129)), image.getpixel((101, 129)))
            self.assertEqual(result.getpixel((64, 124)), image.getpixel((64, 124)))


class CasualBlazerCatalogTests(SimpleTestCase):
    def test_casual_closeups_preserve_reference_neck_and_jacket_silhouette(self):
        from PIL import ImageChops
        from fabricapp.ai.garments.blazer.catalog.casual import DEFINITION
        from fabricapp.catalog_engine.runner import Services, generate_shot

        data = {'fabric_image': io.BytesIO(picture())}
        for shot in (shot for shot in DEFINITION.shots if shot.key in ('lapel', 'pocket')):
            result = generate_shot(data, shot, DEFINITION, {}, {}, Services(None, None, None))
            with Image.open(io.BytesIO(result.image_bytes)) as output, Image.open(shot.reference) as reference, \
                    Image.open(shot.reference_mask) as mask:
                self.assertEqual(output.size, reference.size)
                difference = ImageChops.difference(output, reference.convert('RGB'))
                outside = mask.point(lambda value: 255 if value == 0 else 0)
                self.assertIsNone(Image.composite(difference, Image.new('RGB', output.size), outside).getbbox())
                self.assertIsNotNone(difference.getbbox())

    def test_dark_side_jacket_moves_towards_swatch_without_colour_spilling_into_scene(self):
        import numpy as np
        from PIL import ImageDraw

        image = Image.new('RGB', (200, 480), (230, 223, 204))
        ImageDraw.Draw(image).rectangle((74, 83, 163, 248), fill=(104, 95, 114))
        encoded = io.BytesIO()
        image.save(encoded, 'PNG')
        target = np.array([209, 193, 217])
        source = GenerationResult(encoded.getvalue(), 42)
        corrected = align_portrait_colour(source, 'side', target, soft_edges=True)
        with Image.open(io.BytesIO(corrected.image_bytes)) as output:
            self.assertLess(np.linalg.norm(np.array(output.getpixel((127, 162))) - target), 60)
            self.assertEqual(output.getpixel((38, 160)), image.getpixel((38, 160)))
            self.assertEqual(output.getpixel((127, 270)), image.getpixel((127, 270)))

    def test_each_view_passes_its_style_reference_to_the_model(self):
        styles = {'casual': CASUAL_REFERENCES, 'wedding': WEDDING_REFERENCES}
        for style, source_key in product(styles, ('fabric_image', 'garment_image')):
            with self.subTest(style=style, source=source_key):
                with patch('fabricapp.catalog.generate_edit',
                           return_value=GenerationResult(picture(), 42)) as provider, patch(
                    'fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/catalog.png'},
                ):
                    response = APIClient().post('/api/generate-catalog/', {
                        'garment_type': 'blazer', 'garment_style': style, 'gender': 'men',
                        source_key: upload(),
                    }, format='multipart')
                    self.assertEqual(response.status_code, 200, response.content if not response.streaming else '')
                    events = [json.loads(line) for line in response.streaming_content]

                self.assertEqual(events[0]['catalog_edition'], f'{style}-v1')
                self.assertEqual(events[0]['views'], VIEWS)
                self.assertEqual(events[-1]['status'], 'completed')
                self.assertEqual(events[-1]['collage']['aspect_ratio'], '3:4')
                local_views = ({'wedding': {'cuff', 'pocket'}, 'casual': {'lapel', 'pocket'}}[style]
                               if source_key == 'fabric_image' else set())
                generated_views = [view for view in VIEWS if view not in local_views]
                self.assertEqual(provider.call_count, len(generated_views))
                self.assertEqual({item['view'] for item in events[-1]['images']
                                  if item['operation'] == 'swatch_composite'}, local_views)
                for view, call in zip(generated_views, provider.call_args_list):
                    index = VIEWS.index(view) + 1
                    reference = styles[style] / f'{index:02}_{view}.png'
                    self.assertEqual(reference.name, f'{index:02}_{view}.png')
                    self.assertEqual(call.kwargs['person_image'].getvalue(), reference.read_bytes())
                    self.assertIn(source_key, call.kwargs)
                    prompt = call.kwargs['prompt_config']['prompt']
                    self.assertIn(f'{style.title()} Blazer', prompt)
                    if style == 'wedding' and source_key == 'fabric_image':
                        if view == 'lapel':
                            self.assertIn('gold chain', prompt)
                        if index <= 3:
                            self.assertIn('matching trousers in the same swatch cloth', prompt)
                        if view in ('side', 'back'):
                            self.assertNotEqual(call.kwargs['face_image'].getvalue(), picture())
                            self.assertIn('image 0’s exact', prompt)
                            self.assertIn('already photographed suit', prompt)
                    if index <= 3:
                        self.assertEqual(call.kwargs['pose_reference_path'], reference)
                    else:
                        self.assertEqual(call.kwargs['scenario'], 'person_photo')
                        self.assertNotIn('face_image', call.kwargs)
                        self.assertNotIn('pose_reference_path', call.kwargs)
                        if source_key == 'garment_image':
                            self.assertNotEqual(call.kwargs[source_key].getvalue(), picture())
