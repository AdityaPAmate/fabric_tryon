"""Replay saved AI responses through old/new processing; NEVER calls AI or storage."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tryon.settings')
import django
django.setup()
from django.test import override_settings
from PIL import Image
from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.catalog_engine.registry import get_request_definition
from fabricapp.catalog_engine.runner import generate_catalog, Services


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.report / 'report.json').read_text(encoding='utf-8'))
    request = report['request']
    base = {key: request[key] for key in ('garment_type', 'garment_style', 'fabric_type', 'seed', 'guidance', 'background')
            if request.get(key) is not None}
    base['options'] = request.get('options') or {}
    base.update({key: value for key, value in request.get('generated_person', {}).items() if value is not None})
    fabric = (args.report / 'garment_source.jpg').read_bytes()
    source = {**base, 'fabric_image': io.BytesIO(fabric)}
    definition = get_request_definition(source)
    saved = {image['view']: (args.report / image['report_output_path']).read_bytes()
             for image in report['catalog']['images']}
    references = {shot.reference.read_bytes(): saved[shot.key] for shot in definition.shots
                  if shot.operation == 'template_edit'}
    results, pixels = [], []
    for enabled in (False, True):
        uploads = {}
        lock = threading.Lock()
        calls = []
        def edit(**kwargs):
            payload = references[kwargs['person_image'].getvalue()]
            with lock:
                calls.append(1)
            return GenerationResult(payload, kwargs['prompt_config']['seed'])
        def upload(payload):
            key = hashlib.sha256(payload).hexdigest()
            with lock:
                uploads[key] = payload
            return {'url': key}
        def forbidden(**kwargs):
            raise AssertionError('Unexpected pipeline generation in this replay')
        with override_settings(CATALOG_PERFORMANCE_ENABLED=enabled, CATALOG_GENERATION_WORKERS=2):
            started = time.perf_counter()
            events = list(generate_catalog({**base, 'fabric_image': io.BytesIO(fabric)}, threading.Event(),
                                           Services(forbidden, edit, upload)))
            elapsed = time.perf_counter() - started
        complete = events[-1]
        assert complete['status'] == 'completed', complete
        decoded = {}
        for item in complete['images'] + [complete['collage']]:
            with Image.open(io.BytesIO(uploads[item['url']])) as image:
                decoded[item['view']] = (image.size, hashlib.sha256(image.convert('RGB').tobytes()).hexdigest())
        pixels.append(decoded)
        results.append({'mode': 'new' if enabled else 'rollback', 'local_seconds': round(elapsed, 3),
                        'replayed_ai_responses': len(calls), 'mock_uploads': len(uploads)})
    assert pixels[0] == pixels[1], 'Decoded shot or collage pixels changed'
    summary = {'source_report': str(args.report), 'no_external_requests': True,
               'note': 'Local saved-response replay, not deployed generation latency.',
               'identical_decoded_pixels': True, 'runs': results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
