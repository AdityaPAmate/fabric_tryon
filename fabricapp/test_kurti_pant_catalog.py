import io
import json
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image

from fabricapp.catalog_engine.registry import get_definition
from fabricapp.test_catalog_engine import picture, post


class KurtiPantCatalogTests(SimpleTestCase):
    @override_settings(SAVE_DEBUG_FILES=False)
    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.test/image.png'})
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_default_catalog_streams_six_reference_edits_and_a_3x4_export(self, provider, upload):
        def answer(url, **request):
            fields = request['data']
            return Mock(status_code=200, headers={'Content-Type': 'image/png'},
                        content=picture(size=(fields['width'], fields['height'])))

        provider.side_effect = answer
        response = post(garment_type='kurti_pant',
                        face_image=SimpleUploadedFile('face.png', picture('orange'), content_type='image/png'),
                        garment_details=['full_sleeves', 'with_dupatta'], options='{"draft_mode": true}')
        self.assertEqual(response.status_code, 200)
        try:
            events = [json.loads(chunk) for chunk in response.streaming_content]
        finally:
            response.close()

        expected = {
            'front': 'kurti_front_1.png', 'side': 'kurti_side_2.png', 'back': 'kurti_back_3.png',
            'neckline': 'kurti_closeup_4.png', 'sleeve': 'kurti_sleves_5.png', 'pant': 'kurti_pant_6.png',
        }
        self.assertEqual(events[0]['views'], list(expected))
        ready = [event['image'] for event in events if event['event'] == 'image_ready']
        self.assertEqual({image['view']: image['reference_template'] for image in ready}, expected)
        self.assertEqual(len({image['generation']['input_hashes']['input_image_0'] for image in ready}), 6)
        self.assertEqual(len({image['generation']['input_hashes']['input_image_1'] for image in ready}), 1)
        for image in ready:
            self.assertEqual('input_image_2' in image['generation']['input_hashes'], image['view'] in ('front', 'side'))
        self.assertIn('full-length sleeves', provider.call_args_list[0].kwargs['data']['prompt'])
        self.assertIn('Add a dupatta', provider.call_args_list[2].kwargs['data']['prompt'])
        self.assertIn('Keep the pants solid white', provider.call_args_list[-1].kwargs['data']['prompt'])
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(events[-1]['collage']['aspect_ratio'], '3:4')
        self.assertFalse(events[-1]['collage']['includes_original_swatch'])
        self.assertEqual(provider.call_count, 6)
        self.assertEqual(upload.call_count, 7)
        with Image.open(io.BytesIO(upload.call_args.args[0])) as collage:
            self.assertEqual(collage.size, (1800, 2400))

    def test_classic_edition_still_resolves_to_the_legacy_catalog(self):
        classic = get_definition('kurti_pant', 'classic-v1')
        self.assertEqual(classic.layout({}).size, (1800, 3200))
        self.assertEqual(classic.shots[0].operation, 'pipeline')
