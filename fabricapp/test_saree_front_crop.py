"""Pleats must be the generated front's real pixels, with no new AI request."""
import hashlib
import io
from unittest.mock import Mock

from django.test import SimpleTestCase
from PIL import Image, ImageOps

from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.runner import generate_shot, Services
from fabricapp.ai.garments.saree.catalog.detail_prompts import build_detail_config
from fabricapp.test_catalog_engine import data, picture


class SareeFrontCropTests(SimpleTestCase):
    def test_pleats_uses_front_pixels_and_seed_for_different_fabrics(self):
        definition=get_definition('saree');shot=definition.shots[-1]
        self.assertEqual(shot.operation,'crop')
        self.assertEqual(shot.dependencies,('front',))
        for colour in ('teal','ivory','purple'):
            front=Image.new('RGB',(576,1920),colour)
            front.paste('magenta',(0,0,576,900))  # upper body must stay out
            front.paste('gold',(40,1740,540,1790))  # original lower hem
            buffer=io.BytesIO();front.save(buffer,'PNG');source=buffer.getvalue()
            provider=Mock(side_effect=AssertionError('No AI call permitted'))
            result=generate_shot(data(),shot,definition,{'front':source},{'front':314},
                                 Services(provider,provider,provider))
            provider.assert_not_called()
            self.assertEqual(result.effective_seed,314)
            self.assertEqual(result.diagnostics['source_image_sha256'],hashlib.sha256(source).hexdigest())
            self.assertTrue(result.diagnostics['no_new_ai_generation'])
            box=result.diagnostics['source_crop']
            self.assertGreaterEqual(box[1],.50)
            self.assertEqual(box[3],.94)
            bounds=tuple(round(value*dimension) for value,dimension in zip(box,(576,1920,576,1920)))
            expected=ImageOps.fit(front.crop(bounds),(532,852),method=Image.Resampling.LANCZOS)
            with Image.open(io.BytesIO(result.image_bytes)) as actual:
                self.assertEqual(actual.tobytes(),expected.tobytes())
                self.assertNotEqual(actual.getpixel((0,0)),(255,0,255))
            self.assertNotIn('prompt',definition.build_config(data(),shot,42))

    def test_independent_pleats_generation_is_explicitly_rejected(self):
        shot=get_definition('saree').shots[-1]
        with self.assertRaisesRegex(ValueError,'cropped from the generated front'):
            build_detail_config(data(),shot,42)

    def test_crop_aspect_and_bounds_follow_front_resolution(self):
        definition=get_definition('saree');shot=definition.shots[-1]
        for size in ((576,1920),(288,960),(768,2048)):
            source=picture(size=size)
            box=definition.resolve_crop(data(),shot,source)
            self.assertTrue(0<=box[0]<box[2]<=1 and 0<=box[1]<box[3]<=1)
            aspect=(box[2]-box[0])*size[0]/((box[3]-box[1])*size[1])
            self.assertAlmostEqual(aspect,532/852)
