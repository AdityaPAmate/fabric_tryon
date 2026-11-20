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
    def test_real_border_runs_from_first_to_third_corner(self):
        source=Image.new('RGB',(100,400),'red');source.paste('blue',(30,0,50,400))
        payload=io.BytesIO();source.save(payload,'PNG');payload.seek(0)
        definition=get_definition('saree');shot=next(s for s in definition.shots if s.key=='border')
        result=definition.render_product(data(fabric_image=payload,
            options={'fabric_border_crop_box':[30,0,50,400]}),shot)
        with Image.open(io.BytesIO(result.image_bytes)) as image:
            for fraction in (.1,.5,.9):
                self.assertEqual(image.getpixel((round(fraction*(image.width-1)),
                                                 round(fraction*(image.height-1)))),(0,0,255))
            self.assertNotEqual(image.getpixel((image.width-1,0)),(0,0,255))
        self.assertEqual(result.diagnostics['photo_fit'],'side_band_diagonal_1_to_3')
        self.assertTrue(result.diagnostics['no_new_ai_generation'])

    def test_pleats_edit_task_leads_for_plain_and_patterned_fabrics(self):
        definition=get_definition('saree');shot=next(s for s in definition.shots if s.key=='pleats')
        for material in ('unspecified','cotton','silk','velvet'):
            for patterned in (False,True):
                source=Image.new('RGB',(180,240),'teal')
                if patterned:
                    source.paste('gold',(50,0,70,240));source.paste('white',(140,0,160,240))
                payload=io.BytesIO();source.save(payload,'PNG');payload.seek(0)
                config=definition.build_config(data(fabric_image=payload,fabric_type=material,options={}),shot,42)
                self.assertTrue(config['prompt'].startswith('EDIT IMAGE 0 IN PLACE:'))
                self.assertIn('FOLDED TEXTILE',config['prompt'])
                self.assertNotIn('saree body and pallu',config['prompt'])
                self.assertNotIn('Keep the garment construction',config['prompt'])
                self.assertIn('exact pleat count',config['prompt'])
                self.assertTrue(config['fabric_colour_reference']['colours'])

    def test_narrow_border_input_keeps_design_and_gains_real_source_context(self):
        from fabricapp.ai.garments.saree.catalog.product_details import border_reference_box
        from fabricapp.ai.garments.saree.catalog.regions import source_regions
        source = Image.new('RGB',(1000,1000),'ivory');source.paste('blue',(281,0,312,740))
        payload=io.BytesIO();source.save(payload,'PNG');payload.seek(0)
        request=data(fabric_image=payload,options={'fabric_border_crop_box':[281,0,312,740]})
        box=border_reference_box(request,source_regions(request))
        self.assertGreaterEqual(box[2]-box[0],185)
        self.assertLessEqual(box[0],281);self.assertGreaterEqual(box[2],312)
        self.assertEqual(source.crop(box).getpixel((281-box[0],100)),(0,0,255))
        definition=get_definition('saree');shot=next(s for s in definition.shots if s.key=='pleats')
        config=definition.build_config(request,shot,42)
        self.assertEqual(config['fabric_reference_crops']['side_border'],box)

    def test_full_side_preserves_terminal_product_evidence_and_uses_full_body_reference(self):
        definition=get_definition('saree');shot=next(s for s in definition.shots if s.key=='side_portrait')
        config=definition.build_config(data(options={'fabric_body_crop_box':[0,0,40,80]}),shot,42)
        self.assertIsNone(config['fabric_crop_box'])
        self.assertEqual(config['fabric_region'],'full_saree')
        self.assertEqual(shot.framing,'side_full_body')
        self.assertIn('FULL-LENGTH head-to-floor',config['prompt'])
        self.assertNotIn('head-to-upper-thigh',config['prompt'])
        self.assertNotIn('pallu end stays below the frame',config['prompt'])

    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_report_sized_narrow_border_is_not_sent_as_a_31_pixel_input(self, provider):
        from fabricapp.ai.providers.cloudflare_engine import generate_tryon_image
        source=Image.new('RGB',(1000,1000),'ivory');source.paste('blue',(281,0,312,740))
        payload=io.BytesIO();source.save(payload,'PNG');payload.seek(0)
        request=data(fabric_image=payload,options={'fabric_border_crop_box':[281,0,312,740]})
        definition=get_definition('saree');shot=next(s for s in definition.shots if s.key=='pleats')
        config=definition.build_config(request,shot,42)
        def reply(url,**kwargs):
            with Image.open(kwargs['files']['input_image_2'][1]) as extra:
                self.assertGreaterEqual(min(extra.size),128)
                self.assertLessEqual(max(extra.size),1024)
            fields=kwargs['data']
            return Mock(status_code=200,headers={'Content-Type':'image/png'},
                        content=picture(size=(fields['width'],fields['height'])))
        provider.side_effect=reply
        with patch('django.conf.settings.SAVE_DEBUG_FILES',False):
            result=generate_tryon_image(garment_type='saree',fabric_image=payload,
                person_image=io.BytesIO(shot.reference.read_bytes()),scenario='person_photo',
                options=request['options'],prompt_config=config)
        self.assertEqual(result.diagnostics['input_dimensions']['input_image_2'],[128,511])

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
