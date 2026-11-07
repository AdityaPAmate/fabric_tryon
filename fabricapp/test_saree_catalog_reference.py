"""Reference routing, real side-border shots and exact 9:16 export contracts."""
import io
import threading
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase
from PIL import Image, ImageDraw

from fabricapp.ai.garments.saree.builder import build_prompt as normal_builder
from fabricapp.ai.garments.saree.poses import get_pose_parts
from fabricapp.ai.references.pose_reference import get_pose_reference_path
from fabricapp.catalog_engine.registry import get_definition, DEFAULTS
from fabricapp.catalog_engine.renderer import render_catalog
from fabricapp.ai.providers.cloudflare_engine import GenerationResult, CloudflareGenerationError
from fabricapp.catalog import generate_catalog
from fabricapp.test_catalog_engine import data, picture, post


class SareeCatalogReferenceTests(SimpleTestCase):
    def test_back_reuses_the_normal_builder_and_identical_reference(self):
        definition = get_definition('saree')
        shot = next(shot for shot in definition.shots if shot.key == 'back_pallu')
        with patch('fabricapp.ai.garments.saree.builder.build_prompt', wraps=normal_builder) as shared:
            config = definition.build_config(data(), shot, 71)
        shared.assert_called_once()
        args = shared.call_args.kwargs
        self.assertEqual(args['scenario'], 'pose_reference')
        self.assertEqual(args['context']['pose'], 'back_showing_pallu')
        self.assertFalse(args['context']['use_face_reference'])
        self.assertIsNone(shot.identity_from)
        self.assertEqual(shot.dependencies, ())
        self.assertTrue(config['forbid_identity_references'])
        self.assertNotIn('image 2', config['prompt'].lower())
        expected = normal_builder(scenario='pose_reference', garment_type='saree', context=args['context'], seed=71)
        self.assertEqual(config['prompt'], expected['prompt'])
        self.assertEqual(config['seed'], 71)
        self.assertEqual(shot.reference.read_bytes(), Path(get_pose_reference_path('saree', 'back_showing_pallu')).read_bytes())
        self.assertIn('BACK-PALLU GEOMETRY LOCK', config['prompt'])
        self.assertIn('both arms and hands', config['prompt'])

    @patch('fabricapp.ai.main._generate_with_engine')
    def test_normal_endpoint_rejects_face_or_person_inputs_for_back_pose(self, engine):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rest_framework.test import APIClient
        for field in ('face_image', 'face_choice', 'person_image'):
            request = {'fabric_image': SimpleUploadedFile('fabric.png', picture(), content_type='image/png'),
                       'garment_type': 'saree', 'pose': 'back_showing_pallu'}
            if field != 'person_image':
                request['gender'] = 'women'
            request[field] = 'anaya' if field == 'face_choice' else SimpleUploadedFile('identity.png', picture(), content_type='image/png')
            response = APIClient().post('/api/replace-fabric/', request, format='multipart')
            self.assertEqual(response.status_code, 400, field)
        engine.assert_not_called()

    @patch('fabricapp.ai.main._generate_with_engine')
    def test_ready_garment_mode_cannot_bypass_no_identity_pose_rule(self, engine):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from rest_framework.test import APIClient
        response = APIClient().post('/api/replace-fabric/', {
            'garment_image': SimpleUploadedFile('garment.png', picture(), content_type='image/png'),
            'pose': 'back_showing_pallu', 'gender': 'women', 'face_choice': 'anaya',
        }, format='multipart')
        self.assertEqual(response.status_code, 400)
        engine.assert_not_called()

    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_provider_guard_rejects_identity_even_if_api_validation_is_bypassed(self, provider):
        from fabricapp.ai.providers.cloudflare_engine import generate_tryon_image
        definition = get_definition('saree')
        shot = next(shot for shot in definition.shots if shot.key == 'back_pallu')
        config = definition.build_config(data(), shot, 42)
        with self.assertRaises(CloudflareGenerationError):
            generate_tryon_image(garment_type='saree', fabric_image=io.BytesIO(picture()),
                                 face_image=io.BytesIO(picture()), pose_reference_path=shot.reference,
                                 scenario='pose_reference', prompt_config=config)
        provider.assert_not_called()

    def test_back_pose_no_longer_contains_placeholder_instructions(self):
        parts = get_pose_parts('back_showing_pallu')
        self.assertNotIn('Describe the exact', str(parts))
        self.assertIn('torso facing away', str(parts))
        self.assertIn('broad', str(parts))

    def test_border_is_a_side_edge_generation_not_a_body_crop(self):
        definition = get_definition('saree')
        shot = next(shot for shot in definition.shots if shot.key == 'border')
        self.assertEqual(shot.operation, 'template_edit')
        self.assertEqual(shot.dependencies, ())
        self.assertIsNone(shot.source_crop)
        config = definition.build_config(data(), shot, 42)
        self.assertIn('LONG SIDE BORDER / SELVEDGE', config['prompt'])
        self.assertIn('not the main body print', config['prompt'])
        self.assertIn('plain narrow stitched selvedge', config['prompt'])

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.test/a.png'})
    @patch('fabricapp.catalog.generate_edit')
    def test_border_still_runs_if_pallu_generation_fails(self, edit, upload):
        edit.side_effect = [GenerationResult(picture(), 42)] * 4 + [CloudflareGenerationError('pallu failed')] + [GenerationResult(picture(), 42)] * 2
        events = list(generate_catalog(data(), threading.Event()))
        self.assertEqual(events[-1]['failed_views'], ['pallu'])
        self.assertIn('border', [image['view'] for image in events[-1]['images']])
        self.assertEqual(edit.call_count, 7)

    def test_all_default_catalog_exports_are_exactly_9_by_16(self):
        for garment in DEFAULTS:
            layout = get_definition(garment).layout({})
            self.assertEqual(layout.size[0] * 16, layout.size[1] * 9, garment)
        self.assertEqual(get_definition('saree').layout({}).size, (1800, 3200))

    def test_back_and_border_edges_are_not_cropped_away_by_composition(self):
        definition = get_definition('saree')
        layout = definition.layout({})
        shots = {shot.key: picture() for shot in definition.shots}
        for key in ('back_pallu', 'border'):
            panel = next(panel for panel in layout.panels if panel.shot == key)
            self.assertEqual(panel.fit, 'contain')
            image = Image.new('RGB', (400, 400), 'blue')
            ImageDraw.Draw(image).rectangle((0, 0, 399, 399), outline='red', width=12)
            buffer = io.BytesIO(); image.save(buffer, 'PNG'); shots[key] = buffer.getvalue()
        output = Image.open(io.BytesIO(render_catalog(shots, b'', layout)))
        self.assertEqual(output.size, (1800, 3200))
        for key in ('back_pallu', 'border'):
            left, top, right, bottom = next(panel.box for panel in layout.panels if panel.shot == key)
            side = min(right-left, bottom-top)
            x, y = left + (right-left-side)//2, top + (bottom-top-side)//2
            for point in ((x+2, y+side//2), (x+side-3, y+side//2),
                          (x+side//2, y+2), (x+side//2, y+side-3)):
                self.assertGreater(output.getpixel(point)[0], 200)
                self.assertLess(output.getpixel(point)[2], 60)
