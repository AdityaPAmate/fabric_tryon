"""Match solid Pathani fabric under diffuse light in each reference framing."""
import io
from dataclasses import replace

import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, gaussian_filter, label


# Central cloth sample, then the bounds where cloth correction is safe.
# The front and side hands divide the upper and lower cloth regions.
REGIONS = {
    'front': (((.37, .26, .65, .35), (0, .17, 1, .44)),
              ((.35, .53, .65, .61), (.06, .47, .94, .78))),
    'side': (((.52, .25, .68, .32), (.24, .16, .97, .46)),
             ((.42, .50, .60, .57), (.17, .46, .91, .78))),
    'back': (((.37, .32, .63, .47), (0, .15, 1, .73)),),
    'collar': (((.12, .46, .35, .65), (0, .16, 1, 1)),),
    'cuff': (((.48, .37, .63, .51), (0, 0, 1, 1)),),
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
    adjustment = np.zeros_like(pixels)
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
        side_chest = view == 'side' and sy / height < .4
        if saturation < 24:
            # Achromatic cloth has no reliable hue. Combine chroma and tone.
            candidate = (patch_sat < 32) & (np.abs(tone - measured) < 38)
        else:
            candidate = (hue_gap < 27) & (patch_sat > max(22, saturation * .36))
            ceiling = measured * (3 if side_chest else 2) + 24
            candidate &= (tone > measured * .38) & (tone < ceiling)
            # Bright skin can share a brown cloth hue. Require a closer
            # chroma match as lightness approaches the top of the range.
            bright_chroma = .52 if side_chest else .76
            candidate &= (tone < measured * 1.5 + 12) | (patch_sat >= saturation * bright_chroma)
        if side_chest:
            # Exclude the exposed neck and hands before including stronger
            # highlights on the shoulder and chest of the side pose.
            x = np.arange(left, right) / width
            y = np.arange(top, bottom)[:, None] / height
            neck = (y < .218) & (x < .56)
            hands = (y > .376) & (x < .33)
            candidate &= ~(neck | hands)
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

        # An isolated glare patch can fall outside the hue mask even while
        # surrounded by cloth. Recover only broad, bright interior holes.
        holes = binary_fill_holes(cloth) & ~cloth
        spread = gaussian_filter(holes.astype(np.float32), max(1, min(image.size) / 135))
        glare = holes & (spread > .65) & (tone > measured + 12)
        cloth |= glare

        # Adjust the broad light and colour cast additively. The original
        # pixel differences still carry the weave, stitching and fold detail.
        sigma = max(2, min(image.size) / 58)
        coverage = np.maximum(gaussian_filter(cloth.astype(np.float32), sigma), .001)
        local = gaussian_filter(pixels[window] * cloth[:, :, None], (sigma, sigma, 0))
        local /= coverage[:, :, None]
        strength = np.where(glare, .97, .86)
        shift = np.clip((target - local) * strength[:, :, None], -220, 85)
        # Taper near the edge of each safe sampling region.
        pad = max(2, min(image.size) * .085)
        x, y = np.arange(left, right), np.arange(top, bottom)
        fade = np.ones(cloth.shape, dtype=np.float32)
        for distance, interior in ((x - left, left > 0), (right - 1 - x, right < width),
                                   ((y - top)[:, None], top > 0), ((bottom - 1 - y)[:, None], bottom < height)):
            if interior:
                fade *= np.clip(distance / pad, 0, 1)
        adjustment[window] = shift * (cloth * fade)[:, :, None]

    if not adjustment.any():
        return generation
    # Blur the correction rather than the photograph so the cloth boundary
    # blends without smearing seams, skin or the original photograph.
    feather = max(1, min(image.size) / 100)
    adjustment = gaussian_filter(adjustment, (feather, feather, 0))
    out = io.BytesIO()
    Image.fromarray(np.rint(np.clip(pixels + adjustment, 0, 255)).astype(np.uint8)).save(out, 'PNG')
    return replace(generation, image_bytes=out.getvalue(), diagnostics={
        **(generation.diagnostics or {}), 'pathani_swatch_rgb': np.rint(target).astype(int).tolist(),
    })
