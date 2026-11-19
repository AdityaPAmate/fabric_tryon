"""Measure the plain Pathani trouser dye from the source cloth."""
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
