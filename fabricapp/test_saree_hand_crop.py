"""The fifth panel reuses front pixels; no independent pose or fabric generation."""
import hashlib
import io
from unittest.mock import Mock

from django.test import SimpleTestCase
from PIL import Image, ImageOps

from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.runner import Services, generate_shot
from fabricapp.ai.garments.saree.catalog.detail_prompts import build_detail_config
from fabricapp.test_catalog_engine import data, picture


class SareeHandCropTests(SimpleTestCase):
    def test_hand_detail_is_exact_front_pixels_for_multiple_fabrics(self):
        definition = get_definition('saree')
        shot = next(s for s in definition.shots if s.key == 'border')
        self.assertEqual(shot.operation, 'crop')
        self.assertEqual(shot.dependencies, ('front',))
        self.assertIsNone(shot.reference)
        for colour in ('teal', 'ivory', 'purple'):
            front = Image.new('RGB', (576, 1920), colour)
            front.paste('magenta', (0, 0, 576, 600))  # Head/shoulder area stays out.
            front.paste('gold', (180, 850, 290, 1020))  # Simulated hands/bangles.
            front.paste('black', (0, 1500, 576, 1920))  # Lower hem stays out.
            output = io.BytesIO(); front.save(output, 'PNG'); source = output.getvalue()
            provider = Mock(side_effect=AssertionError('No AI permitted'))
            result = generate_shot(data(face_choice='anaya'), shot, definition,
                                   {'front': source}, {'front': 314}, Services(provider, provider, provider))
            provider.assert_not_called()
            self.assertEqual(result.effective_seed, 314)
            self.assertEqual(result.diagnostics['source_view'], 'front')
            self.assertEqual(result.diagnostics['source_image_sha256'], hashlib.sha256(source).hexdigest())
            self.assertTrue(result.diagnostics['no_new_ai_generation'])
            box = result.diagnostics['source_crop']
            bounds = tuple(round(v*d) for v, d in zip(box, (576, 1920, 576, 1920)))
            expected = ImageOps.fit(front.crop(bounds), (532, 704), method=Image.Resampling.LANCZOS)
            with Image.open(io.BytesIO(result.image_bytes)) as actual:
                self.assertEqual(actual.tobytes(), expected.tobytes())
            self.assertNotIn('prompt', definition.build_config(data(), shot, 42))

    def test_bounds_and_aspect_follow_source_resolution(self):
        definition = get_definition('saree')
        shot = next(s for s in definition.shots if s.key == 'border')
        for width, height in ((576, 1920), (288, 960), (768, 2048), (256, 1920)):
            box = definition.resolve_crop(data(), shot, picture(size=(width, height)))
            self.assertTrue(0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1)
            aspect = (box[2]-box[0])*width/((box[3]-box[1])*height)
            self.assertAlmostEqual(aspect, 532/704)
            self.assertAlmostEqual(box[3], .61)

    def test_independent_hand_generation_is_rejected(self):
        shot = next(s for s in get_definition('saree').shots if s.key == 'border')
        with self.assertRaisesRegex(ValueError, 'cropped from the generated front'):
            build_detail_config(data(), shot, 42)
