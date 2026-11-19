"""Measure the plain Pathani trouser dye from the source cloth."""
import colorsys
import io

import numpy as np
from PIL import Image

from fabricapp.ai.fabric.body_region import select_body_fabric_region
from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours
from fabricapp.ai.fabric.solid_swatch import solid_swatch_rgb


def trouser_colour(data):
    source = data.get('fabric_image')
    if source is not None:
        crop, _ = select_body_fabric_region(data)
    else:
        source = data['garment_image']
        position = source.tell()
        try:
            source.seek(0)
            with Image.open(source) as image:
                crop = (round(image.width * .34), round(image.height * .53),
                        round(image.width * .66), round(image.height * .82))
        finally:
            source.seek(position)
    profile = measure_fabric_colours(source, crop, palette_size=8, min_coverage=.01)
    solid = solid_swatch_rgb(profile)
    if solid is not None:
        return solid
    colours = profile['colours']
    if not colours:
        return None
    # Combine nearby shades of the most-covered colour without averaging
    # contrasting printed motifs into the trouser dye.
    base = np.asarray(colours[0]['rgb'], dtype=np.float32)
    family = [colour for colour in colours if np.linalg.norm(np.asarray(colour['rgb']) - base) <= 40]
    return np.average([colour['rgb'] for colour in family], axis=0,
                      weights=[colour['coverage'] for colour in family])


def trousers_match(image_bytes, target):
    """Check coloured trouser midtones before accepting a full-length shot."""
    if target is None or np.ptp(target) < 20:
        return True
    with Image.open(io.BytesIO(image_bytes)) as source:
        image = source.convert('RGB')
    box = tuple(round(value * side) for value, side in zip((.28, .81, .72, .89), image.size * 2))
    sample = image.crop(box)
    hsv = np.asarray(sample.convert('HSV'), dtype=np.float32)
    hue = colorsys.rgb_to_hsv(*(target / 255))[0] * 255
    delta = np.abs(hsv[:, :, 0] - hue)
    cloth = (np.minimum(delta, 256 - delta) < 28) & (hsv[:, :, 1] > 10)
    if cloth.mean() < .25:
        return False
    measured = np.median(np.asarray(sample, dtype=np.float32)[cloth], axis=0)
    return bool(np.max(np.abs(measured - target)) <= 45)
