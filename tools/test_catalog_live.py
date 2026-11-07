"""Run one real catalog request; save each independent image and stream event."""
import argparse
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tryon.settings')
import django
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient
from fabricapp.services.cloudinary_service import upload_generated_image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fabric', required=True)
    parser.add_argument('--garment', default='shirt')
    parser.add_argument('--gender')
    parser.add_argument('--edition')
    parser.add_argument('--product-json', type=Path)
    parser.add_argument('--person-image')
    parser.add_argument('--style')
    parser.add_argument('--output', required=True)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--material', default='unspecified')
    parser.add_argument('--face-image')
    parser.add_argument('--face-choice')
    parser.add_argument('--background')
    parser.add_argument('--reference', help='Existing front output for a focused view prompt recheck')
    parser.add_argument('--anchor', action='append', default=[], help='Additional saved dependency: shot_key=PATH')
    parser.add_argument('--views', nargs='+', default=['back'])
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    import shutil, hashlib
    shutil.copy2(args.fabric, output / ('original_swatch' + Path(args.fabric).suffix))
    (output / 'run.json').write_text(json.dumps({
        'garment': args.garment, 'edition': args.edition, 'draft': args.draft,
        'material': args.material, 'fabric_sha256': hashlib.sha256(Path(args.fabric).read_bytes()).hexdigest(),
        'evidence': 'real provider calls and real Cloudinary uploads',
    }, indent=2), encoding='utf-8')
    events = []
    current_view = ['front']

    if args.reference:
        from fabricapp.catalog_engine.registry import get_definition
        from fabricapp.catalog_engine.runner import Services, generate_shot
        from fabricapp.catalog_engine.validation import validate_definition
        from fabricapp.catalog import generate_edit, generate_tryon_image
        import io
        definition = get_definition(args.garment, args.edition)
        validate_definition(definition)
        views = {shot.key: shot for shot in definition.shots}
        if any(view not in views for view in args.views):
            parser.error('Unknown view; choose from: ' + ', '.join(views))
        data = {'fabric_image': io.BytesIO(Path(args.fabric).read_bytes()), 'garment_type': args.garment,
                'fabric_type': args.material, 'options': {'draft_mode': args.draft},
                'background': args.background, 'seed': 42}
        anchor = definition.shots[0].key
        anchors, seeds = {anchor: Path(args.reference).read_bytes()}, {anchor: 42}
        for item in args.anchor:
            key, separator, path = item.partition('=')
            if not separator or key not in views:
                parser.error('--anchor must be a known shot_key=PATH')
            anchors[key], seeds[key] = Path(path).read_bytes(), 42
        services = Services(generate_tryon_image, generate_edit, upload_generated_image)
        for view in args.views:
            shot = views[view]
            if shot.operation == 'pipeline' or shot.identity_from == 'request':
                parser.error('Run a full catalog to test initial/pipeline shots')
            if any(key not in anchors for key in shot.dependencies):
                parser.error('Reference does not provide the required dependency for ' + view)
            config_seed = seeds[shot.dependencies[0]] if shot.dependencies else 42
            (output / f'{view}_prompt.json').write_text(json.dumps(definition.build_config(data, shot, config_seed), indent=2))
            result = generate_shot(data, shot, definition, anchors, seeds, services)
            from PIL import Image
            with Image.open(io.BytesIO(result.image_bytes)) as image:
                extension = (image.format or 'PNG').lower()
            (output / f'{view}.{extension}').write_bytes(result.image_bytes)
            image = {'view': view, **upload_generated_image(result.image_bytes),
                     'generation_seed': result.effective_seed, 'generation': result.diagnostics,
                     'reference_template': shot.reference.name if shot.reference else None}
            events.append(image)
            (output / 'recheck.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
            print(json.dumps(image), flush=True)
        return

    def save_upload(raw):
        # Order is fixed: only successful provider responses reach the uploader.
        from PIL import Image
        import io
        with Image.open(io.BytesIO(raw)) as image:
            extension = (image.format or 'PNG').lower()
        (output / f'{current_view[0]}.{extension}').write_bytes(raw)
        return upload_generated_image(raw)

    # Capture the generator's view before generation, not after stream delivery
    # (the worker may already have started the next image).
    from fabricapp.catalog import generate_catalog, generate_edit
    def capture_edit(**kwargs):
        view = current_view[0]
        (output / f'{view}_prompt.json').write_text(json.dumps(kwargs['prompt_config'], indent=2), encoding='utf-8')
        try:
            result = generate_edit(**kwargs)
        except Exception as exc:
            trace = {'failure_type': getattr(exc, 'failure_type', None), 'provider_code': getattr(exc, 'provider_code', None), 'generation': getattr(exc, 'diagnostics', None)}
            (output / f'{view}_trace.json').write_text(json.dumps(trace, indent=2), encoding='utf-8')
            raise
        (output / f'{view}_trace.json').write_text(json.dumps(result.diagnostics, indent=2), encoding='utf-8')
        return result
    def capture(data, stopped):
        for event in generate_catalog(data, stopped):
            if event['event'] == 'composing':
                current_view[0] = 'catalog'
            if event['event'] == 'generating':
                current_view[0] = event['view']
            yield event

    with override_settings(ALLOWED_HOSTS=['testserver'], SAVE_DEBUG_FILES=False), patch(
        'fabricapp.catalog.upload_generated_image', side_effect=save_upload
    ), patch('fabricapp.catalog.generate_edit', side_effect=capture_edit), patch('fabricapp.catalog.generate_catalog', side_effect=capture):
        payload = {
            'fabric_image': SimpleUploadedFile(Path(args.fabric).name, Path(args.fabric).read_bytes()),
            'garment_type': args.garment, 'gender': args.gender or ('women' if args.garment == 'saree' else 'men'), 'body_type': 'trim',
            'fabric_type': args.material,
            'seed': '42', 'options': json.dumps({'draft_mode': args.draft}),
        }
        if args.edition:
            payload['catalog_edition'] = args.edition
        if args.product_json:
            payload['catalog_product'] = args.product_json.read_text(encoding='utf-8')
        if args.style:
            payload['garment_style'] = args.style
        if args.person_image:
            payload['person_image'] = SimpleUploadedFile(Path(args.person_image).name, Path(args.person_image).read_bytes())
            payload.pop('gender', None)
            payload.pop('body_type', None)
        if args.face_choice:
            payload['face_choice'] = args.face_choice
        if args.face_image:
            payload['face_image'] = SimpleUploadedFile(Path(args.face_image).name, Path(args.face_image).read_bytes())
        if args.background:
            payload['background'] = args.background
        response = APIClient().post('/api/generate-catalog/', payload, format='multipart')
        if response.status_code != 200:
            raise RuntimeError(f'HTTP {response.status_code}: {response.data}')
        try:
            for line in response.streaming_content:
                event = json.loads(line)
                events.append(event)
                (output / 'events.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
                print(json.dumps(event), flush=True)
        finally:
            response.close()
    if not events or events[-1].get('status') != 'completed':
        raise SystemExit('Catalog did not complete; inspect events.json')


if __name__ == '__main__':
    main()
