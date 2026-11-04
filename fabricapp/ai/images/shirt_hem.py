"""Apply a swatch to the fabric area traced on the packaged hem photograph."""
import io
from hashlib import sha256

from PIL import Image, ImageChops, ImageDraw, ImageOps


# The trace belongs to this exact reference. A replacement photo needs its own trace.
REFERENCE_SHA256 = '46f13a1d0a61bc09b32db025c481d239ec516cb206c2dd8f6a6407dd5a88c2c2'
FABRIC_OUTLINE = [
    (127, 0), (1672, 0), (1672, 714), (1620, 724), (1530, 740),
    (1450, 748), (1320, 759), (1315, 741), (1210, 741), (1100, 737),
    (1000, 727), (900, 724), (800, 708), (700, 686), (600, 660),
    (500, 624), (400, 579), (320, 532), (240, 481), (175, 433),
    (127, 390), (97, 362), (109, 286), (110, 193), (117, 101),
]


def render_shirt_hem(reference, swatch, crop_box=None):
    reference_bytes = reference.read_bytes()
    if sha256(reference_bytes).hexdigest() != REFERENCE_SHA256:
        raise ValueError('Shirt hem reference changed and needs a matching fabric mask.')
    with Image.open(io.BytesIO(reference_bytes)) as source:
        base = source.convert('RGB')
    with Image.open(io.BytesIO(swatch)) as source:
        fabric = ImageOps.exif_transpose(source).convert('RGB')
    if crop_box:
        fabric = fabric.crop(crop_box)
    # Keep the bottom of the swatch visible so bordered prints retain their hem motif.
    texture = ImageOps.fit(fabric, base.size, Image.Resampling.LANCZOS, centering=(0.5, 1.0))
    mask = Image.new('L', base.size)
    draw = ImageDraw.Draw(mask)
    draw.polygon(FABRIC_OUTLINE, fill=255)
    draw.ellipse((1314, 121, 1384, 197), fill=0)
    # Retain the reference's subtle fabric shading without shifting the swatch hue.
    shade = base.convert('L').point(lambda value: min(255, round(value * 255 / 235)))
    texture = ImageChops.multiply(texture, Image.merge('RGB', (shade, shade, shade)))
    result = Image.composite(texture, base, mask)
    output = io.BytesIO()
    result.save(output, format='PNG')
    return output.getvalue()
