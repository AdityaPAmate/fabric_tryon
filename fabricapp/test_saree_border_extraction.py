"""A border detail may only sample the selected side band, never the full cloth."""
import io
import json
from unittest.mock import patch
import numpy as np
from PIL import Image, ImageDraw
from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.test_catalog_engine import post,picture

from fabricapp.ai.garments.saree.catalog.border_extraction import (
    extract_band,render_band,render_from_source,_rectify,_auto_quad,BorderSelectionRequired,
)


class SareeBorderExtractionTests(SimpleTestCase):
    def test_right_band_direction_is_normalized_with_override(self):
        source=Image.new('RGB',(200,400),'white')
        source.paste('red',(150,0,190,200));source.paste('blue',(150,200,190,400))
        for rotation,expected in [('auto',(0,0,255)),(0,(255,0,0)),(180,(0,0,255))]:
            strip,meta=extract_band(source,{'fabric_border_crop_box':[150,0,190,400],
                                           'fabric_border_rotation':rotation})
            rendered=render_from_source(source,strip,meta,(532,704))
            self.assertEqual(rendered.getpixel((133,176)),expected)

    def test_edge_touching_gold_band_is_not_confused_with_pink_body(self):
        source=Image.new('RGB',(300,600),(190,0,80));source.paste('gold',(0,0,24,600))
        strip,meta=extract_band(source,{})
        self.assertEqual(meta['selection'],'detected_edge_touching_band')
        self.assertEqual(meta['side'],'left')
        self.assertGreater(np.asarray(strip)[:,:,1].mean(),150)

    def test_single_pass_render_samples_original_not_intermediate_strip(self):
        source=Image.new('RGB',(100,400),'red');source.paste('blue',(20,0,60,400))
        corrupted_strip=Image.new('RGB',(40,400),'lime')
        meta={'source_crop_box':[20,0,60,400],'orientation_rotation':0}
        result=render_from_source(source,corrupted_strip,meta,(532,704))
        self.assertEqual(result.getpixel((266,352)),(0,0,255))
        self.assertEqual(meta['source_sampling_passes'],1)

    def test_rectification_does_not_invent_eighty_pixels_of_source_detail(self):
        source=Image.new('RGB',(100,200),'blue')
        strip=_rectify(source,[(10,10),(10,110),(22,110),(22,10)])
        self.assertEqual(strip.size,(12,100))

    def test_rotation_option_is_validated_and_saree_only(self):
        from fabricapp.catalog import CatalogRequestSerializer
        from rest_framework.exceptions import ValidationError
        for value in (True,90,'180',None):
            with self.assertRaises(ValidationError):
                CatalogRequestSerializer().validate_options({'fabric_border_rotation':value})
        for value in ('auto',0,180):
            self.assertEqual(CatalogRequestSerializer().validate_options({'fabric_border_rotation':value})['fabric_border_rotation'],value)
        response=post(garment_type='shirt',gender='men',options=json.dumps({'fabric_border_rotation':180}))
        self.assertEqual(response.status_code,400)

    def test_collapsing_edge_pair_is_rejected_before_stretching(self):
        source=Image.new('RGB',(200,400),'white')
        def candidates(sample,right=False):
            return ([],146,7) if right else ([(30,20,0),(25,45,-.2)],146,7)
        with patch('fabricapp.ai.garments.saree.catalog.border_extraction._candidates',side_effect=candidates):
            self.assertEqual(_auto_quad(source),(None,None))

    @patch('fabricapp.catalog.upload_generated_image',return_value={'url':'https://example.test/a.png'})
    @patch('fabricapp.catalog.generate_edit',return_value=GenerationResult(picture(),42))
    def test_rotation_override_reaches_the_public_catalog_result(self,edit,upload):
        for rotation in (0,180):
            response=post(options=json.dumps({'fabric_border_rotation':rotation,
                                              'fabric_border_crop_box':[0,0,40,100]}))
            events=[json.loads(chunk) for chunk in response.streaming_content];response.close()
            self.assertEqual(events[-1]['status'],'completed')
            border=next(e['image'] for e in events if e['event']=='image_ready' and e['image']['view']=='border')
            self.assertEqual(border['operation'],'crop')
            self.assertTrue(border['generation']['no_new_ai_generation'])
            self.assertEqual(border['generation']['source_view'],'front')

    def test_explicit_band_cannot_leak_bright_body_or_terminal_artwork(self):
        source=Image.new('RGB',(300,600),'red')
        source.paste('blue',(20,0,60,400))
        source.paste('lime',(0,450,300,600))
        strip,meta=extract_band(source,{'fabric_border_crop_box':[20,0,60,400]})
        pixels=np.asarray(render_from_source(source,strip,meta,(532,704)))
        self.assertFalse(np.any(np.all(pixels==(255,0,0),axis=2)))
        self.assertFalse(np.any(np.all(pixels==(0,255,0),axis=2)))
        self.assertTrue(np.any(np.all(pixels==(0,0,255),axis=2)))
        self.assertEqual(meta['selection'],'explicit_crop')

    def test_slanted_long_edge_is_rectified_without_sampling_terminal_panel(self):
        source=Image.new('RGB',(400,800),'white');draw=ImageDraw.Draw(source)
        draw.polygon([(70,0),(10,800),(65,800),(125,0)],fill='navy')
        draw.rectangle((150,0,399,799),fill='salmon')
        draw.rectangle((0,600,399,799),fill='lime')
        strip,meta=extract_band(source,{})
        self.assertEqual(meta['selection'],'detected_long_edge_pair')
        self.assertTrue(all(y<600 for x,y in meta['source_quad']))
        self.assertFalse(np.any(np.all(np.asarray(strip)==(0,255,0),axis=2)))

    def test_missing_border_never_falls_back_to_whole_patterned_fabric(self):
        rng=np.random.default_rng(7)
        source=Image.fromarray(rng.integers(80,190,(200,200,3),dtype=np.uint8))
        with self.assertRaises(BorderSelectionRequired):
            extract_band(source,{})

    def test_manual_band_bounds_are_checked_before_rendering(self):
        source=Image.new('RGB',(100,200),'red')
        for box in ([0,0,101,200],[True,0,50,100],[0,0,0,200]):
            with self.assertRaises(BorderSelectionRequired):
                extract_band(source,{'fabric_border_crop_box':box})

    def test_landscape_manual_band_is_supported(self):
        source=Image.new('RGB',(600,100),'gold')
        strip,meta=extract_band(source,{'fabric_border_crop_box':[0,20,600,40]})
        self.assertEqual(strip.size,(20,600))

    @patch('fabricapp.catalog.upload_generated_image',return_value={'url':'https://example.test/a.png'})
    @patch('fabricapp.catalog.generate_edit',return_value=GenerationResult(picture(),42))
    def test_hand_drape_does_not_require_automatic_border_detection(self,edit,upload):
        source=Image.fromarray(np.random.default_rng(7).integers(80,190,(200,200,3),dtype=np.uint8))
        buffer=io.BytesIO();source.save(buffer,'PNG')
        response=post(fabric_image=SimpleUploadedFile('ambiguous.png',buffer.getvalue(),'image/png'))
        events=[json.loads(chunk) for chunk in response.streaming_content];response.close()
        self.assertEqual(events[-1]['failed_views'],[])
        self.assertEqual(events[-1]['status'],'completed')
        self.assertEqual(edit.call_count,3)
