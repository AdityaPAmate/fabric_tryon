import io
import json
import threading
from unittest.mock import patch
from unittest.mock import Mock

from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from fabricapp.ai.providers.cloudflare_engine import GenerationResult, CloudflareGenerationError
from fabricapp.catalog import generate_catalog, catalog_plan, edit_config, CATALOG_SLOTS
from fabricapp.ai.references.catalog_reference import get_catalog_reference_path


def picture():
    out = io.BytesIO()
    Image.new('RGB', (64, 96), '#822330').save(out, 'PNG')
    return out.getvalue()


class CatalogTests(SimpleTestCase):
    def data(self):
        return {'garment_type': 'shirt', 'gender': 'men', 'fabric_type': 'velvet',
                'fabric_image': io.BytesIO(picture()), 'options': {'draft_mode': True}}

    def test_plan_for_every_garment(self):
        for garment in ('shirt', 'blazer', 'kurta', 'kurti_pant', 'pant', 'saree'):
            plan = catalog_plan(garment)
            self.assertEqual(len(plan), 6)
            self.assertEqual(len({key for key, _ in plan}), 6)
            self.assertEqual([key for key, _ in plan[:3]], ['front', 'close_up' if garment == 'shirt' else 'three_quarter', 'back'])
        self.assertEqual([key for key, _ in catalog_plan('pant')[3:]], ['waistband', 'pocket', 'hem'])

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/photo.png'})
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 42))
    @patch('fabricapp.catalog.generate_tryon_image', return_value=GenerationResult(picture(), 42))
    def test_single_request_streams_six_images(self, front, edit, upload):
        response = APIClient().post('/api/generate-catalog/', {
            'fabric_image': SimpleUploadedFile('swatch.png', picture(), content_type='image/png'),
            'garment_type': 'shirt', 'gender': 'men', 'fabric_type': 'velvet',
            'body_type': 'trim', 'face_choice': 'raghav',
        }, format='multipart')
        self.assertEqual(response.status_code, 200)
        events = [json.loads(chunk) for chunk in response.streaming_content]
        response.close()
        self.assertEqual([e['image']['view'] for e in events if e['event'] == 'image_ready'],
                         ['front', 'close_up', 'back', 'collar', 'cuff', 'hem'])
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(events[0]['catalog_id'], events[-1]['catalog_id'])
        self.assertTrue(events[0]['catalog_id'])
        self.assertTrue(all(event['image']['generation_seed'] == 42
                            for event in events if event['event'] == 'image_ready'))
        self.assertEqual([call.kwargs['camera_view'] for call in front.call_args_list], ['front', 'close_up'])
        front_args, close_args = [call.kwargs for call in front.call_args_list]
        self.assertEqual(close_args, {**front_args, 'camera_view': 'close_up'})
        self.assertEqual(close_args['body_type'], 'trim')
        self.assertEqual(close_args['face_choice'], 'raghav')
        self.assertEqual(edit.call_count, 4)
        self.assertEqual(upload.call_count, 7)
        self.assertEqual(events[-1]["collage"]["layout"], "portrait-catalog-v2")
        self.assertFalse(front.call_args.kwargs['options']['draft_mode'])
        for view, call in zip(['back', 'collar', 'cuff', 'hem'], edit.call_args_list):
            template = get_catalog_reference_path('shirt', view)
            expected = template.read_bytes() if template else picture()
            self.assertTrue(call.kwargs['person_image'].getvalue() == expected, view)
            self.assertEqual(call.kwargs['scenario'], 'person_pose' if view == 'close_up' else 'person_photo')
            self.assertIn('exact crop' if template else 'SAME person', call.kwargs['prompt_config']['prompt'])
            self.assertIn('velvet', call.kwargs['prompt_config']['prompt'])
        for call in edit.call_args_list[1:]:
            self.assertNotIn('fabric_mask', call.kwargs)
            self.assertNotIn('Image 2', call.kwargs['prompt_config']['prompt'])
            self.assertIn('catalog-template-v5-direct-ai', call.kwargs['prompt_config']['prompt_version'])
        ready = {e['image']['view']: e['image'] for e in events if e['event'] == 'image_ready'}
        self.assertEqual(ready['close_up']['framing'], 'head_to_hip')
        self.assertEqual(ready['collar']['reference_template'], 'shirt_collar.png')
        self.assertEqual(ready['cuff']['reference_template'], 'sleeve.png')
        self.assertEqual(ready['hem']['reference_template'], 'hem.png')
        # Upload the provider photograph unchanged, with no local mask/composite fallback.
        for call in upload.call_args_list[:6]:
            self.assertEqual(call.args[0], picture())

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/photo.png'})
    @patch('fabricapp.catalog.generate_edit')
    @patch('fabricapp.catalog.generate_tryon_image', return_value=GenerationResult(picture(), 42))
    def test_failed_detail_does_not_discard_other_images(self, front, edit, upload):
        edit.side_effect = [CloudflareGenerationError('rejected')] + [GenerationResult(picture(), 42)] * 3
        events = list(generate_catalog(self.data(), threading.Event()))
        self.assertEqual(events[-1]['status'], 'partial')
        self.assertEqual(events[-1]['failed_views'], ['back'])
        self.assertEqual(len(events[-1]['images']), 5)

    @patch('fabricapp.catalog.generate_edit')
    @patch('fabricapp.catalog.generate_tryon_image', side_effect=CloudflareGenerationError('quota', status_code=429))
    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/photo.png'})
    def test_quota_stops_further_provider_calls(self, upload, front, edit):
        events = list(generate_catalog(self.data(), threading.Event()))
        self.assertEqual(events[-1]['status'], 'failed')
        self.assertEqual(len(events[-1]['failed_views']), 6)
        front.assert_called_once()
        edit.assert_not_called()
        upload.assert_not_called()

    @patch('fabricapp.catalog.generate_tryon_image')
    def test_cancel_before_start(self, front):
        stop = threading.Event()
        stop.set()
        list(generate_catalog(self.data(), stop))
        front.assert_not_called()

    @patch('fabricapp.catalog.generate_tryon_image')
    def test_validation_before_generation(self, front):
        for extras in ({'camera_view': 'front'}, {'pose': 'invalid'}, {'fabric_type': 'wool'}):
            response = APIClient().post('/api/generate-catalog/', {
                'fabric_image': SimpleUploadedFile('fabric.png', picture(), content_type='image/png'),
                'garment_type': 'shirt', 'gender': 'men', **extras,
            }, format='multipart')
            self.assertEqual(response.status_code, 400)
        front.assert_not_called()

    def test_busy_response(self):
        self.assertTrue(CATALOG_SLOTS.acquire(blocking=False))
        try:
            response = APIClient().post('/api/generate-catalog/', {
                'fabric_image': SimpleUploadedFile('fabric.png', picture(), content_type='image/png'),
                'garment_type': 'shirt', 'gender': 'men',
            }, format='multipart')
            self.assertEqual(response.status_code, 429)
        finally:
            CATALOG_SLOTS.release()

    def test_page_and_targeted_detail_prompt(self):
        response = APIClient().get('/api/catalog/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Generate Catalog')
        config = edit_config(self.data(), catalog_plan('shirt')[3][1], 43)
        self.assertIn('extreme close-up', config['prompt'])
        self.assertNotIn('shown fully from head to feet', config['prompt'])
        self.assertEqual(config['seed'], 43)

    def test_back_is_close_up_and_angle_is_front_dominant(self):
        for garment in ('shirt', 'blazer', 'kurta', 'kurti_pant', 'pant', 'saree'):
            plan = dict(catalog_plan(garment))
            self.assertIn('REAR CLOSE-UP', plan['back'])
            self.assertNotIn('back full-body', plan['back'])
            if garment == 'shirt':
                self.assertIn('close_up', plan)
            else:
                self.assertIn('45 degrees', plan['three_quarter'])
        data = self.data()
        data['background'] = 'white_marble_terrace'
        prompt = edit_config(data, dict(catalog_plan('shirt'))['back'], 42, view='back')['prompt']
        self.assertIn('marble terrace', prompt)
        self.assertIn('FINAL CAMERA REQUIREMENT: REAR CLOSE-UP', prompt)

    def test_templates_are_packaged_and_keep_reference_geometry(self):
        for view in ('collar', 'cuff', 'hem'):
            path = get_catalog_reference_path('shirt', view)
            self.assertTrue(path.is_file())
            data = self.data()
            config = edit_config(data, dict(catalog_plan('shirt'))[view], 42,
                                 reference_template=path, view=view)
            self.assertIn('Replace ALL visible shirt fabric', config['prompt'])
            self.assertIn('FINAL CROP: match image 0 exactly', config['prompt'])
            self.assertNotIn('both shoulders', config['prompt'])
            self.assertIn('only the visible cloth', config['prompt'])
            self.assertNotIn('SAME person', config['prompt'])
        self.assertIsNone(get_catalog_reference_path('saree', 'collar'))

    def test_assets_resolve_after_package_move(self):
        from fabricapp.ai.references.faces import get_face_image_path
        from fabricapp.ai.references.pose_reference import get_pose_reference_path
        from pathlib import Path
        self.assertTrue(get_face_image_path('raghav').is_file())
        self.assertTrue(Path(get_pose_reference_path('saree', 'pallu_on_head')).is_file())

    def test_template_requests_align_dimensions_without_relaxing_output_validation(self):
        from fabricapp.ai.providers.cloudflare_engine import generate_tryon_image as engine
        template = get_catalog_reference_path('shirt', 'collar')
        config = edit_config(self.data(), dict(catalog_plan('shirt'))['collar'], 42,
                             reference_template=template, view='collar')
        def provider(*args, **kwargs):
            self.assertEqual(set(kwargs['files']), {'input_image_0', 'input_image_1'})
            name, source, mime = kwargs['files']['input_image_1']
            self.assertEqual((name, mime), ('garment_source.png', 'image/png'))
            self.assertTrue(source.getvalue().startswith(b'\x89PNG\r\n\x1a\n'))
            self.assertEqual((kwargs['data']['width'], kwargs['data']['height']), (1536, 1248))
            result = io.BytesIO()
            Image.new('RGB', (1536, 1248)).save(result, 'PNG')
            return Mock(status_code=200, headers={'Content-Type': 'image/png'}, content=result.getvalue())
        with patch('fabricapp.ai.providers.cloudflare_engine.requests.post', side_effect=provider):
            result = engine(person_image=io.BytesIO(template.read_bytes()), fabric_image=io.BytesIO(picture()),
                            garment_type='shirt', scenario='person_photo', options={'draft_mode': False},
                            prompt_config=config)
        self.assertEqual(result.effective_seed, 42)
        self.assertEqual(result.diagnostics['height'], 1248)

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/photo.png'})
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 42))
    @patch('fabricapp.catalog.generate_tryon_image', side_effect=CloudflareGenerationError('rejected'))
    def test_detail_templates_work_even_if_front_generation_is_rejected(self, front, edit, upload):
        events = list(generate_catalog(self.data(), threading.Event()))
        ready = [event['image']['view'] for event in events if event['event'] == 'image_ready']
        self.assertEqual(ready, ['collar', 'cuff', 'hem'])
        self.assertEqual(events[-1]['status'], 'partial')
        self.assertEqual(edit.call_count, 3)


class CollageTests(SimpleTestCase):
    def test_fixed_portrait_order_and_original_swatch(self):
        from fabricapp.ai.images.catalog_collage import compose_catalog
        views = ['front', 'three_quarter', 'back', 'collar', 'cuff', 'hem']
        colors = ['red', 'green', 'blue', 'yellow', 'cyan', 'magenta']
        shots = {}
        for view, color in zip(views, colors):
            out = io.BytesIO()
            Image.new('RGB', (100, 100), color).save(out, 'PNG')
            shots[view] = out.getvalue()
        result = Image.open(io.BytesIO(compose_catalog(shots, picture(), views)))
        self.assertEqual(result.size, (1800, 3200))
        points = [(380, 1200), (1000, 400), (1500, 400), (1200, 1200), (1200, 1800), (1200, 2300)]
        for point, color in zip(points, colors):
            self.assertEqual(result.getpixel(point), Image.new('RGB', (1, 1), color).getpixel((0, 0)))
        self.assertEqual(result.getpixel((900, 2800)), (130, 35, 48))
        with self.assertRaises(ValueError):
            compose_catalog({}, picture(), views)

    @patch('fabricapp.catalog.upload_generated_image')
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 42))
    @patch('fabricapp.catalog.generate_tryon_image', return_value=GenerationResult(picture(), 42))
    def test_collage_upload_failure_is_partial(self, front, edit, upload):
        upload.side_effect = [{'url': 'https://example.com/photo.png'}] * 6 + [RuntimeError('upload failed')]
        events = list(generate_catalog(CatalogTests().data(), threading.Event()))
        self.assertEqual(events[-1]['status'], 'partial')
        self.assertIsNone(events[-1]['collage'])
        self.assertEqual(events[-1]['collage_error'], 'collage_composition_or_upload_failed')
        self.assertEqual(len(events[-1]['images']), 6)


    def test_sleeve_panel_preserves_all_four_edges(self):
        from fabricapp.ai.images.catalog_collage import compose_catalog
        views = ['front', 'three_quarter', 'back', 'collar', 'cuff', 'hem']
        source = Image.new('RGB', (300, 200), 'blue')
        from PIL import ImageDraw
        ImageDraw.Draw(source).rectangle((0, 0, 299, 199), outline='red', width=8)
        buffer = io.BytesIO(); source.save(buffer, 'PNG')
        shots = {view: picture() for view in views}; shots['cuff'] = buffer.getvalue()
        image = Image.open(io.BytesIO(compose_catalog(shots, picture(), views)))
        # 300:200 source fits to 702x468, centered in a 1028x468 slot.
        for point in [(939, 1800), (1633, 1800), (1200, 1588), (1200, 2048)]:
            self.assertGreater(image.getpixel(point)[0], 200)
            self.assertLess(image.getpixel(point)[2], 50)


class BrownColourTests(SimpleTestCase):
    def test_dark_brown_priority_is_not_applied_to_white_or_blue(self):
        from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours, colour_reference_prompt
        for color, expected in [('#3e281b', True), ('#ffffff', False), ('#204080', False)]:
            buffer = io.BytesIO()
            Image.new('RGB', (64, 64), color).save(buffer, 'PNG'); buffer.seek(0)
            prompt = colour_reference_prompt(measure_fabric_colours(buffer), 'shirt')
            self.assertEqual('COLOUR PRIORITY' in prompt, expected)
            self.assertEqual('dark chocolate brown' in prompt, expected)
