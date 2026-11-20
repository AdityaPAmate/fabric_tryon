"""Hand-drape reference routing and product fidelity without paid inference."""
import io
from unittest.mock import Mock

from django.test import SimpleTestCase

from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.runner import Services, generate_shot
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.test_catalog_engine import data, picture


class SareeHandDrapeTests(SimpleTestCase):
    def test_user_reference_is_sent_unchanged_without_face_or_border_extraction(self):
        definition = get_definition('saree')
        shot = next(s for s in definition.shots if s.key == 'border')
        for colour in ('blue', 'purple'):
            fabric = picture(colour)
            request = data(fabric_image=io.BytesIO(fabric), person_image=io.BytesIO(picture()),
                           face_choice='anaya', options={'fabric_body_crop_box': [0, 0, 40, 80],
                                                        'fabric_border_crop_box': [0, 0, 10, 80]})
            edit = Mock(return_value=GenerationResult(picture(), 42))
            result = generate_shot(request, shot, definition, {}, {}, Services(None, edit, None))
            self.assertEqual(result.image_bytes, picture())
            kwargs = edit.call_args.kwargs
            self.assertNotIn('face_image', kwargs); self.assertNotIn('face_choice', kwargs)
            self.assertEqual(kwargs['person_image'].getvalue(), shot.reference.read_bytes())
            self.assertEqual(kwargs['fabric_image'].getvalue(), fabric)
            self.assertEqual(shot.reference.name, '05_hand_drape.png')
            self.assertIsNone(kwargs['prompt_config']['fabric_crop_box'])
            self.assertNotIn('fabric_reference_crops', kwargs['prompt_config'])
            self.assertEqual(kwargs['prompt_config']['fabric_region'], 'hand_drape')
            self.assertEqual(edit.call_count, 1)

    def test_prompt_preserves_hands_and_replaces_all_template_textile(self):
        definition = get_definition('saree')
        shot = next(s for s in definition.shots if s.key == 'border')
        config = definition.build_config(data(), shot, 42)
        for instruction in ('two hands', 'Replace ALL visible saree cloth',
                            'Remove every template red/maroon patch',
                            'Do not paste fabric over skin or bangles', 'no sunlight'):
            self.assertIn(instruction, config['prompt'])
        self.assertEqual(config['prompt_version'], 'saree-hand-drape-v1')
        self.assertNotIn('TOP LEFT to BOTTOM RIGHT', config['prompt'])
