"""Derive the detail panel from the actual approved front, never a new pose."""
import io

from PIL import Image

from fabricapp.ai.garments.saree.catalog.layout import PANELS


def crop_config(data, shot, seed):
    left, top, right, bottom = PANELS[shot.key]
    return {'seed':seed,'output_dimensions': (right-left, bottom-top)}


def resolve_front_crop(data, shot, source):
    """Reference-framing ROI, independent of fabric colour or printed design.

    The full-length front has consistent headroom. Start around the lower waist and
    retain the complete lower hem. Match the panel aspect here, so the shared
    renderer does not subsequently cut off more cloth or add padding.
    """
    with Image.open(io.BytesIO(source)) as image:
        width, height = image.size
    left, top, right, bottom = PANELS[shot.key]
    aspect = (right-left)/(bottom-top)
    crop_bottom = .94*height
    crop_height = .44*height
    crop_width = aspect*crop_height
    if crop_width > .96*width:
        crop_width = .96*width
        crop_height = crop_width/aspect
    crop_left = min(max(.53*width-crop_width/2, 0), width-crop_width)
    crop_top = max(0,crop_bottom-crop_height)
    return (crop_left/width,crop_top/height,
            (crop_left+crop_width)/width,crop_bottom/height)
