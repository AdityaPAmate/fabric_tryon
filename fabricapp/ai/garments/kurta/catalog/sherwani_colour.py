"""Align solid Sherwani cloth across the generated photographs."""
import io
from dataclasses import replace

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import label

from fabricapp.ai.fabric.fabric_colour import has_single_colour_family


# Central garment areas used to measure each pose without sampling the scenery.
SAMPLE_BOXES = {
    'front': (.40, .29, .60, .46),
    'side': (.45, .34, .64, .51),
    'back': (.39, .34, .61, .52),
    'collar': (.13, .54, .39, .80),
}
COAT_BOX = (.08, .18, .94, .75)
COLLAR_BOX = (0, .25, 1, 1)


def solid_swatch_rgb(profile):
    """Recognise solid hues with shading while leaving multicolour prints alone."""
    if not has_single_colour_family(profile):
        return None
    colours = profile['colours']
    if sum(c['coverage'] for c in colours) < .85:
        return None
    return np.average([c['rgb'] for c in colours], axis=0,
                      weights=[c['coverage'] for c in colours])


def match_solid_cloth(generation, view, target):
    if target is None or view not in SAMPLE_BOXES:
        return generation
    with Image.open(io.BytesIO(generation.image_bytes)) as source:
        image = source.convert('RGB')
    pixels = np.asarray(image, dtype=np.float32)
    hsv = np.asarray(image.convert('HSV'), dtype=np.float32)
    width, height = image.size

    def bounds(box):
        return tuple(round(v * extent) for v, extent in zip(box, (width, height, width, height)))

    sx0, sy0, sx1, sy1 = bounds(SAMPLE_BOXES[view])
    sample = pixels[sy0:sy1, sx0:sx1]
    measured = np.median(sample, axis=(0, 1))
    if np.ptp(target) < 24 or np.ptp(measured) < 24:
        return generation

    def hue(rgb):
        return Image.new('RGB', (1, 1), tuple(np.rint(rgb).astype(int))).convert('HSV').getpixel((0, 0))[0]

    # A large hue mismatch is ambiguous (the crop may be scenery or skin).
    hue_gap = abs(hue(measured) - hue(target))
    if min(hue_gap, 256 - hue_gap) > 38:
        return generation
    delta = np.abs(hsv[:, :, 0] - hue(measured))
    weight = np.clip((16 - np.minimum(delta, 256 - delta)) / 7, 0, 1)
    weight *= np.clip((hsv[:, :, 1] - 42) / 26, 0, 1)
    x0, y0, x1, y1 = bounds(COLLAR_BOX if view == 'collar' else COAT_BOX)
    region = np.zeros_like(weight)
    region[y0:y1, x0:x1] = weight[y0:y1, x0:x1]
    components, _ = label(region > .25)
    labels = components[sy0:sy1, sx0:sx1].ravel()
    counts = np.bincount(labels[labels != 0])
    if not counts.size:
        return generation
    garment = components == counts.argmax()
    if np.mean(garment) < .07:
        return generation
    matte = Image.fromarray(np.uint8(region * garment * 255)).filter(ImageFilter.GaussianBlur(2))
    # Keep local lighting and folds as luminance variations around the shared midtone.
    luma = np.array([.2126, .7152, .0722])
    shade = np.clip((pixels @ luma) / max(1, measured @ luma), .55, 1.30)
    corrected = Image.fromarray(np.uint8(np.clip(target * shade[:, :, None], 0, 255)))
    output = io.BytesIO()
    Image.composite(corrected, image, matte).save(output, 'PNG')
    return replace(generation, image_bytes=output.getvalue(),
                   diagnostics={**(generation.diagnostics or {}),
                                'solid_fabric_target_rgb': np.rint(target).astype(int).tolist()})
