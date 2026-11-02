"""Exercise the actual local report HTTP handler using isolated temporary files."""
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen

spec = importlib.util.spec_from_file_location('tester_server', Path(__file__).with_name('server.py'))
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        server_module.ROOT = self.root
        server_module.OUTPUTS_DIR = self.root / 'outputs'
        server_module.REPORTS_DIR = self.root / 'reports'
        server_module.OUTPUTS_DIR.mkdir()
        self.image = server_module.OUTPUTS_DIR / 'generated_0001.png'
        self.image.write_bytes(b'report image fixture')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), server_module.TesterRequestHandler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()
        self.temp.cleanup()

    def post(self, payload):
        request = Request(f'http://127.0.0.1:{self.server.server_port}/save-report',
                          data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
        report = json.loads((self.root / result['report_path'] / 'report.json').read_text(encoding='utf-8'))
        aggregate = json.loads((self.root / result['aggregate_path']).read_text(encoding='utf-8'))
        self.assertEqual(aggregate[-1], report)
        return report

    def payload(self):
        return {'issue_text': 'Check the velvet surface', 'request': {
            'garment_type': 'shirt', 'generation_mode': 'single', 'fabric_type': 'velvet',
            'options': {'draft_mode': False, 'fabric_crop_box': [0, 0, 40, 60]},
            'person_image_used': True, 'generated_person': {'gender': None}},
            'output': {'format': 'png', 'url': 'https://res.cloudinary.com/example.png'},
            'local_output_path': 'outputs/generated_0001.png', 'generation_seed': 42}

    def test_material_crop_and_actual_person_settings_survive_report(self):
        report = self.post(self.payload())
        self.assertEqual(report['schema_version'], 2)
        self.assertEqual(report['request']['fabric_type'], 'velvet')
        self.assertEqual(report['request']['options']['fabric_crop_box'], [0, 0, 40, 60])
        self.assertIsNone(report['request']['generated_person']['gender'])
        self.assertEqual(report['generation_seed'], 42)
        copied = self.root / report['report_path'] / report['files']['generated_output']['local_output_path']
        self.assertEqual(copied.read_bytes(), self.image.read_bytes())

    def test_partial_catalog_archives_all_ready_images_and_failed_view(self):
        payload = self.payload()
        payload['request'].update(generation_mode='catalog', catalog_view='cuff')
        payload['catalog'] = {'catalog_id': 'test-catalog', 'status': 'partial', 'total': 6,
            'images': [{'view': view, 'format': 'png', 'local_output_path': 'outputs/generated_0001.png',
                        'generation_seed': 43, 'generation': {'prompt_version': 'catalog-edit-v1'}}
                       for view in ['front', 'back']],
            'failed_views': [{'view': 'cuff', 'error': 'output_rejected', 'provider_code': 3030}]}
        report = self.post(payload)
        self.assertEqual(report['catalog']['status'], 'partial')
        self.assertEqual(report['catalog']['failed_views'][0]['provider_code'], 3030)
        for image in report['catalog']['images']:
            copied = self.root / report['report_path'] / image['report_output_path']
            self.assertEqual(copied.read_bytes(), self.image.read_bytes())
            self.assertEqual(image['generation_seed'], 43)
        index = json.loads((server_module.REPORTS_DIR / 'index.jsonl').read_text())
        self.assertEqual(index['catalog_id'], 'test-catalog')
        self.assertEqual(index['catalog_view'], 'cuff')

    def test_old_request_still_saves(self):
        payload = self.payload()
        payload['request'] = {'garment_type': 'shirt'}
        report = self.post(payload)
        self.assertIsNone(report['catalog'])

    def test_catalog_does_not_copy_outside_outputs(self):
        secret = self.root / 'private.txt'
        secret.write_text('private')
        destination = self.root / 'example_report'
        destination.mkdir()
        result = server_module.save_catalog_outputs({'images': [
            {'view': '../../private', 'format': 'png', 'local_output_path': 'private.txt'}]}, destination)
        self.assertIsNone(result['images'][0]['report_output_path'])
        self.assertTrue(result['images'][0]['copy_error'])


if __name__ == '__main__':
    unittest.main()
