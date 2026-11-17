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
from fabricapp.ai.fabric.fabric_material import FABRIC_TYPES
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.ai.scene.backgrounds import BACKGROUND_DESCRIPTIONS
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
            self.assertIn('grand palace courtyard', config['prompt'])
            self.assertIn('Keep a formal tie', config['prompt'])
        self.assertIn('keep the face hidden', calls[-1].kwargs['prompt_config']['prompt'])
        details = [event['image']['generation'] for event in events
                   if event['event'] == 'image_ready' and event['image']['view'] in VIEWS[3:]]
        self.assertEqual(len(details), 3)
        for item in details:
            self.assertEqual(item['kind'], 'swatch_composite')
            self.assertEqual(item['fabric_crop_box'], [4, 6, 88, 120])
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
            FABRIC_TYPES, BACKGROUND_DESCRIPTIONS.items(), ('women', 'men', 'boy', 'girl'),
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


class CasualBlazerCatalogTests(SimpleTestCase):
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
                composited = style == 'wedding' and source_key == 'fabric_image'
                generated_views = VIEWS[:4] if composited else VIEWS
                self.assertEqual(provider.call_count, len(generated_views))
                if composited:
                    self.assertEqual([item['operation'] for item in events[-1]['images'][-2:]],
                                     ['swatch_composite', 'swatch_composite'])
                for index, (view, call) in enumerate(zip(generated_views, provider.call_args_list), 1):
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
                    if index <= 3:
                        self.assertEqual(call.kwargs['pose_reference_path'], reference)
                    else:
                        self.assertEqual(call.kwargs['scenario'], 'person_photo')
                        self.assertNotIn('face_image', call.kwargs)
                        self.assertNotIn('pose_reference_path', call.kwargs)
                        if source_key == 'garment_image':
                            self.assertNotEqual(call.kwargs[source_key].getvalue(), picture())
