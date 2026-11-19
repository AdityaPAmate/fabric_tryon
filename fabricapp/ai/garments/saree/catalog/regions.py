"""Saree-catalog source selection; explicit regions override conservative detection."""
from PIL import Image

from fabricapp.ai.fabric.body_region import select_body_fabric_region


def source_regions(data):
    options = data.get('options') or {}
    context = {**data, 'options': {**options}}
    explicit = options.get('fabric_body_crop_box', options.get('fabric_crop_box'))
    if explicit is not None:
        body, selection = explicit, 'explicit_crop'
    else:
        body, selection = select_body_fabric_region(context)
    border = options.get('fabric_border_crop_box')
    border_selection = 'explicit_crop' if border is not None else 'full_source_unresolved'
    source = data['fabric_image']
    position = source.tell()
    try:
        source.seek(0)
        with Image.open(source) as image:
            width, height = image.size
    finally:
        source.seek(position)
    # A detected body inset can expose a side band. Never infer a border from
    # the wide terminal/pallu strip; only look along the long source direction.
    if border is None and body is not None and selection == 'detected_body_crop':
        left, top, right, bottom = body
        if height >= width and left > 0:
            border = [0, top, min(width, left + max(1, (right-left)//10)), bottom]
        elif height >= width and right < width:
            border = [max(0, right-max(1, (right-left)//10)), top, width, bottom]
        elif width > height and top > 0:
            border = [left, 0, right, min(height, top+max(1, (bottom-top)//10))]
        elif width > height and bottom < height:
            border = [left, max(0, bottom-max(1, (bottom-top)//10)), right, height]
        if border is not None:
            border_selection = 'detected_side_band'
    return {'body': body, 'body_selection': selection, 'border': border,
            'border_selection': border_selection, 'size': (width, height)}
