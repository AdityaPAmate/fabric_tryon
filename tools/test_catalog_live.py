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
    parser.add_argument('--output', required=True)
    parser.add_argument('--draft', action='store_true')
    parser.add_argument('--material', default='unspecified')
    parser.add_argument('--face-image')
    parser.add_argument('--background')
    parser.add_argument('--reference', help='Existing front output for a focused view prompt recheck')
    parser.add_argument('--views', nargs='+', default=['three_quarter', 'collar', 'cuff', 'hem'])
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    events = []
    current_view = ['front']

    if args.reference:
        import io
        from fabricapp.catalog import catalog_plan, edit_config, generate_edit
        from fabricapp.ai.references.catalog_reference import get_catalog_reference_path
        data = {'fabric_image': io.BytesIO(Path(args.fabric).read_bytes()), 'garment_type': 'shirt',
                'fabric_type': args.material, 'options': {'draft_mode': args.draft}}
        for view, shot in catalog_plan('shirt'):
            if view not in args.views:
                continue
            template = get_catalog_reference_path('shirt', view)
            source = template if template else Path(args.reference)
            result = generate_edit(person_image=io.BytesIO(source.read_bytes()),
                                   fabric_image=data['fabric_image'], garment_type='shirt',
                                   scenario='person_photo', options=data['options'],
                                   prompt_config=edit_config(data, shot, 42, view=view, reference_template=template))
            (output / f'{view}.jpeg').write_bytes(result.image_bytes)
            image = {'view': view, **upload_generated_image(result.image_bytes)}
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
    from fabricapp.catalog import generate_catalog
    def capture(data, stopped):
        for event in generate_catalog(data, stopped):
            if event['event'] == 'generating':
                current_view[0] = event['view']
            yield event

    with override_settings(ALLOWED_HOSTS=['testserver']), patch(
        'fabricapp.catalog.upload_generated_image', side_effect=save_upload
    ), patch('fabricapp.catalog.generate_catalog', side_effect=capture):
        payload = {
            'fabric_image': SimpleUploadedFile(Path(args.fabric).name, Path(args.fabric).read_bytes()),
            'garment_type': 'shirt', 'gender': 'men', 'body_type': 'trim',
            'fabric_type': args.material,
            'seed': '42', 'options': json.dumps({'draft_mode': args.draft}),
        }
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
