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
    extract_band,render_band,BorderSelectionRequired,
)


class SareeBorderExtractionTests(SimpleTestCase):
    def test_explicit_band_cannot_leak_bright_body_or_terminal_artwork(self):
        source=Image.new('RGB',(300,600),'red')
        source.paste('blue',(20,0,60,400))
        source.paste('lime',(0,450,300,600))
        strip,meta=extract_band(source,{'fabric_border_crop_box':[20,0,60,400]})
        pixels=np.asarray(render_band(strip,(532,704)))
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
    def test_ambiguous_border_surfaces_selection_error_in_catalog_stream(self,edit,upload):
        source=Image.fromarray(np.random.default_rng(7).integers(80,190,(200,200,3),dtype=np.uint8))
        buffer=io.BytesIO();source.save(buffer,'PNG')
        response=post(fabric_image=SimpleUploadedFile('ambiguous.png',buffer.getvalue(),'image/png'))
        events=[json.loads(chunk) for chunk in response.streaming_content];response.close()
        failure=next(e for e in events if e['event']=='image_failed' and e['view']=='border')
        self.assertEqual(failure['error'],'border_selection_required')
        self.assertEqual(events[-1]['failed_views'],['border'])
        self.assertEqual(edit.call_count,3)
