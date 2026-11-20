"""Production border inputs and isolation; no paid inference."""
import io
from unittest.mock import Mock

from django.test import SimpleTestCase
from PIL import Image

from fabricapp.ai.garments.saree.catalog.border_ai import prepare_edit_inputs
from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.runner import Services, generate_shot
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.test_catalog_engine import data, picture


class SareeBorderAITests(SimpleTestCase):
    def test_border_uses_product_pixels_not_old_template_or_identity(self):
        image = Image.new('RGB', (200, 800), 'red')
        image.paste('blue', (0, 0, 40, 800))
        image.paste('yellow', (0, 0, 40, 400))
        buffer = io.BytesIO(); image.save(buffer, 'PNG'); buffer.seek(0)
        definition = get_definition('saree')
        shot = next(s for s in definition.shots if s.key == 'border')
        request = data(fabric_image=buffer, person_image=io.BytesIO(picture()), face_choice='anaya',
                       options={'fabric_border_crop_box': [0, 0, 40, 800],
                                'fabric_body_crop_box': [80, 0, 200, 800]})
        subjects = []
        for rotation in (0, 180):
            request['options']['fabric_border_rotation'] = rotation
            edit = Mock(return_value=GenerationResult(picture(), 42))
            result = generate_shot(request, shot, definition, {}, {}, Services(None, edit, None))
            self.assertEqual(result.image_bytes, picture())  # Return AI result, not cropped pixels.
            kwargs = edit.call_args.kwargs
            self.assertNotIn('face_image', kwargs); self.assertNotIn('face_choice', kwargs)
            self.assertNotEqual(kwargs['person_image'].getvalue(), shot.reference.read_bytes())
            with Image.open(kwargs['fabric_image']) as detail:
                self.assertLessEqual(detail.height, detail.width * 4)
                self.assertNotIn((255, 0, 0), detail.getdata())
                subjects.append(detail.copy())
            self.assertIsNone(kwargs['prompt_config']['fabric_crop_box'])
            self.assertIn('TOP LEFT to BOTTOM RIGHT', kwargs['prompt_config']['prompt'])
            self.assertEqual(edit.call_count, 1)
        self.assertEqual(subjects[0].getpixel((20, 5)), subjects[1].getpixel((20, 154)))
        self.assertEqual(buffer.tell(), 0)

    def test_other_shots_bypass_input_hook(self):
        definition = get_definition('saree')
        for shot in definition.shots:
            if shot.key == 'border':
                continue
            source, fabric = b'original', io.BytesIO(b'fabric')
            actual = prepare_edit_inputs({}, shot, source, fabric)
            self.assertEqual(actual[0], source); self.assertIs(actual[1], fabric)

