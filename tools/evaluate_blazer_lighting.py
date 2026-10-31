"""Paired live lighting/colour/material check using baseline seed/variant.

No fallback resampling: a rejected case stays failed rather than changing the
experimental conditions. Credentials and account URLs are never persisted.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.generate_color_baseline import write_json, digest


def gallery(output, manifest):
    rows = []
    baseline = Path(manifest['baseline'])
    import os
    for case in manifest['cases']:
        old = baseline / case['id']
        prefix = Path(os.path.relpath(old, output)).as_posix()
        images = [(prefix + '/original' + Path(case['fabric']).suffix, 'Original fabric'),
                  (prefix + '/' + case['before_output'], 'Before')]
        if case['status'] == 'complete':
            label = manifest.get('experiment', 'lighting')
            if manifest.get('fabric_type'):
                label += ': ' + manifest['fabric_type']
            images.append((case['id'] + '/' + case['output'], label + ' change'))
        row = ''.join(f'<figure><figcaption>{label}</figcaption><a href="{html.escape(src)}"><img src="{html.escape(src)}"></a></figure>' for src, label in images)
        rows.append(f'<section><h2>{html.escape(case["id"])} — seed {case["seed"]}</h2><div>{row}</div></section>')
    (output / 'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Blazer prompt test</title>
<style>body{font:16px system-ui;margin:30px}h1{font-size:25px}h2{font-size:18px}section{border-top:1px solid #ccc;padding:15px 0}section div{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}figure{margin:0}img{width:100%;height:500px;object-fit:contain}p{max-width:1000px;line-height:1.5}</style>
<h1>Before / after — isolated prompt experiment</h1><p>Each pair uses identical prepared inputs, successful baseline seed, guidance, resolution and primary/compact prompt variant. Alternate-seed fallback is disabled in this test. The provider may be nondeterministic, so these single samples show observed results rather than proving causality. Full-size originals are linked.</p>''' + ''.join(rows), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--cases', nargs='+', help='Optional baseline case IDs for a focused experiment.')
    parser.add_argument('--experiment', choices=('lighting', 'colour', 'material'), default='lighting')
    parser.add_argument('--fabric-type', choices=('cotton', 'silk', 'velvet'))
    args = parser.parse_args()
    if args.experiment == 'material' and not args.fabric_type:
        parser.error('--fabric-type is required for the material experiment.')
    if args.fabric_type and args.experiment != 'material':
        parser.error('--fabric-type is only used by the material experiment.')
    from dotenv import dotenv_values
    from django.conf import settings
    config = dotenv_values(ROOT / '.env')
    names = ['CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_MODEL']
    if not all(config.get(name) for name in names):
        raise SystemExit('Missing Cloudflare configuration.')
    settings.configure(**{name: config[name] for name in names}, SAVE_DEBUG_FILES=False)
    import requests
    from PIL import Image
    from fabricapp.ai.blazer.builder import build_prompt
    from fabricapp.ai.blazer.lighting import scene_and_lighting
    from fabricapp.ai.fabric_colour import colour_reference_prompt
    from fabricapp.ai.blazer.materials import material_prompt
    from fabricapp.ai.cloudflare_engine import generate_tryon_image
    baseline = args.baseline.resolve()
    before = json.loads((baseline / 'baseline.json').read_text())
    if args.cases and not set(args.cases).issubset({c['id'] for c in before['cases']}):
        parser.error('Unknown baseline case ID.')
    assert before['model'] == config['CLOUDFLARE_MODEL']
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'comparison.json'
    if path.exists():
        manifest = json.loads(path.read_text())
        assert manifest['baseline_manifest_sha256'] == digest((baseline / 'baseline.json').read_bytes())
        assert manifest.get('experiment', 'lighting') == args.experiment
        assert manifest.get('fabric_type') == args.fabric_type
    else:
        manifest = {'created_at_utc': datetime.now(timezone.utc).isoformat(), 'experiment': args.experiment,
                    'fabric_type': args.fabric_type,
                    'baseline': str(baseline), 'model': before['model'],
                    'baseline_manifest_sha256': digest((baseline / 'baseline.json').read_bytes()),
                    'source_hashes': {}, 'cases': []}
        for source in sorted((ROOT / 'fabricapp').rglob('*.py')):
            relative = source.relative_to(ROOT)
            target = output / 'source_snapshot' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest['source_hashes'][relative.as_posix()] = digest(source.read_bytes())
    for relative, expected in manifest['source_hashes'].items():
        assert digest((ROOT / relative).read_bytes()) == expected, 'Source changed; use a new output directory.'
    real_post = requests.post
    for old in before['cases']:
        if args.cases and old['id'] not in args.cases:
            continue
        assert old['status'] == 'complete'
        successful = [a for a in old['attempts'] if a.get('http_status') == 200][-1]
        old_config = json.loads((baseline / old['id'] / 'prompt_config.json').read_text())
        compact = successful['request']['prompt'] == old_config['safety_fallback_prompt']
        assert compact or successful['request']['prompt'] == old_config['prompt']
        seed = successful['request']['seed']
        request = dict(before['fixed_request'], seed=seed, background=old['background'])
        if args.experiment == 'material':
            request['fabric_type'] = args.fabric_type
        fabric = baseline / old['id'] / ('original' + Path(old['fabric']).suffix)
        assert digest(fabric.read_bytes()) == old['fabric_sha256']
        context = dict(request, fabric_image=io.BytesIO(fabric.read_bytes()))
        if args.experiment == 'lighting':
            context['_lighting_experiment'] = True
        elif args.experiment == 'colour':
            context['_colour_reference_experiment'] = True
        current = build_prompt(scenario='face_photo', garment_style=request['garment_style'],
                               context=context,
                               seed=seed, guidance=request['guidance'])
        current['prompt'] = current['safety_fallback_prompt'] if compact else current['prompt']
        current['safety_retry_count'] = 0
        # Assert the only prompt difference is replacing the old scene/lighting block.
        text = successful['request']['prompt']
        if args.experiment == 'lighting':
            start = text.index('BACKGROUND:')
            end = text.index('FINAL:', start)
            assert text[:start] + scene_and_lighting('face_photo', old['background']) + text[end:] == current['prompt']
        elif args.experiment == 'colour':
            reference = colour_reference_prompt(current['fabric_colour_reference'])
            assert reference and current['prompt'].count(reference) == 1
            assert current['prompt'].replace(reference, '') == text
        else:
            reference = material_prompt(args.fabric_type)
            assert current['prompt'].count(reference) == 1
            assert current['prompt'].replace(reference, '') == text
        d = output / old['id']; d.mkdir(exist_ok=True)
        case = next((c for c in manifest['cases'] if c['id'] == old['id']), None)
        if case is None:
            case = {'id': old['id'], 'fabric': old['fabric'], 'seed': seed,
                    'compact': compact, 'before_output': old['output'],
                    'fabric_type': args.fabric_type,
                    'status': 'prepared', 'attempts': []}
            manifest['cases'].append(case)
        if case['status'] == 'complete':
            assert digest((d / case['output']).read_bytes()) == case['output_sha256']
            continue
        write_json(d / 'request.json', request)
        write_json(d / 'prompt_config.json', current)
        write_json(path, manifest)
        if args.prepare_only:
            continue

        def capture(url, **kwargs):
            hashes = {slot: digest(item[1].getvalue()) for slot, item in kwargs['files'].items()}
            assert hashes == successful['input_hashes'], 'Prepared inputs differ from baseline.'
            assert kwargs['data']['seed'] == seed
            attempt = {'request': dict(kwargs['data']), 'input_hashes': hashes}
            case['attempts'].append(attempt)
            write_json(path, manifest)
            response = real_post(url, **kwargs)
            attempt['http_status'] = response.status_code
            write_json(path, manifest)
            return response

        print('Generating ' + old['id'] + f' seed={seed} compact={compact}', flush=True)
        try:
            fabric = baseline / old['id'] / ('original' + Path(old['fabric']).suffix)
            with patch('fabricapp.ai.cloudflare_engine.requests.post', capture):
                result = generate_tryon_image(fabric_image=io.BytesIO(fabric.read_bytes()),
                    face_image=io.BytesIO((baseline / 'person_reference.png').read_bytes()),
                    scenario='face_photo', prompt_config=current, **{k:v for k,v in request.items() if k not in ('seed','guidance','fabric_type')})
            with Image.open(io.BytesIO(result.image_bytes)) as im:
                assert list(im.size) == old['dimensions']
                suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}[im.format]
            name = 'output' + suffix
            (d / name).write_bytes(result.image_bytes)
            case.update(status='complete', output=name, output_sha256=digest(result.image_bytes),
                        effective_seed=result.effective_seed, diagnostics=result.diagnostics)
            print('Completed ' + old['id'], flush=True)
        except Exception as exc:
            case.update(status='failed', error_type=type(exc).__name__,
                        failure_type=getattr(exc, 'failure_type', None))
            print('Failed ' + old['id'] + ': ' + type(exc).__name__, flush=True)
        write_json(path, manifest)
    gallery(output, manifest)
    count = sum(c['status'] == 'complete' for c in manifest['cases'])
    expected = len(args.cases) if args.cases else len(before['cases'])
    selected_complete = sum(c['status'] == 'complete' for c in manifest['cases']
                            if not args.cases or c['id'] in args.cases)
    print(f'Completed {count} total; {selected_complete}/{expected} selected; {path}', flush=True)
    if not args.prepare_only and selected_complete != expected:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
