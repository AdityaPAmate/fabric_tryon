"""Material contract, prompt isolation and API-to-builder plumbing."""
import io
from itertools import product
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image
from rest_framework.test import APIRequestFactory

from .ai.blazer.builder import build_prompt
from .ai.blazer.materials import MATERIAL_PROMPTS, material_prompt
from .ai.cloudflare_engine import GenerationResult, CloudflareGenerationError
from .ai.main import generate_tryon_image
from .ai.router import PromptRoutingError
from .serializers import FabricTryOnRequestSerializer
from .views import FabricTryOnView


def swatch():
    data = io.BytesIO(); Image.new('RGB', (32, 32), (82, 14, 22)).save(data, format='PNG')
    return SimpleUploadedFile('swatch.png', data.getvalue(), content_type='image/png')


class FabricMaterialTests(SimpleTestCase):
    def payload(self, **extra):
        return dict(fabric_image=swatch(), garment_type='blazer',
                    garment_style='business', gender='men', **extra)

    def test_omitted_and_explicit_unspecified_preserve_prompts(self):
        for scenario, style in product(
            ('person_photo', 'person_pose', 'face_photo', 'generated_person'),
            ('business', 'wedding', 'casual'),
        ):
            context = {'fabric_image': swatch(), 'background': 'white_marble_terrace'}
            old = build_prompt(scenario=scenario, garment_style=style, context=context)
            explicit = build_prompt(scenario=scenario, garment_style=style,
                                    context=dict(context, fabric_type='unspecified'))
            self.assertEqual(old, explicit)
            self.assertNotIn('MATERIAL:', old['prompt'])
        serializer = FabricTryOnRequestSerializer(data=self.payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['fabric_type'], 'unspecified')

    def test_all_materials_keep_colour_and_retry_contracts(self):
        for scenario, style, material in product(
            ('person_photo', 'person_pose', 'face_photo', 'generated_person'),
            ('business', 'wedding', 'casual'), MATERIAL_PROMPTS,
        ):
            with self.subTest(scenario=scenario, style=style, material=material):
                context = {'fabric_image': swatch(), 'background': 'white_marble_terrace'}
                original = build_prompt(scenario=scenario, garment_style=style, context=context, seed=17, guidance=5)
                selected = build_prompt(scenario=scenario, garment_style=style,
                                        context=dict(context, fabric_type=material), seed=17, guidance=5)
                self.assertEqual(selected['fabric_colour_reference'], original['fabric_colour_reference'])
                self.assertEqual((selected['seed'], selected['guidance']), (17, 5))
                self.assertEqual(selected['fabric_type'], material)
                self.assertEqual(selected['prompt_version'], 'blazer-material-v1-' + material)
                for key in ('prompt', 'safety_fallback_prompt'):
                    self.assertEqual(selected[key].count('MATERIAL:'), 1)
                    self.assertEqual(selected[key].replace(material_prompt(material), ''), original[key])

    def test_serializer_rejects_invalid_and_unsupported_material_requests(self):
        for material in ('', 'leather', 'VELVET', None):
            serializer = FabricTryOnRequestSerializer(data=self.payload(fabric_type=material))
            self.assertFalse(serializer.is_valid())
            self.assertIn('fabric_type', serializer.errors)
        for garment in ('shirt', 'kurta', 'saree'):
            data = {'fabric_image': swatch(), 'garment_type': garment,
                    'gender': 'women', 'fabric_type': 'silk'}
            if garment == 'kurta': data['garment_style'] = 'plain'
            serializer = FabricTryOnRequestSerializer(data=data)
            self.assertFalse(serializer.is_valid())
            self.assertIn('fabric_type', serializer.errors)
        serializer = FabricTryOnRequestSerializer(data={
            'garment_image': swatch(), 'gender': 'men', 'fabric_type': 'velvet'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('fabric_type', serializer.errors)

    def test_unspecified_is_backwards_compatible_for_other_garments(self):
        for data in ({'fabric_image': swatch(), 'garment_type': 'shirt', 'gender': 'men'},
                     {'garment_image': swatch(), 'gender': 'men'}):
            serializer = FabricTryOnRequestSerializer(data=data)
            self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data['fabric_type'], 'unspecified')

    def test_direct_callers_cannot_silently_ignore_invalid_material(self):
        with self.assertRaises(PromptRoutingError):
            build_prompt(scenario='face_photo', garment_style='business', context={'fabric_type': 'unknown'})
        with self.assertRaises(PromptRoutingError):
            build_prompt(scenario='face_photo', use_garment_image=True, context={'fabric_type': 'silk'})
        with patch('fabricapp.ai.main._generate_with_engine') as engine:
            with self.assertRaises(CloudflareGenerationError):
                generate_tryon_image(garment_type='shirt', fabric_type='silk')
            engine.assert_not_called()

    def test_main_delivers_material_to_both_provider_prompt_variants(self):
        with patch('fabricapp.ai.main._generate_with_engine') as engine:
            generate_tryon_image(fabric_image=swatch(), garment_type='blazer', garment_style='business',
                                 gender='men', fabric_type='velvet')
        config = engine.call_args.kwargs['prompt_config']
        self.assertEqual(config['fabric_type'], 'velvet')
        for key in ('prompt', 'safety_fallback_prompt'):
            self.assertIn('dense short plush pile', config[key])
            self.assertIn('COLOUR REFERENCE:', config[key])

    def test_http_request_reaches_actual_builder_and_echoes_selected_material(self):
        factory = APIRequestFactory()
        for material in ('unspecified', 'cotton', 'silk', 'velvet'):
            with self.subTest(material=material):
                with patch('fabricapp.ai.main._generate_with_engine', return_value=GenerationResult(b'image', 42)) as engine, \
                     patch('fabricapp.views.upload_generated_image', return_value={'url': 'https://example.test/output.png'}):
                    response = FabricTryOnView.as_view()(factory.post(
                        '/api/replace-fabric/', self.payload(fabric_type=material), format='multipart'))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['fabric_type'], material)
                config = engine.call_args.kwargs['prompt_config']
                self.assertEqual(config['fabric_type'], material)
                self.assertEqual('MATERIAL:' in config['prompt'], material != 'unspecified')

    def test_invalid_http_material_does_not_generate_or_upload(self):
        with patch('fabricapp.views.generate_tryon_image') as generate, \
             patch('fabricapp.views.upload_generated_image') as upload:
            response = FabricTryOnView.as_view()(APIRequestFactory().post(
                '/api/replace-fabric/', self.payload(fabric_type='unknown'), format='multipart'))
        self.assertEqual(response.status_code, 400)
        self.assertIn('fabric_type', response.data)
        generate.assert_not_called(); upload.assert_not_called()
