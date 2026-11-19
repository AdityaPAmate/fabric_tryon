"""Correct Jodhpuri body-cloth exposure without flattening its printed motifs."""
import colorsys
import io
from dataclasses import replace

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import binary_closing, binary_fill_holes, distance_transform_edt, label


# The inner sample is inside the jacket. The outer region excludes head and trousers.
REGIONS = {
    'front': ((.37, .31, .62, .44), (.05, .20, .95, .61)),
    'side': ((.43, .32, .65, .47), (.10, .21, .92, .62)),
    'back': ((.38, .32, .62, .47), (.07, .16, .93, .54)),
    'collar': ((.15, .48, .40, .76), (0, 0, 1, 1)),
    'cuff': ((.47, .20, .73, .45), (.08, 0, 1, .91)),
}


def matches_solid_jacket(generation, view, target):
    """Reject a replacement textile when a source swatch has one colour family."""
    if target is None or view not in REGIONS:
        return True
    with Image.open(io.BytesIO(generation.image_bytes)) as source:
        image = source.convert('RGB')
    box = tuple(round(value * side) for value, side in zip(REGIONS[view][0], image.size * 2))
    cloth = image.crop(box)
    pixels = np.asarray(cloth, dtype=np.float32)
    if np.ptp(target) < 20:
        chroma = pixels - pixels.mean(axis=2, keepdims=True)
        matching = np.linalg.norm(chroma - (target - target.mean()), axis=2) < 18
    else:
        hsv = np.asarray(cloth.convert('HSV'), dtype=np.float32)
        hue = colorsys.rgb_to_hsv(*(target / 255))[0] * 255
        gap = np.abs(hsv[:, :, 0] - hue)
        matching = (np.minimum(gap, 256 - gap) < 28) & (hsv[:, :, 1] > 8)
    return bool(matching.mean() >= .35)


def align_jacket_colour(generation, view, target):
    if target is None or np.ptp(target) < 20 or view not in REGIONS:
        return generation
    with Image.open(io.BytesIO(generation.image_bytes)) as source:
        image = source.convert('RGB')
    pixels = np.asarray(image, dtype=np.float32)
    hsv = np.asarray(image.convert('HSV'), dtype=np.float32)
    target_hue = colorsys.rgb_to_hsv(*(target / 255))[0] * 255
    delta = np.abs(hsv[:, :, 0] - target_hue)
    hue_gap = np.minimum(delta, 256 - delta)
    weight = np.clip((32 - hue_gap) / 16, 0, 1)
    weight *= np.clip((hsv[:, :, 1] - 4) / 8, 0, 1)

    def bounds(box):
        return tuple(round(value * side) for value, side in zip(box, image.size * 2))

    sample, region = REGIONS[view]
    left, top, right, bottom = bounds(region)
    mask = np.zeros_like(weight)
    mask[top:bottom, left:right] = weight[top:bottom, left:right]
    safe_area = np.zeros_like(weight)
    safe_area[top:bottom, left:right] = 1
    if view in ('collar', 'cuff'):
        x = np.arange(image.width) / image.width
        y = np.arange(image.height)[:, None] / image.height
        if view == 'collar':
            skin = np.abs(x - .5) < np.clip(.32 - .94 * y, 0, .32)
        else:
            skin = (x < .32) & (y > .64 + .60 * x)
        safe_area[skin] = 0
        mask[skin] = 0
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
    if np.max(np.abs(shift)) < 9 and view != 'back':
        return generation
    # Add the same RGB offset to matching cloth pixels so local colour and
    # fold contrast survives. Other hues (such as flowers and gold) stay intact.
    weights = mask * cloth
    corrected = pixels + shift
    if view == 'back':
        # Bridge small breaks in the hue mask and recover pale cloth inside the
        # jacket. Measure exposure over a neighbourhood so weave and print
        # contrast survive the correction.
        silhouette = cloth | binary_fill_holes(binary_closing(cloth, iterations=max(1, image.width // 55)))
        # Highlights on the jacket boundary can shift hue enough to break
        # connectivity. Admit nearby tinted pixels with a soft falloff.
        nearby = np.clip(1 - distance_transform_edt(~silhouette) / (image.width / 21), 0, 1)
        nearby *= np.clip((56 - hue_gap) / 20, 0, 1)
        nearby *= np.clip((hsv[:, :, 1] - 12) / 16, 0, 1)
        coverage = np.maximum(silhouette, nearby) * safe_area
        exposure = np.asarray(image.filter(ImageFilter.GaussianBlur(max(2, image.width / 100))),
                              dtype=np.float32)
        excess = exposure.max(axis=2) - max(target.max(), midtone.max())
        pale = np.clip((excess - 8) / 32, 0, 1)
        pale *= np.clip((96 - hsv[:, :, 1]) / 50, 0, 1) * coverage
        highlight_shift = target - exposure + (.38 * excess)[:, :, None]
        corrected = corrected * (1 - pale[:, :, None]) + (pixels + highlight_shift) * pale[:, :, None]
        weights = np.maximum(weights, pale)
    # Expand only inside the safe garment bounds. A soft taper avoids an RGB
    # step at the measurement rectangle, including the old collar crop line.
    padded = np.pad(safe_area, 1)
    distance = distance_transform_edt(padded)[1:-1, 1:-1]
    feather = np.clip(distance / max(2, image.width * .035), 0, 1)
    weights *= feather
    matte = Image.fromarray(np.uint8(weights * 255)).filter(ImageFilter.GaussianBlur(1.5))
    matte = Image.fromarray(np.uint8(np.asarray(matte) * safe_area))
    correction = Image.fromarray(np.uint8(np.clip(corrected, 0, 255)))
    output = io.BytesIO()
    Image.composite(correction, image, matte).save(output, 'PNG')
    return replace(generation, image_bytes=output.getvalue(), diagnostics={
        **(generation.diagnostics or {}), 'jodhpuri_body_midtone_rgb': np.rint(target).astype(int).tolist(),
    })
