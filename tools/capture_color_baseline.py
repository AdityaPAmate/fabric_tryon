"""Offline capture of current fabric preprocessing; never calls an AI provider.

Run from the repository root. Output contains private input images and should
stay in debug/ (gitignored). Comparisons measure preprocessing, not garment fit.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fabricapp.ai.image_utils import resize_to_fit


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stats(image):
    rgb = np.asarray(image.convert('RGB'), dtype=float)
    hsv = np.asarray(image.convert('HSV'), dtype=float)
    return {
        'mean_rgb_0_255': rgb.mean(axis=(0, 1)).round(4).tolist(),
        'mean_saturation_0_1': round(float(hsv[:, :, 1].mean() / 255), 6),
    }


def capture(source, dest, max_dim, crop_box):
    raw = source.read_bytes()
    with Image.open(io.BytesIO(raw)) as opened:
        metadata = {'size': list(opened.size), 'mode': opened.mode,
                    'icc_profile_present': bool(opened.info.get('icc_profile')),
                    'exif_orientation': opened.getexif().get(274)}
        original = opened.convert('RGB')
    prepared = resize_to_fit(io.BytesIO(raw), max_dim, crop_box).getvalue()
    sent = Image.open(io.BytesIO(prepared)).convert('RGB')
    # Same-size, lossless reference isolates JPEG encoding from spatial resize.
    reference = original.crop(crop_box) if crop_box else original.copy()
    reference.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    pixels = np.asarray(sent, dtype=float) - np.asarray(reference, dtype=float)
    folder = dest / source.stem
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, folder / ('original' + source.suffix.lower()))
    (folder / 'sent_to_model.jpg').write_bytes(prepared)
    reference.save(folder / 'resized_before_jpeg.png')
    panel = Image.new('RGB', (1000, 620), 'white')
    draw = ImageDraw.Draw(panel)
    display_size = original.copy()
    display_size.thumbnail((480, 570))
    for x, title, img in [(0, 'Original (display resized)', original),
                          (500, 'Actual prepared JPEG (current local code)', sent)]:
        preview = img.resize(display_size.size, Image.Resampling.LANCZOS)
        panel.paste(preview, (x + (500 - preview.width) // 2, 40))
        draw.text((x + 10, 10), title, fill='black')
    panel.save(folder / 'comparison.png')
    before, after = stats(original.crop(crop_box) if crop_box else original), stats(sent)
    return {
        'source_name': source.name, 'source_sha256': sha(raw),
        'prepared_sha256': sha(prepared), 'metadata': metadata,
        'prepared_size': list(sent.size), 'original': before, 'prepared': after,
        'resized_before_jpeg': stats(reference),
        'mean_rgb_shift': (np.array(after['mean_rgb_0_255']) - np.array(before['mean_rgb_0_255'])).round(4).tolist(),
        'jpeg_mean_absolute_channel_error_0_255': round(float(np.abs(pixels).mean()), 4),
        'comparison': str((folder / 'comparison.png').resolve()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fabric-dir', required=True, type=Path)
    parser.add_argument('--files', nargs='+', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--crop-box', nargs=4, type=int)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output directory to preserve the previous baseline.')
    # Read the actual engine constant without importing Django/settings/secrets.
    import ast
    tree = ast.parse((ROOT / 'fabricapp/ai/cloudflare_engine.py').read_text(encoding='utf-8'))
    max_dim = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and any(
                       isinstance(target, ast.Name) and target.id == 'MAX_INPUT_DIM'
                       for target in node.targets))
    args.output.mkdir(parents=True)
    records = [capture(args.fabric_dir / name, args.output, max_dim, args.crop_box)
               for name in args.files]
    code = {}
    snapshot = args.output / 'source_snapshot'
    for source in sorted((ROOT / 'fabricapp').rglob('*.py')):
        relative = source.relative_to(ROOT)
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        code[relative.as_posix()] = sha(source.read_bytes())
    manifest = {
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
        'processing': {'max_input_dim': max_dim, 'crop_box': args.crop_box,
                       'function': 'fabricapp.ai.image_utils.resize_to_fit'},
        'scope': 'Local preprocessing baseline; deployed version not verified.',
        'generation_baseline_status': 'Historical outputs only; exact original request settings unknown. No new AI generations performed.',
        'metric_limits': 'Whole-swatch averages can hide local changes. JPEG error uses same-size reference. Metrics do not measure generated garment colour, material, or physical colour accuracy.',
        'records': records, 'source_hashes': code,
    }
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output.resolve()), 'records': records}, indent=2))


if __name__ == '__main__':
    main()
