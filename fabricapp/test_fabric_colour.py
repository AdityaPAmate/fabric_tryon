import io
from unittest import TestCase
from PIL import Image

from .ai.fabric_colour import measure_fabric_colours, colour_reference_prompt, has_single_colour_family
from .ai.blazer.builder import build_prompt


def image_buffer(rgb, size=(32, 32)):
    stream = io.BytesIO()
    Image.new('RGB', size, rgb).save(stream, format='PNG')
    stream.seek(0)
    return stream


class FabricColourTests(TestCase):
    def test_rollout_groups_tonal_variants_but_not_distinct_colours(self):
        profile = {'colours': [{'name': 'light lavender-purple'}, {'name': 'light muted lavender-purple'}]}
        self.assertTrue(has_single_colour_family(profile))
        self.assertFalse(has_single_colour_family({'colours': [{'name': 'muted blue'}, {'name': 'grey'}]}))

    def test_tonal_variants_use_one_colour_reference_instead_of_a_long_palette(self):
        image = Image.new('RGB', (40, 20), (188, 171, 196))
        image.paste(Image.new('RGB', (20, 20), (234, 217, 241)), (20, 0))
        source = io.BytesIO(); image.save(source, format='PNG'); source.seek(0)
        profile = measure_fabric_colours(source)
        reference = colour_reference_prompt(profile)
        self.assertTrue(has_single_colour_family(profile))
        self.assertIn('the jacket fabric is light lavender-purple', reference)
        self.assertNotIn('about', reference)

    def test_light_purple_stays_purple_and_stream_position_is_restored(self):
        source = image_buffer((209, 193, 217))
        source.seek(7)
        profile = measure_fabric_colours(source)
        self.assertEqual(source.tell(), 7)
        self.assertEqual(profile['colours'][0]['rgb'], [209, 193, 217])
        self.assertIn('lavender-purple', profile['colours'][0]['name'])

    def test_crop_controls_palette_instead_of_unselected_colour(self):
        image = Image.new('RGB', (40, 20), 'red')
        image.paste(Image.new('RGB', (20, 20), 'blue'), (20, 0))
        source = io.BytesIO(); image.save(source, format='PNG'); source.seek(0)
        profile = measure_fabric_colours(source, [20, 0, 40, 20])
        self.assertEqual(profile['colours'][0]['rgb'], [0, 0, 255])
        self.assertEqual(profile['colours'][0]['coverage'], 1)
        source.seek(0)
        profile = measure_fabric_colours(source)
        self.assertEqual({tuple(c['rgb']) for c in profile['colours']}, {(255, 0, 0), (0, 0, 255)})
        self.assertIn('does not replace the pattern', colour_reference_prompt(profile))

    def test_single_family_reference_is_automatic_and_identical_in_both_retry_variants(self):
        source = image_buffer((209, 193, 217))
        normal = build_prompt(scenario='face_photo', garment_style='business',
                              context={})
        candidate = build_prompt(scenario='face_photo', garment_style='business',
                                 context={'fabric_image': source})
        reference = colour_reference_prompt(candidate['fabric_colour_reference'])
        for key in ('prompt', 'safety_fallback_prompt'):
            self.assertEqual(candidate[key].count('COLOUR REFERENCE:'), 1)
            self.assertEqual(candidate[key].replace(reference, ''), normal[key])
        self.assertNotIn('fabric_colour_reference', normal)
        self.assertEqual(candidate['prompt_version'], 'blazer-colour-v5')
        self.assertEqual(source.tell(), 0)

    def test_multicolour_pattern_is_not_automatically_rolled_out(self):
        image = Image.new('RGB', (40, 20), 'red')
        image.paste(Image.new('RGB', (20, 20), 'blue'), (20, 0))
        source = io.BytesIO(); image.save(source, format='PNG'); source.seek(0)
        normal = build_prompt(scenario='face_photo', garment_style='business',
                              context={'fabric_image': source})
        candidate = build_prompt(scenario='face_photo', garment_style='business',
                                 context={'fabric_image': source, '_colour_reference_experiment': True})
        self.assertNotIn('COLOUR REFERENCE:', normal['prompt'])
        self.assertIn('COLOUR REFERENCE:', candidate['prompt'])
        self.assertEqual(candidate['prompt_version'], 'blazer-colour-experiment-v2')

    def test_crop_is_honoured_by_builder_and_context_not_mutated(self):
        source = image_buffer((209, 193, 217))
        context = {'fabric_image': source, 'options': {'fabric_crop_box': [1, 1, 20, 20]}}
        for scenario in ('person_photo', 'person_pose', 'face_photo', 'generated_person'):
            config = build_prompt(scenario=scenario, garment_style='casual', context=context)
            self.assertEqual(config['fabric_colour_reference']['crop_box'], [1, 1, 20, 20])
            self.assertNotIn('_fabric_colour_profile', context)
            self.assertEqual(source.tell(), 0)

    def test_invalid_source_restores_position_and_missing_source_keeps_original_route(self):
        source = io.BytesIO(b'invalid image'); source.seek(3)
        with self.assertRaises(OSError):
            measure_fabric_colours(source)
        self.assertEqual(source.tell(), 3)
        config = build_prompt(scenario='person_photo', garment_style='business',
                              context={'_colour_reference_experiment': True})
        self.assertNotIn('COLOUR REFERENCE:', config['prompt'])
