"""Saree-only original full-product and side-border photos; no generative calls."""
import hashlib
import io
import os

import numpy as np
from PIL import Image

from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.ai.garments.saree.catalog.layout import PANELS
from fabricapp.ai.garments.saree.catalog.regions import source_regions
from fabricapp.ai.garments.saree.catalog.border_extraction import extract_band, render_band


def _load(data):
    stream = data.get('fabric_image')
    if stream is None:
        raise ValueError('Saree product details require the original fabric photograph.')
    position = stream.tell()
    try:
        stream.seek(0)
        raw = stream.read()
        with Image.open(io.BytesIO(raw)) as image:
            # Crop coordinates are defined in original upload pixels.
            return image.convert('RGB'), hashlib.sha256(raw).hexdigest()
    finally:
        stream.seek(position)


def border_box(image, data, regions):
    """Prefer an explicit selection; otherwise narrow an observed side band.

    A sustained coloured band is evidence, a wide inferred body inset is not.
    Neutral/ambiguous borders need explicit selection; never invent ornament.
    """
    explicit = (data.get('options') or {}).get('fabric_border_crop_box')
    if explicit is not None:
        return list(explicit), 'explicit_crop'
    candidate = regions['border']
    if candidate is not None:
        band = image.crop(candidate)
        pixels = np.asarray(band, dtype=np.float32)
        chroma = np.ptp(pixels, axis=2)
        vertical = image.height >= image.width
        strength = (chroma > 38).mean(axis=0 if vertical else 1)
        # Sparse floral borders need not cover most rows with saturated ink.
        # Compare against actual body coverage so a printed body is not simply
        # mistaken for a border because it contains some coloured motifs.
        body_box = regions['body']
        body_pixels = np.asarray(image.crop(body_box) if body_box else image, dtype=np.float32)
        body_coverage = float((np.ptp(body_pixels, axis=2) > 38).mean())
        threshold = max(.12, min(.55, body_coverage+.08))
        active = strength > threshold
        runs, start = [], None
        for index, yes in enumerate(np.append(active, False)):
            if yes and start is None:
                start = index
            elif not yes and start is not None:
                if index-start >= 3:
                    runs.append((start, index))
                start = None
        if runs:
            first, last = min(run[0] for run in runs), max(run[1] for run in runs)
            # Retain adjoining cloth on each side for a readable real edge.
            margin = max(2, (last-first)//8)
            box = list(candidate)
            axis = 0 if vertical else 1
            box[axis] += max(0, first-margin)
            box[axis+2] = candidate[axis] + min(len(strength), last+margin)
            return box, 'detected_chromatic_side_band'
    return regions['body'] or [0, 0, image.width, image.height], 'body_only_no_confirmed_border'


def _whole_photo(image, size):
    # The fixed panel must show every source edge without padding or cropping.
    # Adapt the photo's aspect to that panel; do not synthesize textile pixels.
    return image.resize(size, Image.Resampling.LANCZOS)


def border_reference_box(data, regions):
    """Real side band plus enough neighbouring cloth for a usable image input.

    Keep explicit/selected border coordinates intact for display. The model gets
    additional genuine source context rather than a near-one-dimensional strip.
    """
    image, _ = _load(data)
    box, selection = border_box(image, data, regions)
    if selection == 'body_only_no_confirmed_border' or min(image.size) < 64:
        return None
    left, top, right, bottom = box
    width, height = right-left, bottom-top
    wanted_width = min(image.width, max(width, 128, round(height/4)))
    wanted_height = min(image.height, max(height, 128, round(width/4)))
    # Grow toward the source centre to retain body cloth beside an edge band.
    if left+right < image.width:
        right = min(image.width, left+wanted_width)
        left = max(0, right-wanted_width)
    else:
        left = max(0, right-wanted_width)
        right = min(image.width, left+wanted_width)
    if top+bottom < image.height:
        bottom = min(image.height, top+wanted_height)
        top = max(0, bottom-wanted_height)
    else:
        top = max(0, bottom-wanted_height)
        bottom = min(image.height, top+wanted_height)
    return [left, top, right, bottom]


def render_product(data, shot):
    image, digest = _load(data)
    left, top, right, bottom = PANELS[shot.key]
    size = (right-left, bottom-top)
    if (data.get('options') or {}).get('draft_mode'):
        scale = min(1, 512/max(size))
        size = tuple(max(1, round(value*scale)) for value in size)
    box, selection, extraction = None, 'full_source', {}
    if shot.key == 'fabric_texture':
        result = _whole_photo(image, size)
    elif shot.key == 'border':
        strip, extraction = extract_band(image, data.get('options') or {})
        selection = extraction['selection']
        box = extraction.get('source_crop_box')
        result = render_band(strip, size)
    else:
        raise ValueError(f'Unsupported Saree product shot: {shot.key}')
    output = io.BytesIO()
    result.save(output, 'PNG')
    diagnostics = {
        'kind': 'original_product_photo',
        'deployment_revision': os.getenv('RENDER_GIT_COMMIT') or 'unknown',
        'no_new_ai_generation': True, 'source_sha256': digest,
        'fabric_region': 'full_saree' if shot.key == 'fabric_texture' else shot.key,
        'fabric_crop_box': box, 'fabric_region_selection': selection,
        'display_crop_box': box,
        'photo_fit': 'full_source_resized_no_crop' if shot.key == 'fabric_texture' else 'side_band_diagonal_1_to_3',
        'output_dimensions': list(result.size),
    }
    if shot.key == 'border':
        diagnostics.update(border_extraction=extraction,border_only_pixels=True)
    return GenerationResult(output.getvalue(), data.get('seed',42),diagnostics)
