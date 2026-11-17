"""Match portrait cloth midtones to the same source used in the close-ups."""
from dataclasses import replace
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import binary_propagation

from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours


# Allow for some variation in the generated silhouette. Samples avoid the shirt and hands.
PORTRAIT_REGIONS = {
    'front': ((.27, .27, .40, .36), (
        (.04, .23), (.31, .19), (.41, .22), (.41, .35), (.60, .35),
        (.60, .21), (.71, .20), (.96, .25), (.96, .41), (.85, .45),
        (.83, .52), (.60, .54), (.60, .46), (.38, .46), (.37, .54),
        (.16, .53), (.15, .45), (.04, .41),
    )),
    'side': ((.58, .30, .73, .40), (
        (.37, .28), (.49, .18), (.65, .17), (.79, .22), (.82, .37),
        (.79, .50), (.66, .52), (.55, .49), (.47, .50), (.39, .45),
    )),
    'back': ((.34, .27, .65, .39), (
        (.13, .25), (.31, .17), (.56, .16), (.77, .20), (.87, .25),
        (.92, .48), (.77, .49), (.73, .50), (.27, .50), (.23, .49), (.10, .48),
    )),
}
LUMA = np.array([.299, .587, .114], dtype=np.float32)


def _chroma(rgb):
    return rgb - (rgb @ LUMA)[..., None]


def jacket_midtone(data):
    crop = data.get('options', {}).get('fabric_crop_box')
    profile = measure_fabric_colours(data['fabric_image'], crop, palette_size=24, min_coverage=.005)
    return profile_midtone(profile)


def profile_midtone(profile):
    colours = profile['colours']
    pixels = np.asarray([colour['rgb'] for colour in colours], dtype=np.float32)
    weights = np.asarray([colour['coverage'] for colour in colours])
    family = (np.linalg.norm(_chroma(pixels) - _chroma(pixels[0]), axis=1) <= 24)
    family &= np.abs((pixels - pixels[0]) @ LUMA) <= 48
    if weights[family].sum() >= .54:
        return np.average(pixels[family], axis=0, weights=weights[family])
    return None


def align_portrait_colour(generation, view, target):
    if target is None:
        return generation
    with Image.open(BytesIO(generation.image_bytes)) as source:
        image = source.convert('RGB')
    pixels = np.asarray(image, dtype=np.float32)
    box, polygon = PORTRAIT_REGIONS[view]
    width, height = image.size
    x0, y0, x1, y1 = (round(value * extent) for value, extent in zip(box, (width, height) * 2))
    area = Image.new('1', image.size)
    ImageDraw.Draw(area).polygon([(round(x * width), round(y * height)) for x, y in polygon], fill=1)
    eligible = (np.linalg.norm(_chroma(pixels) - _chroma(target), axis=2) <= 32)
    eligible &= (np.abs((pixels - target) @ LUMA) <= 64) & np.asarray(area)
    sample_selection = eligible[y0:y1, x0:x1]
    if sample_selection.mean() < .55:
        return generation
    measured = np.median(pixels[y0:y1, x0:x1][sample_selection], axis=0)
    shift = np.clip(target - measured, -36, 36)
    if np.max(np.abs(shift)) < 4:
        return generation

    # Correct connected cloth of the measured shade. Preserve folds and other print hues.
    matching = eligible & (np.linalg.norm(_chroma(pixels) - _chroma(measured), axis=2) <= 21)
    seeds = np.zeros_like(matching)
    seeds[y0:y1, x0:x1] = matching[y0:y1, x0:x1]
    connected = binary_propagation(seeds, mask=matching)
    matte = Image.fromarray(connected.astype(np.uint8) * 255).filter(ImageFilter.GaussianBlur(1))
    corrected = Image.fromarray(np.rint(np.clip(pixels + shift, 0, 255)).astype(np.uint8))
    result = BytesIO()
    Image.composite(corrected, image, matte).save(result, 'PNG')
    return replace(generation, image_bytes=result.getvalue(), diagnostics={
        **(generation.diagnostics or {}),
        'blazer_cloth_midtone_rgb': np.rint(target).astype(int).tolist(),
        'blazer_cloth_rgb_shift': np.rint(shift).astype(int).tolist(),
    })
