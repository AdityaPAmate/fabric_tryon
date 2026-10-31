"""Live paired swatch/material checks via the public generation coordinator.

Images and credentials stay out of Git. No Cloudinary upload is performed.
"""
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.generate_color_baseline import write_json, digest

PLAN = (
    ('shirt', None, 'men', 'red_velvet7.jpg', 'velvet'),
    ('pant', None, 'men', 'red_velvet7.jpg', 'velvet'),
    ('kurta', 'plain', 'men', 'faint_purple_fabric.jpg', 'cotton'),
    ('kurti_pant', None, 'women', 'faint_purple_fabric.jpg', 'silk'),
    ('saree', None, 'women', 'faint_purple_fabric.jpg', 'silk'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fabric-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--garments', nargs='+', choices=[case[0] for case in PLAN])
    args = parser.parse_args()
    selected_plan = [case for case in PLAN if not args.garments or case[0] in args.garments]
    from dotenv import dotenv_values
    from django.conf import settings
    values = dotenv_values(ROOT / '.env')
    keys = ('CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_MODEL')
    if not all(values.get(key) for key in keys):
        raise SystemExit('Cloudflare configuration is incomplete.')
    settings.configure(**{key: values[key] for key in keys}, SAVE_DEBUG_FILES=False)
    import requests
    from PIL import Image, ImageDraw
    from fabricapp.ai.main import generate_tryon_image
    from fabricapp.ai.router import build_prompt_config
    from fabricapp.ai.fabric_material import material_prompt

    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    path = output / 'results.json'
    if path.exists():
        manifest = json.loads(path.read_text())
        assert manifest['model'] == values['CLOUDFLARE_MODEL']
    else:
        manifest = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
                    'model': values['CLOUDFLARE_MODEL'], 'source_hashes': {}, 'cases': [],
                    'notes': ['Generated adults; no person or face photo sent.',
                              'Same seed/input/guidance/size per pair; alternate-seed fallback disabled.',
                              'One sample per case is not a physical material or colour accuracy benchmark.']}
        for source in sorted((ROOT / 'fabricapp').rglob('*.py')):
            relative = source.relative_to(ROOT); target = output / 'source_snapshot' / relative
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, target)
            manifest['source_hashes'][relative.as_posix()] = digest(source.read_bytes())
    for relative, expected in manifest['source_hashes'].items():
        assert digest((ROOT / relative).read_bytes()) == expected, 'Source changed; choose a new output directory.'
    real_post = requests.post
    for garment, style, gender, filename, selected in selected_plan:
        raw = (args.fabric_dir / filename).read_bytes()
        request = dict(garment_type=garment, garment_style=style, gender=gender,
                       body_type='trim', camera_view='front', background=None,
                       options={'draft_mode': False}, seed=42, guidance=7.0)
        reference = build_prompt_config(scenario='generated_person', garment_type=garment,
            garment_style=style, context=dict(request, fabric_image=io.BytesIO(raw)), seed=42, guidance=7)
        for fabric_type in ('unspecified', selected):
            case_id = garment + '__' + fabric_type
            folder = output / case_id; folder.mkdir(exist_ok=True)
            case = next((c for c in manifest['cases'] if c['id'] == case_id), None)
            if case is None:
                case = {'id': case_id, 'garment': garment, 'fabric_type': fabric_type,
                        'source': filename, 'source_sha256': digest(raw), 'status': 'prepared', 'attempts': []}
                manifest['cases'].append(case)
            assert digest(raw) == case['source_sha256']
            if case['status'] == 'complete':
                assert digest((folder / case['output']).read_bytes()) == case['output_sha256']
                continue
            (folder / ('original' + Path(filename).suffix)).write_bytes(raw)
            write_json(folder / 'request.json', dict(request, fabric_type=fabric_type))

            def controlled_config(**kwargs):
                result = build_prompt_config(**kwargs)
                addition = material_prompt(fabric_type, garment, style)
                for key in ('prompt', 'safety_fallback_prompt'):
                    if key in reference:
                        assert result[key].replace(addition, '', 1) == reference[key] if addition else result[key] == reference[key]
                assert result['fabric_colour_reference'] == reference['fabric_colour_reference']
                result['safety_retry_count'] = 0
                write_json(folder / 'prompt_config.json', result)
                return result

            def capture(url, **kwargs):
                hashes = {slot: digest(item[1].getvalue()) for slot, item in kwargs['files'].items()}
                baseline = next((c for c in manifest['cases'] if c['id'] == garment + '__unspecified'), None)
                if fabric_type != 'unspecified' and baseline and baseline['attempts']:
                    first = baseline['attempts'][0]
                    assert hashes == first['input_hashes']
                    for key in ('seed', 'guidance', 'width', 'height'):
                        assert kwargs['data'][key] == first['request'][key]
                attempt = {'request': dict(kwargs['data']), 'input_hashes': hashes}
                case['attempts'].append(attempt)
                for slot, item in kwargs['files'].items():
                    (folder / (slot + '.jpg')).write_bytes(item[1].getvalue())
                write_json(path, manifest)
                response = real_post(url, **kwargs)
                attempt['http_status'] = response.status_code
                write_json(path, manifest)
                return response

            print('Generating ' + case_id, flush=True)
            try:
                with patch('fabricapp.ai.main.build_prompt_config', controlled_config), \
                     patch('fabricapp.ai.cloudflare_engine.requests.post', capture):
                    result = generate_tryon_image(fabric_image=io.BytesIO(raw), fabric_type=fabric_type, **request)
                with Image.open(io.BytesIO(result.image_bytes)) as im:
                    suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}[im.format]
                    size = list(im.size); im.verify()
                name = 'output' + suffix; (folder / name).write_bytes(result.image_bytes)
                case.update(status='complete', output=name, output_sha256=digest(result.image_bytes),
                            size=size, effective_seed=result.effective_seed, diagnostics=result.diagnostics)
                print('Completed ' + case_id, flush=True)
            except Exception as exc:
                case.update(status='failed', error_type=type(exc).__name__,
                            provider_code=getattr(exc, 'provider_code', None),
                            failure_type=getattr(exc, 'failure_type', None))
                print('Failed ' + case_id + ': ' + type(exc).__name__, flush=True)
                if case['failure_type'] == 'allocation_exhausted':
                    write_json(path, manifest)
                    raise SystemExit('Cloudflare allocation exhausted; remaining requests were not sent.')
            write_json(path, manifest)
    sheet = Image.new('RGB', (900, len(selected_plan) * 340), 'white'); draw = ImageDraw.Draw(sheet)
    for row, (garment, _, _, filename, selected) in enumerate(selected_plan):
        before = next(c for c in manifest['cases'] if c['id'] == garment + '__unspecified')
        after = next(c for c in manifest['cases'] if c['id'] == garment + '__' + selected)
        images = [(output / before['id'] / ('original' + Path(filename).suffix), garment + ': original')]
        for c in (before, after):
            if c['status'] == 'complete': images.append((output / c['id'] / c['output'], garment + ': ' + c['fabric_type']))
        for col, (image_path, label) in enumerate(images):
            im = Image.open(image_path).convert('RGB'); im.thumbnail((285, 305))
            sheet.paste(im, (col * 300 + (300 - im.width) // 2, row * 340 + 30))
            draw.text((col * 300 + 5, row * 340 + 8), label, fill='black')
    sheet.save(output / 'overview.jpg', quality=95)
    count = sum(c['status'] == 'complete' for c in manifest['cases'])
    expected = len(selected_plan) * 2
    selected_ids = {garment + '__' + material for garment, _, _, _, chosen in selected_plan
                    for material in ('unspecified', chosen)}
    selected_complete = sum(c['status'] == 'complete' and c['id'] in selected_ids for c in manifest['cases'])
    print(f'Completed {count} total; {selected_complete}/{expected} selected live cases; {path}', flush=True)
    if selected_complete != expected: raise SystemExit(1)


if __name__ == '__main__':
    main()
