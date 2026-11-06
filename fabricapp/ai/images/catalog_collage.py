"""Deterministic portrait catalog composition; no additional model request."""
import io
from PIL import Image, ImageOps, ImageDraw, ImageFont

LAYOUT = 'portrait-catalog-v3'
SIZE = (1800, 3200)
SHIRT_SIZE = (1368, 2432)
SHIRT_FRONT_SIZE = (576, 1920)


def catalog_layout(views):
    return LAYOUT if 'close_up' in views else 'portrait-catalog-v2'

def compose_catalog(shots, swatch, views):
    """Return PNG bytes. Require all six views; never silently omit a panel."""
    if len(views) != 6 or any(view not in shots for view in views):
        raise ValueError('All six catalog views are required')
    shirt = 'close_up' in views
    canvas = Image.new('RGB', SHIRT_SIZE if shirt else SIZE, 'white')
    boxes = [(0, 0, 760, 2520), (772, 0, 1280, 894),
             (1292, 0, 1800, 894), (772, 906, 1800, 1572),
             (772, 1584, 1800, 2052), (772, 2064, 1800, 2520)]
    if shirt:
        # The front photograph is generated at exactly this panel size.
        # Do not enlarge a 1536px image to fill the former 2520px panel.
        boxes = [(0, 0, 576, 1920), (584, 0, 972, 680),
                 (980, 0, 1368, 680), (584, 688, 1368, 1192),
                 (584, 1200, 1368, 1552), (584, 1560, 1368, 1920)]
    def place(payload, box, crop=True):
        with Image.open(io.BytesIO(payload)) as source:
            source = ImageOps.exif_transpose(source).convert('RGB')
            width, height = box[2]-box[0], box[3]-box[1]
            # Fill each fixed panel without stretching; crop excess background centrally.
            tile = (ImageOps.fit(source, (width, height)) if crop else
                    ImageOps.pad(source, (width, height), color='white'))
            canvas.paste(tile, box[:2])
    for view, box in zip(views, boxes):
        preserve = ('front', 'close_up', 'back', 'cuff', 'sleeve', 'hem') if shirt else ('close_up', 'cuff', 'sleeve', 'hem')
        place(shots[view], box, crop=view not in preserve)
    place(swatch, (28, 1936, 1340, 2336) if shirt else (36, 2544, 1764, 3072), crop=True)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=30 if shirt else 40)
    draw.text((684, 2384) if shirt else (900, 3132), 'FABRIC SWATCH', fill='black', font=font, anchor='mm')
    output = io.BytesIO()
    canvas.save(output, 'PNG')
    return output.getvalue()
