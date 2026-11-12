"""Reference routing, real side-border shots and exact 3:4 export contracts."""
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
    def test_side_uses_its_own_template_and_only_explicit_identity_inputs(self):
        definition = get_definition('saree')
        shot = next(shot for shot in definition.shots if shot.key == 'side_portrait')
        self.assertEqual(shot.operation, 'template_edit')
        self.assertEqual(shot.dependencies, ())
        self.assertEqual(shot.identity_from, 'request')
        without_identity = definition.build_config(data(), shot, 42)
        self.assertIn('Keep the person, face, hairstyle and skin tone already in image 0', without_identity['prompt'])
        self.assertNotIn('Image 2', without_identity['prompt'])
        with_identity = definition.build_config(data(face_choice='anaya'), shot, 42)
        self.assertIn('Image 2 supplies only the requested face/hair identity', with_identity['prompt'])
        self.assertNotIn('Image 3', with_identity['prompt'])

    def test_catalog_contains_only_the_six_numbered_replacement_assets(self):
        import hashlib
        import json
        definition = get_definition('saree')
        root = definition.shots[0].reference.parent
        expected = {'01_front_pallu.png', '02_three_quarter.png', '03_back_view.png',
                    '04_fabric_texture.png', '05_border_closeup.png', '06_pleats_hem.png'}
        self.assertEqual({shot.reference.name for shot in definition.shots}, expected)
        self.assertEqual({path.name for path in root.iterdir() if path.suffix in ('.png', '.jpg', '.jpeg')}, expected)
        manifest = json.loads((root / 'manifest.json').read_text())
        for filename in expected:
            self.assertEqual(hashlib.sha256((root / filename).read_bytes()).hexdigest(), manifest[filename]['sha256'])

    def test_back_reuses_normal_builder_with_new_catalog_reference(self):
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
        self.assertEqual(shot.reference.name, '03_back_view.png')
        self.assertTrue(Path(get_pose_reference_path('saree', 'back_showing_pallu')).is_file())
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
        self.assertIn('plain finished edge', config['prompt'])

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.test/a.png'})
    @patch('fabricapp.catalog.generate_edit')
    def test_border_still_runs_if_texture_generation_fails(self, edit, upload):
        edit.side_effect = [GenerationResult(picture(), 42)] * 3 + [CloudflareGenerationError('texture failed')] + [GenerationResult(picture(), 42)] * 2
        events = list(generate_catalog(data(), threading.Event()))
        self.assertEqual(events[-1]['failed_views'], ['fabric_texture'])
        self.assertIn('border', [image['view'] for image in events[-1]['images']])
        self.assertEqual(edit.call_count, 6)

    def test_editorial_catalogs_are_3_by_4_and_other_defaults_are_9_by_16(self):
        for garment in DEFAULTS:
            layout = get_definition(garment).layout({})
            ratio = (3, 4) if garment in ('saree', 'kurti_pant') else (9, 16)
            self.assertEqual(layout.size[0] * ratio[1], layout.size[1] * ratio[0], garment)
        self.assertEqual(get_definition('saree').layout({}).size, (1800, 2400))

    def test_layout_matches_reference_crops_and_has_no_header_footer_or_unused_space(self):
        definition = get_definition('saree')
        layout = definition.layout({'title': 'MUST NOT APPEAR', 'product_name': 'HIDDEN'})
        self.assertEqual(layout.texts, ())
        self.assertEqual(layout.lines, ())
        self.assertIsNone(layout.swatch_box)
        self.assertEqual(len(layout.panels), 6)
        colors = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta']
        shots = {shot.key: picture(color) for shot, color in zip(definition.shots, colors)}
        output = Image.open(io.BytesIO(render_catalog(shots, b'', layout)))
        self.assertEqual(output.size, (1800, 2400))
        used_area = 0
        for panel, color in zip(layout.panels, colors):
            left, top, right, bottom = panel.box
            self.assertEqual(panel.fit, 'cover')
            self.assertEqual(output.getpixel(((left+right)//2, (top+bottom)//2)),
                             Image.new('RGB', (1, 1), color).getpixel((0, 0)))
            used_area += (right-left)*(bottom-top)
            reference = next(shot.reference for shot in definition.shots if shot.key == panel.shot)
            with Image.open(reference) as image:
                self.assertLess(abs((image.width/image.height)/((right-left)/(bottom-top))-1), .06)
        from collections import Counter
        self.assertEqual(Counter(output.getdata())[(255, 255, 255)], 1800*2400-used_area)
