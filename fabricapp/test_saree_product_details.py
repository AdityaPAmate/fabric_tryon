"""Original product fidelity and fail-closed catalog-back privacy, without paid AI."""
import io
from dataclasses import replace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from PIL import Image

from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.runner import Services, generate_shot
from fabricapp.catalog_engine.validation import validate_definition
from fabricapp.ai.providers.cloudflare_engine import CloudflareGenerationError, generate_tryon_image
from fabricapp.test_catalog_engine import data, picture


class SareeProductDetailTests(SimpleTestCase):
    def test_full_photo_keeps_all_four_coloured_corners_despite_body_crop(self):
        source = Image.new('RGB', (532, 820), 'purple')
        for box, colour in [((0,0,20,20),'red'),((512,0,532,20),'green'),
                            ((0,800,20,820),'blue'),((512,800,532,820),'yellow')]:
            source.paste(colour, box)
        payload = io.BytesIO(); source.save(payload, 'PNG'); payload.seek(0)
        definition = get_definition('saree')
        shot = next(s for s in definition.shots if s.key == 'fabric_texture')
        provider = Mock(side_effect=AssertionError('Product photo must not use AI'))
        result = generate_shot(data(fabric_image=payload, options={'fabric_body_crop_box':[100,100,200,300]}),
                               shot, definition, {}, {}, Services(None,provider,None))
        with Image.open(io.BytesIO(result.image_bytes)) as actual:
            self.assertEqual(actual.tobytes(), source.tobytes())
        self.assertTrue(result.diagnostics['no_new_ai_generation'])
        provider.assert_not_called()

    def test_explicit_border_uses_actual_pixels_and_plain_fallback_is_honest(self):
        source = Image.new('RGB', (100,200), 'red');source.paste('blue',(0,0,20,200))
        payload = io.BytesIO();source.save(payload,'PNG');payload.seek(0)
        definition = get_definition('saree');shot = next(s for s in definition.shots if s.key == 'border')
        result = definition.render_product(data(fabric_image=payload, options={'fabric_border_crop_box':[0,0,20,200]}),shot)
        with Image.open(io.BytesIO(result.image_bytes)) as actual:
            self.assertEqual(actual.getpixel((actual.width//2,actual.height//2)),(0,0,255))
        result = definition.render_product(data(options={}),shot)
        self.assertEqual(result.diagnostics['fabric_region_selection'],'body_only_no_confirmed_border')

    def test_back_identity_declaration_is_rejected_before_provider_call(self):
        definition = get_definition('saree');back = next(s for s in definition.shots if s.key == 'back_pallu')
        for identity in ('request','front'):
            bad = replace(back, identity_from=identity)
            provider = Mock()
            with self.assertRaises(CloudflareGenerationError):
                generate_shot(data(face_choice='poonam'),bad,definition,{}, {},Services(None,provider,None))
            provider.assert_not_called()
            with self.assertRaisesRegex(ValueError,'Identity references are forbidden'):
                validate_definition(replace(definition,shots=tuple(bad if s.key == back.key else s for s in definition.shots)))

    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_back_provider_rejects_every_identity_slot(self, provider):
        definition = get_definition('saree');back = next(s for s in definition.shots if s.key == 'back_pallu')
        config = definition.build_config(data(),back,42)
        for extra in ({'face_choice':'poonam'},{'face_image':io.BytesIO(picture())},
                      {'composition_reference_path':back.reference}):
            with self.assertRaises(CloudflareGenerationError):
                generate_tryon_image(garment_type='saree',fabric_image=io.BytesIO(picture()),
                                     scenario='pose_reference',pose_reference_path=back.reference,
                                     prompt_config=config,**extra)
        provider.assert_not_called()
