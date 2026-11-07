"""Render a catalog locally without generating images or uploading anything."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.validation import validate_definition
from fabricapp.catalog_engine.renderer import render_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--garment', default='saree')
    parser.add_argument('--edition')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--references', action='store_true', help='Layout proof using bundled references, not generated results')
    source.add_argument('--shots-dir', type=Path, help='Directory containing shot-key.png files from a completed catalog')
    parser.add_argument('--product-json', type=Path, help='JSON object with product/header text')
    parser.add_argument('--swatch', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    definition = get_definition(args.garment, args.edition)
    product = json.loads(args.product_json.read_text(encoding='utf-8')) if args.product_json else {}
    layout = validate_definition(definition, product)
    shots = {}
    for shot in definition.shots:
        path = shot.reference if args.references else args.shots_dir / (shot.key + '.png')
        if path is None:
            parser.error(f'{shot.key} has no template; use --shots-dir for this edition')
        shots[shot.key] = path.read_bytes()
    if layout.swatch_box and not args.swatch:
        parser.error('--swatch is required for this layout')
    payload = render_catalog(shots, args.swatch.read_bytes() if args.swatch else b'', layout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(('REFERENCE-ONLY layout proof: ' if args.references else 'Recomposed catalog: ') + str(args.output.resolve()))


if __name__ == '__main__':
    main()
