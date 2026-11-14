"""Match solid Pathani fabric under diffuse light in each reference framing."""
import io
from dataclasses import replace

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter, label


# Central cloth sample, then the bounds where cloth correction is safe.
# The front and side hands divide the upper and lower cloth regions.
REGIONS = {
    'front': (((.37, .26, .65, .35), (0, .18, 1, .43)),
              ((.35, .53, .65, .61), (.06, .46, .94, .68))),
    'side': (((.56, .25, .72, .32), (.28, .18, .97, .39)),
             ((.42, .50, .64, .57), (.13, .43, .94, .68))),
    'back': (((.37, .32, .63, .47), (0, .15, 1, .70)),),
    'collar': (((.12, .46, .35, .65), (0, .16, 1, 1)),),
    'cuff': (((.48, .37, .63, .51), (0, 0, 1, 1)),),
    'pocket': (((.30, .18, .62, .29), (0, 0, 1, .91)),),
}
LUMA = np.array([.2126, .7152, .0722], dtype=np.float32)


def match_cloth_exposure(generation, view, target):
    if target is None or view not in REGIONS:
        return generation
    with Image.open(io.BytesIO(generation.image_bytes)) as source:
        image = source.convert('RGB')
    pixels = np.asarray(image, dtype=np.float32)
    hsv = np.asarray(image.convert('HSV'), dtype=np.float32)
    light = pixels @ LUMA
    source_light = float(target @ LUMA)
    correction = pixels.copy()
    matte = np.zeros(light.shape, dtype=np.float32)
    width, height = image.size

    def bounds(box):
        return tuple(round(value * extent) for value, extent in zip(box, (width, height, width, height)))

    for sample, region in REGIONS[view]:
        sx, sy, ex, ey = bounds(sample)
        observed = np.median(pixels[sy:ey, sx:ex], axis=(0, 1))
        hue, saturation, _ = Image.new('RGB', (1, 1), tuple(np.rint(observed).astype(int))).convert('HSV').getpixel((0, 0))
        left, top, right, bottom = bounds(region)
        window = np.s_[top:bottom, left:right]
        tone = light[window]
        measured = max(1, float(observed @ LUMA))
        if abs(measured - source_light) > 105:
            continue
        patch_hue, patch_sat, _ = np.moveaxis(hsv[window], -1, 0)
        delta = np.abs(patch_hue - hue)
        hue_gap = np.minimum(delta, 256 - delta)
        if saturation < 24:
            # Achromatic cloth has no reliable hue. Combine chroma and tone.
            candidate = (patch_sat < 32) & (np.abs(tone - measured) < 38)
        else:
            candidate = (hue_gap < 27) & (patch_sat > max(22, saturation * .36))
            candidate &= (tone > measured * .38) & (tone < measured * 2 + 24)
            # Bright skin can share a brown cloth hue. Require a closer
            # chroma match as lightness approaches the top of the range.
            candidate &= (tone < measured * 1.5 + 12) | (patch_sat >= saturation * .76)
        if view == 'collar':
            # The central opening contains the chin and neck down to the
            # start of the placket. Preserve it even when skin matches hue.
            x = np.arange(left, right) / width
            y = np.arange(top, bottom)[:, None] / height
            candidate &= np.abs(x - .50) > np.clip(.25 - .52 * y, 0, .25)

        components, _ = label(candidate)
        sample_ids = components[sy-top:ey-top, sx-left:ex-left]
        present = sample_ids[sample_ids > 0]
        if present.size < sample_ids.size * .45:
            continue
        cloth = components == np.bincount(present).argmax()
        if cloth[sy-top:ey-top, sx-left:ex-left].mean() < .4:
            continue
        if view == 'collar':
            # The placket can separate the two chest panels in the colour mask.
            opposite = components[sy-top:ey-top, width-ex-left:width-sx-left]
            opposite_ids = opposite[opposite > 0]
            if opposite_ids.size >= opposite.size * .45:
                cloth |= components == np.bincount(opposite_ids).argmax()

        # Compress broad lighting variations while retaining a fraction of the
        # original thread, fold and stitched edge contrast.
        sigma = max(2, min(image.size) / 38)
        local = gaussian_filter(tone * cloth, sigma) / np.maximum(gaussian_filter(cloth.astype(np.float32), sigma), .001)
        shade = np.clip((local - measured) * .13 + (tone - local) * .58, -36, 36)
        correction[window] = target + shade[:, :, None]
        # Taper at interior crop edges, including the hand exclusion band.
        pad = max(2, min(image.size) * .12)
        x, y = np.arange(left, right), np.arange(top, bottom)
        fade = np.ones(cloth.shape, dtype=np.float32)
        for distance, interior in ((x - left, left > 0), (right - 1 - x, right < width),
                                   ((y - top)[:, None], top > 0), ((bottom - 1 - y)[:, None], bottom < height)):
            if interior:
                fade *= np.clip(distance / pad, 0, 1)
        matte[window] = cloth * fade

    if not matte.any():
        return generation
    # Fade across sampling bounds instead of creating a visible exposure step.
    mask = Image.fromarray(np.uint8(matte * 255)).filter(ImageFilter.GaussianBlur(max(2, width / 45)))
    mask_pixels = np.asarray(mask) * (matte > 0)
    out = io.BytesIO()
    matched = Image.fromarray(np.uint8(np.clip(correction, 0, 255)))
    Image.composite(matched, image, Image.fromarray(np.uint8(mask_pixels))).save(out, 'PNG')
    return replace(generation, image_bytes=out.getvalue(), diagnostics={
        **(generation.diagnostics or {}), 'pathani_swatch_rgb': np.rint(target).astype(int).tolist(),
    })
