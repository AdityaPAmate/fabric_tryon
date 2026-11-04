"""Deterministic portrait catalog composition; no additional model request."""
import io
from PIL import Image, ImageOps, ImageDraw, ImageFont

LAYOUT = 'portrait-catalog-v1'
SIZE = (1800, 3200)

def compose_catalog(shots, swatch, views):
    """Return PNG bytes. Require all six views; never silently omit a panel."""
    if len(views) != 6 or any(view not in shots for view in views):
        raise ValueError('All six catalog views are required')
    canvas = Image.new('RGB', SIZE, 'white')
    boxes = [(0, 0, 760, 2520), (772, 0, 1280, 894),
             (1292, 0, 1800, 894), (772, 906, 1800, 1572),
             (772, 1584, 1800, 2052), (772, 2064, 1800, 2520)]
    def place(payload, box, crop=True):
        with Image.open(io.BytesIO(payload)) as source:
            source = ImageOps.exif_transpose(source).convert('RGB')
            width, height = box[2]-box[0], box[3]-box[1]
            # Fill each fixed panel without stretching; crop excess background centrally.
            tile = (ImageOps.fit(source, (width, height)) if crop else
                    ImageOps.pad(source, (width, height), color='white'))
            canvas.paste(tile, box[:2])
    for view, box in zip(views, boxes):
        place(shots[view], box)
    place(swatch, (36, 2544, 1764, 3072), crop=True)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=40)
    draw.text((900, 3132), 'FABRIC SWATCH', fill='black', font=font, anchor='mm')
    output = io.BytesIO()
    canvas.save(output, 'PNG')
    return output.getvalue()
