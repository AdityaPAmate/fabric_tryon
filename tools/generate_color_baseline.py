"""Capture real, unmodified current-engine outputs for colour regression work.

Uses existing .env credentials; never saves credentials or uploads to Cloudinary.
Run with the project's virtualenv Python. Completed cases are never regenerated.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def render_gallery(output, manifest):
    """Local test evidence only; images keep their original output bytes."""
    rows = []
    for fabric in dict.fromkeys(c['fabric'] for c in manifest['cases']):
        cases = [c for c in manifest['cases'] if c['fabric'] == fabric]
        first = cases[0]
        cells = [f'<figure><figcaption>Original swatch</figcaption><img src="{first["id"]}/original{Path(fabric).suffix}"></figure>',
                 f'<figure><figcaption>Actual prepared input</figcaption><img src="{first["id"]}/input_image_1.jpg"></figure>']
        for case in cases:
            if case['status'] != 'complete':
                continue
            seed = case['effective_seed']
            label = 'Studio' if case['background'] is None else 'Outdoor terrace'
            retry = ' — fallback prompt/seed: compare separately' if seed != manifest['fixed_request']['seed'] else ''
            cells.append(f'<figure><figcaption>{label}; seed {seed}{retry}</figcaption><a href="{case["id"]}/{case["output"]}"><img src="{case["id"]}/{case["output"]}"></a></figure>')
        rows.append('<section><h2>' + html.escape(fabric) + '</h2><div class="grid">' + ''.join(cells) + '</div></section>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Colour baseline — before changes</title>
<style>body{font:16px system-ui;margin:30px;color:#202020;background:white}h1{font-size:26px}h2{font-size:19px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}figure{margin:0}figcaption{min-height:48px;font-size:14px}img{width:100%;height:430px;object-fit:contain}section{border-top:1px solid #ddd;padding:20px 0}p{max-width:1000px;line-height:1.5}@media(max-width:800px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}</style>
<h1>Colour baseline — current engine, before changes</h1>
<p>Five fabrics, two backgrounds. Same face reference; generated trim body; business blazer; front view; guidance 7; final resolution. Outputs are uncorrected. Click an output for full size.</p>
<p>Retries may change both seed and prompt; these are labelled and cannot isolate background effects. This is a face-reference baseline, not a full-person-photo editing benchmark. No pure white fabric is included.</p>
<p><a href="baseline.json">Complete settings, actual requests and provenance</a></p>'''
    (output / 'index.html').write_text(page + ''.join(rows) + '</html>', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fabric-dir', type=Path, required=True)
    parser.add_argument('--face-image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    from dotenv import dotenv_values
    from django.conf import settings
    config = dotenv_values(ROOT / '.env')
    names = ['CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_MODEL']
    if not all(config.get(name) for name in names):
        raise SystemExit('Missing Cloudflare configuration in project .env')
    settings.configure(**{name: config[name] for name in names}, SAVE_DEBUG_FILES=False)
    import requests
    from PIL import Image
    from fabricapp.ai.main import generate_tryon_image
    from fabricapp.ai.router import build_prompt_config
    from fabricapp.ai.cloudflare_engine import _build_subject, MAX_INPUT_DIM
    from fabricapp.ai.image_utils import resize_to_fit

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / 'baseline.json'
    fabrics = ['kurti_fabric3.png', 'red_velvet7.jpg', 'plain_green_fabric.jpg',
               'faint_purple_fabric.jpg', 'blue_checks_fabric11.png']
    fixed = dict(garment_type='blazer', garment_style='business', gender='men',
                 body_type='trim', camera_view='front', pose=None,
                 garment_details=[], additional_style_note=None,
                 options={'draft_mode': False}, seed=42, guidance=7.0)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest['model'] != config['CLOUDFLARE_MODEL'] or manifest['fixed_request'] != fixed:
            raise SystemExit('Baseline configuration differs; choose a new output directory.')
    else:
        manifest = {
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'model': config['CLOUDFLARE_MODEL'], 'fixed_request': fixed,
            'scenario': 'face_photo', 'person_reference': str(args.face_image),
            'person_sha256': digest(args.face_image.read_bytes()),
            'notes': ['Current local engine, not a reconstruction of historical deployment.',
                      'Same face reference; body generated with fixed trim setting.',
                      'Same seed does not guarantee deterministic provider output.',
                      'Uses current application prompts; no test-specific prompt edits or colour correction.',
                      'Outdoor means white_marble_terrace, studio means background omitted.'],
            'source_hashes': {}, 'cases': [],
        }
        for source in sorted((ROOT / 'fabricapp').rglob('*.py')):
            relative = source.relative_to(ROOT)
            target = output / 'source_snapshot' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest['source_hashes'][relative.as_posix()] = digest(source.read_bytes())
        shutil.copy2(args.face_image, output / 'person_reference.png')
    if digest(args.face_image.read_bytes()) != manifest['person_sha256']:
        raise SystemExit('Person reference changed; choose a new baseline.')
    for relative, expected in manifest['source_hashes'].items():
        if digest((ROOT / relative).read_bytes()) != expected:
            raise SystemExit('Application source changed; choose a new baseline.')
    real_post = requests.post
    for fabric in fabrics:
        for scene, background in [('studio', None), ('outdoor', 'white_marble_terrace')]:
            case_id = Path(fabric).stem + '__' + scene
            case_dir = output / case_id
            case_dir.mkdir(exist_ok=True)
            case = next((c for c in manifest['cases'] if c['id'] == case_id), None)
            raw = (args.fabric_dir / fabric).read_bytes()
            if case and case['fabric_sha256'] != digest(raw):
                raise SystemExit('Fabric changed; choose a new baseline.')
            if case and case['status'] == 'complete':
                if digest((case_dir / case['output']).read_bytes()) != case['output_sha256']:
                    raise SystemExit('Saved output was modified.')
                continue
            if case is None:
                case = {'id': case_id, 'fabric': fabric, 'fabric_sha256': digest(raw),
                        'background': background, 'status': 'prepared', 'attempts': []}
                manifest['cases'].append(case)
            (case_dir / ('original' + Path(fabric).suffix)).write_bytes(raw)
            request = dict(fixed, background=background)
            face = io.BytesIO(args.face_image.read_bytes())
            context = dict(request, use_face_reference=True, face_image=face,
                           fabric_image=io.BytesIO(raw))
            prompt_config = build_prompt_config(scenario='face_photo',
                garment_type='blazer', garment_style='business', context=context,
                seed=42, guidance=7.0)
            write_json(case_dir / 'prompt_config.json', prompt_config)
            write_json(case_dir / 'request.json', dict(request, face_image='../person_reference.png',
                       fabric_image='original' + Path(fabric).suffix))
            subject, reference, width, height = _build_subject('face_photo', None, None, face, 1536, None)
            (case_dir / 'input_image_0.jpg').write_bytes(subject.getvalue())
            (case_dir / 'input_image_2.jpg').write_bytes(reference.getvalue())
            (case_dir / 'input_image_1.jpg').write_bytes(resize_to_fit(io.BytesIO(raw), MAX_INPUT_DIM).getvalue())
            write_json(manifest_path, manifest)
            if args.prepare_only:
                continue

            def captured_post(url, **kwargs):
                index = len(case['attempts']) + 1
                data = dict(kwargs['data'])
                files = kwargs['files']
                hashes = {}
                for slot, (_, buffer, _) in files.items():
                    payload = buffer.getvalue()
                    (case_dir / f'attempt_{index}_{slot}.jpg').write_bytes(payload)
                    hashes[slot] = digest(payload)
                attempt = {'index': index, 'request': data, 'input_hashes': hashes,
                           'started_at_utc': datetime.now(timezone.utc).isoformat()}
                case['attempts'].append(attempt)
                write_json(manifest_path, manifest)
                response = real_post(url, **kwargs)
                attempt['http_status'] = response.status_code
                write_json(manifest_path, manifest)
                return response

            print('Generating ' + case_id, flush=True)
            case['status'] = 'running'
            write_json(manifest_path, manifest)
            try:
                with patch('fabricapp.ai.cloudflare_engine.requests.post', captured_post):
                    generation = generate_tryon_image(fabric_image=io.BytesIO(raw),
                        face_image=io.BytesIO(args.face_image.read_bytes()), **request)
                with Image.open(io.BytesIO(generation.image_bytes)) as image:
                    suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}.get(image.format, '.img')
                    case['dimensions'] = list(image.size)
                filename = 'output' + suffix
                (case_dir / filename).write_bytes(generation.image_bytes)
                case.update(status='complete', output=filename,
                            output_sha256=digest(generation.image_bytes),
                            effective_seed=generation.effective_seed,
                            diagnostics=generation.diagnostics)
                print('Completed ' + case_id, flush=True)
            except Exception as exc:
                # Do not stringify network exceptions: their URL may include account identifiers.
                case.update(status='failed', error_type=type(exc).__name__,
                            provider_code=getattr(exc, 'provider_code', None),
                            failure_type=getattr(exc, 'failure_type', None))
                print('Failed ' + case_id + ': ' + type(exc).__name__, flush=True)
                write_json(manifest_path, manifest)
                if not case['attempts'] or not any(a.get('http_status') for a in case['attempts']):
                    raise SystemExit('Network unavailable; remaining cases not sent.')
            write_json(manifest_path, manifest)
    complete = sum(c['status'] == 'complete' for c in manifest['cases'])
    render_gallery(output, manifest)
    print(f'Baseline: {complete}/10 completed. {manifest_path}', flush=True)
    if not args.prepare_only and complete != 10:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
