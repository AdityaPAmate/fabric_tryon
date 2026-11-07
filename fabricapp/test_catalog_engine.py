"""Catalog contracts, seven-view streaming, dependency isolation and provider inputs."""
import io
import json
import threading
from dataclasses import replace
from unittest.mock import patch, Mock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from email.parser import BytesParser
from email.policy import default

from django.test import SimpleTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from PIL import Image

from fabricapp.ai.providers.cloudflare_engine import GenerationResult, CloudflareGenerationError
from fabricapp.catalog import generate_catalog
from fabricapp.catalog_engine.registry import get_definition, DEFAULTS
from fabricapp.catalog_engine.validation import validate_definition
from fabricapp.catalog_engine.renderer import render_catalog
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot, Panel, Layout


def picture(color='purple', size=(96, 128)):
    buffer = io.BytesIO()
    Image.new('RGB', size, color).save(buffer, 'PNG')
    return buffer.getvalue()


def data(**extra):
    return {'fabric_image': io.BytesIO(picture()), 'garment_type': 'saree', 'gender': 'women',
            'fabric_type': 'cotton', 'options': {'draft_mode': True}, **extra}


def post(**extra):
    return APIClient().post('/api/generate-catalog/', {
        'fabric_image': SimpleUploadedFile('fabric.png', picture(), content_type='image/png'),
        'garment_type': 'saree', 'gender': 'women', **extra,
    }, format='multipart')


class CatalogDefinitionTests(SimpleTestCase):
    def test_all_registered_defaults_and_legacy_editions_validate(self):
        for garment in DEFAULTS:
            definition = get_definition(garment)
            validate_definition(definition)
            self.assertEqual(len(definition.shots), 7 if garment == 'saree' else 6)
        self.assertEqual(len(get_definition('saree', 'classic-v1').shots), 6)

    def test_invalid_and_cyclic_dependencies_and_missing_assets_fail_preflight(self):
        definition = get_definition('saree')
        first = definition.shots[0]
        for shot in (replace(first, dependencies=('back_pallu',)),
                     replace(first, reference=first.reference / 'missing.png'),
                     replace(first, identity_from='unknown')):
            with self.assertRaises(ValueError):
                validate_definition(replace(definition, shots=(shot, *definition.shots[1:])))

    def test_duplicate_shots_missing_panels_and_overlap_fail(self):
        definition = get_definition('saree')
        layout = definition.layout({})
        with self.assertRaises(ValueError):
            validate_definition(replace(definition, shots=(definition.shots[0], *definition.shots)))
        for panels in (layout.panels[:-1],
                       (replace(layout.panels[0], box=layout.panels[1].box), *layout.panels[1:])):
            with self.assertRaises(ValueError):
                validate_definition(replace(definition, layout=lambda product: replace(layout, panels=panels)))

    def test_an_eighth_panel_requires_no_runner_or_renderer_branch(self):
        shots = tuple(Shot(str(i), 'detail', 'pipeline', 'detail', camera_view='front') for i in range(8))
        layout = Layout('extension-test', (800, 100), tuple(Panel(str(i), (i*100, 0, (i+1)*100, 100)) for i in range(8)))
        definition = CatalogDefinition('future', 'v1', shots, lambda *args: {}, lambda product: layout)
        validate_definition(definition)
        output = render_catalog({shot.key: picture() for shot in shots}, b'', layout)
        self.assertEqual(Image.open(io.BytesIO(output)).size, (800, 100))

    def test_back_reference_is_separate_byte_identical_copy(self):
        from pathlib import Path
        path = get_definition('saree').shots[2].reference
        original = Path(__file__).parent / 'ai/references/assets/poses/saree/back_showing_pallu.jpg'
        self.assertNotEqual(path, original)
        self.assertEqual(path.read_bytes(), original.read_bytes())

    def test_saree_prompts_do_not_leak_shirt_instructions_and_draft_is_small(self):
        definition = get_definition('saree')
        for shot in definition.shots:
            config = definition.build_config(data(face_choice='aadhya'), shot, 71)
            self.assertEqual(config['seed'], 71)
            self.assertLessEqual(max(config['output_dimensions']), 512)
            self.assertTrue(all(value % 32 == 0 for value in config['output_dimensions']))
            self.assertIn('Image 1 is the product fabric swatch', config['prompt'])
            self.assertNotIn('shirt', config['prompt'].lower())
            self.assertIn('cotton', config['prompt'])


class SareeCatalogTests(SimpleTestCase):
    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/image.png'})
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 71))
    @patch('fabricapp.catalog.generate_tryon_image')
    def test_seven_shots_stream_with_correct_identity_and_reference_roles(self, pipeline, edit, upload):
        response = post(catalog_product=json.dumps({'product_name': 'Test Saree', 'product_code': 'S-7'}))
        self.assertEqual(response.status_code, 200)
        events = [json.loads(chunk) for chunk in response.streaming_content]
        response.close()
        self.assertEqual(events[0]['total'], 7)
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(events[-1]['collage']['layout'], 'saree-editorial-v1')
        self.assertFalse(events[-1]['collage']['includes_original_swatch'])
        self.assertEqual(edit.call_count, 7)
        self.assertEqual(upload.call_count, 8)
        pipeline.assert_not_called()
        definition = get_definition('saree')
        self.assertEqual([event['image']['view'] for event in events if event['event'] == 'image_ready'],
                         [shot.key for shot in definition.shots])
        for shot, call in zip(definition.shots, edit.call_args_list):
            self.assertEqual(call.kwargs['person_image'].getvalue(), shot.reference.read_bytes())
            if shot.identity_from == 'front':
                self.assertEqual(call.kwargs['face_image'].getvalue(), picture())
                self.assertEqual(call.kwargs['pose_reference_path'], shot.reference)
            elif not shot.identity_from:
                self.assertNotIn('face_image', call.kwargs)
        self.assertEqual(Image.open(io.BytesIO(upload.call_args.args[0])).size, (2200, 2900))

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/image.png'})
    @patch('fabricapp.catalog.generate_edit')
    def test_front_failure_skips_identity_dependents_but_keeps_fabric_templates(self, edit, upload):
        edit.side_effect = [CloudflareGenerationError('rejected')] + [GenerationResult(picture(), 42)] * 3
        events = list(generate_catalog(data(), threading.Event()))
        self.assertEqual(events[-1]['failed_views'], ['front', 'side_portrait', 'back_pallu', 'neckline'])
        self.assertEqual([image['view'] for image in events[-1]['images']], ['pallu', 'border', 'pleats'])
        self.assertEqual(events[-1]['status'], 'partial')
        self.assertEqual(edit.call_count, 4)

    @patch('fabricapp.catalog.upload_generated_image')
    @patch('fabricapp.catalog.generate_edit', return_value=GenerationResult(picture(), 42))
    def test_front_upload_failure_keeps_anchor_for_dependents(self, edit, upload):
        upload.side_effect = [RuntimeError('upload failed')] + [{'url': 'https://example.com/a.png'}] * 6
        events = list(generate_catalog(data(), threading.Event()))
        self.assertEqual(edit.call_count, 7)
        self.assertEqual(events[-1]['failed_views'], ['front'])
        self.assertEqual(len(events[-1]['images']), 6)

    @patch('fabricapp.catalog.generate_edit', side_effect=CloudflareGenerationError('quota', status_code=429))
    def test_quota_and_cancel_stop_remaining_calls(self, edit):
        events = list(generate_catalog(data(), threading.Event()))
        self.assertEqual(events[-1]['status'], 'failed')
        self.assertEqual(len(events[-1]['failed_views']), 7)
        edit.assert_called_once()
        edit.reset_mock()
        stopped = threading.Event()
        stopped.set()
        list(generate_catalog(data(), stopped))
        edit.assert_not_called()

    @patch('fabricapp.catalog.generate_edit')
    def test_invalid_edition_metadata_and_gender_rejected_before_generation(self, edit):
        for extra in ({'catalog_edition': '../../bad'}, {'gender': 'men'},
                      {'catalog_product': '[]'}, {'catalog_product': '{"unknown":"value"}'},
                      {'catalog_product': '{"product_name":"' + 'x'*101 + '"}'},
                      {'options': '{"_catalog_config": {}}'}):
            self.assertEqual(post(**extra).status_code, 400, extra)
        edit.assert_not_called()

    @patch('fabricapp.catalog.generate_edit')
    @patch('fabricapp.catalog_engine.validation.validate_definition', side_effect=ValueError('missing reference'))
    def test_missing_configuration_returns_503_before_streaming(self, validation, edit):
        self.assertEqual(post().status_code, 503)
        edit.assert_not_called()

    @patch('fabricapp.catalog.upload_generated_image', return_value={'url': 'https://example.com/image.png'})
    @patch('fabricapp.ai.providers.cloudflare_engine.requests.post')
    def test_actual_engine_prepares_seven_multipart_requests_with_identity_slots(self, provider, upload):
        seen = []
        def answer(url, **kwargs):
            fields = kwargs['data']
            slots = set(kwargs['files'])
            seen.append(slots)
            payload = picture(size=(fields['width'], fields['height']))
            self.assertIn('saree', fields['prompt'])
            return Mock(status_code=200, headers={'Content-Type': 'image/png'}, content=payload)
        provider.side_effect = answer
        with patch('django.conf.settings.SAVE_DEBUG_FILES', False):
            response = post(face_image=SimpleUploadedFile('face.png', picture('orange'), content_type='image/png'),
                            options='{"draft_mode": true}')
            events = [json.loads(chunk) for chunk in response.streaming_content]
            response.close()
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(len(seen), 7)
        self.assertTrue(all(slots == {'input_image_0', 'input_image_1', 'input_image_2'} for slots in seen[:4]))
        self.assertTrue(all(slots == {'input_image_0', 'input_image_1'} for slots in seen[4:]))


class SareeRendererTests(SimpleTestCase):
    def test_metadata_changes_do_not_generate_or_change_photo_pixels(self):
        definition = get_definition('saree')
        shots = {shot.key: picture() for shot in definition.shots}
        layout = definition.layout({})
        first = Image.open(io.BytesIO(render_catalog(shots, b'', layout)))
        second = Image.open(io.BytesIO(render_catalog(shots, b'', definition.layout({'product_name': 'New Product'}))))
        for panel in layout.panels:
            self.assertEqual(first.crop(panel.box).tobytes(), second.crop(panel.box).tobytes())
        self.assertNotEqual(first.tobytes(), second.tobytes())
        for text in layout.texts:
            self.assertNotIn('5.5', text.value)
            self.assertNotIn('Cotton Blend', text.value)
        with self.assertRaises(ValueError):
            render_catalog({}, b'', layout)


class CatalogHttpBoundaryTests(SimpleTestCase):
    @override_settings(CLOUDFLARE_ACCOUNT_ID='local-test', CLOUDFLARE_API_TOKEN='local-test',
                       CLOUDFLARE_MODEL='local-model', SAVE_DEBUG_FILES=False)
    def test_stream_through_real_provider_multipart_and_local_storage_standins(self):
        """Local HTTP evidence only: no live AI, storage, credentials or provider quality claims."""
        import requests
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                message = BytesParser(policy=default).parsebytes(
                    ('Content-Type: ' + self.headers['Content-Type'] + '\r\n\r\n').encode() + body)
                fields = {part.get_param('name', header='Content-Disposition'): part.get_payload(decode=True)
                          for part in message.iter_parts()}
                calls.append((self.path, set(fields)))
                if self.path == '/generate':
                    payload = picture(size=(int(fields['width']), int(fields['height'])))
                    content_type = 'image/png'
                else:
                    with Image.open(io.BytesIO(fields['file'])) as image:
                        payload = json.dumps({'secure_url': 'https://example.com/local.png',
                                              'public_id': 'local', 'format': 'png',
                                              'width': image.width, 'height': image.height,
                                              'bytes': len(fields['file'])}).encode()
                    content_type = 'application/json'
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = 'http://127.0.0.1:' + str(server.server_port)
        session = requests.Session()
        session.trust_env = False

        def provider(url, **kwargs):
            self.assertIn('/accounts/local-test/ai/run/local-model', url)
            return session.post(base + '/generate', **kwargs)

        def upload(stream, **kwargs):
            response = session.post(base + '/upload', files={'file': ('image.png', stream, 'image/png')}, timeout=10)
            response.raise_for_status()
            return response.json()

        try:
            with patch('fabricapp.ai.providers.cloudflare_engine.requests.post', side_effect=provider), \
                 patch('fabricapp.services.cloudinary_service.cloudinary.uploader.upload', side_effect=upload):
                response = post(options='{"draft_mode": true}',
                                face_image=SimpleUploadedFile('face.png', picture(), content_type='image/png'))
                events = [json.loads(chunk) for chunk in response.streaming_content]
                response.close()
            self.assertEqual(events[-1]['status'], 'completed')
            generated = [fields for path, fields in calls if path == '/generate']
            self.assertEqual(len(generated), 7)
            self.assertEqual(sum(path == '/upload' for path, fields in calls), 8)
            self.assertTrue(all('input_image_2' in fields for fields in generated[:4]))
            self.assertTrue(all('input_image_2' not in fields for fields in generated[4:]))
        finally:
            session.close()
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
