"""Correct Jodhpuri body-cloth exposure without flattening its printed motifs."""
import colorsys
import io
from dataclasses import replace

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import label


# The inner sample is inside the jacket. The outer region excludes head and trousers.
REGIONS = {
    'front': ((.37, .31, .62, .44), (.05, .20, .95, .61)),
    'side': ((.43, .32, .65, .47), (.10, .21, .92, .62)),
    'back': ((.38, .32, .62, .47), (.07, .22, .93, .64)),
    'collar': ((.15, .48, .40, .76), (0, .28, 1, 1)),
    'cuff': ((.47, .20, .73, .45), (.08, 0, 1, .91)),
}


def align_jacket_colour(generation, view, target):
    if target is None or np.ptp(target) < 20 or view not in REGIONS:
        return generation
    with Image.open(io.BytesIO(generation.image_bytes)) as source:
        image = source.convert('RGB')
    pixels = np.asarray(image, dtype=np.float32)
    hsv = np.asarray(image.convert('HSV'), dtype=np.float32)
    target_hue = colorsys.rgb_to_hsv(*(target / 255))[0] * 255
    delta = np.abs(hsv[:, :, 0] - target_hue)
    weight = np.clip((32 - np.minimum(delta, 256 - delta)) / 16, 0, 1)
    weight *= np.clip((hsv[:, :, 1] - 4) / 8, 0, 1)

    def bounds(box):
        return tuple(round(value * side) for value, side in zip(box, image.size * 2))

    sample, region = REGIONS[view]
    left, top, right, bottom = bounds(region)
    mask = np.zeros_like(weight)
    mask[top:bottom, left:right] = weight[top:bottom, left:right]
    components, _ = label(mask > .30)
    left, top, right, bottom = bounds(sample)
    centre = components[top:bottom, left:right]
    matches = centre[centre > 0]
    if matches.size < centre.size * .35:
        return generation
    cloth = components == np.bincount(matches).argmax()
    selected = cloth[top:bottom, left:right]
    if selected.sum() < centre.size * .35:
        return generation
    midtone = np.median(pixels[top:bottom, left:right][selected], axis=0)
    shift = np.clip(target - midtone, -80, 55)
    if np.max(np.abs(shift)) < 9:
        return generation
    # Add the same RGB offset to matching cloth pixels so local colour and
    # fold contrast survives. Other hues (such as flowers and gold) stay intact.
    matte = Image.fromarray(np.uint8(mask * cloth * 255)).filter(ImageFilter.GaussianBlur(1.5))
    correction = Image.fromarray(np.uint8(np.clip(pixels + shift, 0, 255)))
    output = io.BytesIO()
    Image.composite(correction, image, matte).save(output, 'PNG')
    return replace(generation, image_bytes=output.getvalue(), diagnostics={
        **(generation.diagnostics or {}), 'jodhpuri_body_midtone_rgb': np.rint(target).astype(int).tolist(),
    })
