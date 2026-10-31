"""Cross-garment material/colour contracts through public routing and HTTP."""
import io
from itertools import product
from unittest.mock import patch
from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIRequestFactory

from .ai.router import build_prompt_config, IMPLEMENTED_GARMENT_TYPES, PromptRoutingError
from .ai.fabric_material import SUPPORTED_GARMENTS, FABRIC_TYPES, fabric_target, material_prompt
from .ai.fabric_colour import colour_reference_prompt
from .ai.cloudflare_engine import GenerationResult
from .views import FabricTryOnView


STYLES = {'blazer': ('business', 'wedding', 'casual'),
          'kurta': ('plain', 'sherwani', 'pathani', 'jodhpuri'),
          'shirt': (None,), 'kurti_pant': (None,), 'pant': (None,), 'saree': (None,)}


def swatch():
    buffer = io.BytesIO(); Image.new('RGB', (40, 40), (209, 193, 217)).save(buffer, format='PNG')
    return SimpleUploadedFile('purple.png', buffer.getvalue(), content_type='image/png')


def config(garment, style, scenario, context):
    return build_prompt_config(scenario=scenario, garment_type=garment,
                               garment_style=style, context=context, seed=19, guidance=4.5)


class AllGarmentFabricTests(SimpleTestCase):
    def test_contract_covers_all_implemented_garments(self):
        self.assertEqual(SUPPORTED_GARMENTS, IMPLEMENTED_GARMENT_TYPES)

    def test_every_style_route_and_material_keeps_colour_and_construction(self):
        for garment, styles in STYLES.items():
            for style, scenario in product(styles, ('person_photo', 'person_pose', 'face_photo', 'generated_person')):
                context = {'gender': 'women' if garment in ('saree', 'kurti_pant') else 'men',
                           'fabric_image': swatch(), 'camera_view': 'front', 'body_type': 'trim'}
                source = context['fabric_image']; source.seek(7)
                normal = config(garment, style, scenario, context)
                self.assertEqual(source.tell(), 7)
                self.assertEqual(normal['prompt'].count('COLOUR REFERENCE:'), 1)
                self.assertIn('lavender-purple', normal['prompt'])
                for material in ('cotton', 'silk', 'velvet'):
                    with self.subTest(garment=garment, style=style, scenario=scenario, material=material):
                        chosen = config(garment, style, scenario, dict(context, fabric_type=material))
                        self.assertEqual((chosen['seed'], chosen['guidance']), (19, 4.5))
                        self.assertEqual(chosen['fabric_type'], material)
                        self.assertEqual(chosen['fabric_colour_reference'], normal['fabric_colour_reference'])
                        for key in ('prompt', 'safety_fallback_prompt'):
                            if key not in normal: continue
                            self.assertEqual(chosen[key].count('MATERIAL:'), 1)
                            self.assertEqual(chosen[key].count('COLOUR REFERENCE:'), 1)
                            self.assertEqual(chosen[key].replace(material_prompt(material, garment, style), ''), normal[key])
                            if garment not in ('blazer', 'kurta'):
                                prefix = material_prompt(material, garment, style)
                                self.assertNotIn('lapels', prefix)
                                self.assertNotIn('jacket', prefix)
                        self.assertEqual(source.tell(), 7)
                self.assertNotIn('_fabric_colour_profile', context)

    def test_nonblazer_conditioning_preserves_the_entire_original_prompt(self):
        for garment in ('kurta', 'kurti_pant', 'pant', 'saree', 'shirt'):
            style = 'plain' if garment == 'kurta' else None
            context = {'gender': 'women' if garment in ('saree', 'kurti_pant') else 'men', 'body_type': 'trim'}
            normal = config(garment, style, 'generated_person', context)
            chosen = config(garment, style, 'generated_person', dict(context, fabric_image=swatch(), fabric_type='silk'))
            target = fabric_target(garment, style)
            colour = colour_reference_prompt(chosen['fabric_colour_reference'], target)
            prefix = colour + material_prompt('silk', garment, style)
            for key in ('prompt', 'safety_fallback_prompt'):
                if key in normal:
                    self.assertTrue(chosen[key].startswith(prefix))
                    self.assertEqual(chosen[key][len(prefix):], normal[key])

    def test_shirt_new_colour_reference_replaces_legacy_palette_only_for_single_family(self):
        result = config('shirt', None, 'face_photo', {'gender': 'men', 'fabric_image': swatch()})
        self.assertIn('COLOUR REFERENCE:', result['prompt'])
        self.assertNotIn('SWATCH PALETTE:', result['prompt'])
        image = Image.new('RGB', (40, 20), 'blue'); image.paste(Image.new('RGB', (20, 20), 'red'), (20, 0))
        buffer = io.BytesIO(); image.save(buffer, format='PNG'); buffer.seek(0)
        result = config('shirt', None, 'face_photo', {'gender': 'men', 'fabric_image': buffer})
        self.assertIn('SWATCH PALETTE:', result['prompt'])
        self.assertNotIn('COLOUR REFERENCE:', result['prompt'])

    def test_targets_keep_separate_garments_out_of_the_surface_override(self):
        for garment in ('kurta', 'kurti_pant'):
            normal = fabric_target(garment, 'plain' if garment == 'kurta' else None)
            self.assertNotIn('pant', normal)
            self.assertIn('selected matching dupatta', fabric_target(garment, garment_details=['with_dupatta']))
            self.assertNotIn('dupatta', fabric_target(garment, garment_details=['with_dupatta'], pose='pallu_on_head'))
        self.assertEqual(fabric_target('pant'), 'trousers')
        self.assertEqual(fabric_target('saree'), 'saree body and pallu')
        for fabric_type in ('cotton', 'silk', 'velvet'):
            text = material_prompt(fabric_type, 'pant')
            self.assertIn('two separate trouser legs', text)
            self.assertIn('gender, age, body build and camera framing', text)

    def test_saree_reference_pose_keeps_drape_and_final_rules(self):
        context = {'gender': 'women', 'pose': 'pallu_on_head'}
        normal = config('saree', None, 'pose_reference', context)
        chosen = config('saree', None, 'pose_reference', dict(context, fabric_image=swatch(), fabric_type='silk'))
        prefix = colour_reference_prompt(chosen['fabric_colour_reference'], 'saree body and pallu') + material_prompt('silk', 'saree', pose='pallu_on_head')
        self.assertEqual(chosen['prompt'], prefix + normal['prompt'])
        self.assertNotIn('lapels', prefix)

    def test_all_http_material_choices_reach_actual_builders(self):
        factory = APIRequestFactory()
        for garment, material in product(STYLES, FABRIC_TYPES):
            with self.subTest(garment=garment, material=material):
                payload = {'fabric_image': swatch(), 'garment_type': garment,
                           'gender': 'women' if garment in ('saree', 'kurti_pant') else 'men',
                           'fabric_type': material}
                if garment in ('blazer', 'kurta'): payload['garment_style'] = STYLES[garment][0]
                with patch('fabricapp.ai.main._generate_with_engine', return_value=GenerationResult(b'image',19)) as engine, \
                     patch('fabricapp.views.upload_generated_image', return_value={'url':'https://example.test/result.png'}):
                    response = FabricTryOnView.as_view()(factory.post('/api/replace-fabric/', payload, format='multipart'))
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data['fabric_type'], material)
                prompt = engine.call_args.kwargs['prompt_config']['prompt']
                self.assertEqual('MATERIAL:' in prompt, material != 'unspecified')
                self.assertEqual(prompt.count('COLOUR REFERENCE:'), 1)

    def test_garment_image_and_direct_router_cannot_silently_override_material(self):
        for garment in STYLES:
            with self.assertRaises(PromptRoutingError):
                build_prompt_config(scenario='generated_person', garment_type=garment,
                                    use_garment_image=True, context={'fabric_type': 'silk'})
        with patch('fabricapp.views.generate_tryon_image') as generate:
            response = FabricTryOnView.as_view()(APIRequestFactory().post('/api/replace-fabric/',
                {'garment_image': swatch(), 'gender': 'men', 'fabric_type': 'silk'}, format='multipart'))
        self.assertEqual(response.status_code, 400)
        generate.assert_not_called()
