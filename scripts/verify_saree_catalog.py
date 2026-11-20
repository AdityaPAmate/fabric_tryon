"""Replay one saved saree report with exactly one six-shot catalog request.

This spends four provider generations and uploads six shots through the deployed application.
Run only with the user's explicit generation budget authorization.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    report = json.loads((args.report / 'report.json').read_text(encoding='utf-8'))
    request = report['request']
    assert request['garment_type'] == 'saree'
    out = Path(__file__).resolve().parents[1] / 'outputs' / ('saree_redesign_' + args.revision)
    out.mkdir(parents=True, exist_ok=False)  # Refuse accidental reruns/spending.
    fabric = (args.report / 'garment_source.jpg').read_bytes()
    (out / 'source.jpg').write_bytes(fabric)
    payload = {key: request[key] for key in ('garment_type', 'fabric_type', 'seed', 'guidance')}
    payload['options'] = json.dumps(request['options'])
    for key in ('gender', 'body_type', 'face_choice'):
        if request['generated_person'].get(key):
            payload[key] = request['generated_person'][key]
    for key in ('background', 'additional_style_note'):
        if request.get(key):
            payload[key] = request[key]
    (out / 'request.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    events = []
    started = time.perf_counter()
    with requests.post(request['api_url'], data=payload,
                       files={'fabric_image': ('saree.jpg', fabric, 'image/jpeg')},
                       stream=True, timeout=(20, 360)) as response:
        response.raise_for_status()
        for line in response.iter_lines(chunk_size=1):
            if not line:
                continue
            event = json.loads(line)
            events.append(event)
            (out / 'events.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
            if event['event'] != 'heartbeat':
                print(event['event'], event.get('view', ''), event.get('error', ''), flush=True)
    elapsed = round(time.perf_counter() - started, 3)
    complete = next(e for e in reversed(events) if e['event'] == 'complete')
    # Save/download even failed-quality results before assertions, for review.
    for item in complete['images'] + ([complete['collage']] if complete.get('collage') else []):
        response = requests.get(item['url'], timeout=(20, 90))
        response.raise_for_status()
        (out / f"{item['view']}.{item['format']}").write_bytes(response.content)
    summary = {'request_seconds': elapsed, 'source_report': str(args.report), **complete}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    assert complete['status'] == 'completed' and not complete['failed_views']
    assert len(complete['images']) == 6
    assert complete['collage']['aspect_ratio'] == '3:4'
    for item in complete['images']:
        generation = item['generation']
        if generation.get('kind') != 'derived_crop':
            assert generation['deployment_revision'].startswith(args.revision)
        if generation.get('no_new_ai_generation'):
            assert item['view'] in ('fabric_texture', 'border', 'pleats')
            if item['view'] == 'pleats':
                front = next(image for image in complete['images'] if image['view'] == 'front')
                assert generation['source_view'] == 'front'
                assert generation['source_image_sha256'] == hashlib.sha256(
                    (out / f"front.{front['format']}").read_bytes()).hexdigest()
        else:
            assert len(generation['attempts']) == 1
        if item['view'] == 'back_pallu':
            assert set(generation['input_hashes']) == {'input_image_0', 'input_image_1'}
    print(f'Completed in {elapsed}s; evidence: {out}', flush=True)


if __name__ == '__main__':
    main()
