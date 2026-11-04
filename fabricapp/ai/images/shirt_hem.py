"""Apply a swatch to the fabric area traced on the packaged hem photograph."""
import io
from hashlib import sha256

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageOps


# The trace belongs to this exact reference. A replacement photo needs its own trace.
REFERENCE_SHA256 = '9929effbb04f4406ac066063537b9a89d4be9db11d3d8f55c50364e66e40d90c'
FABRIC_OUTLINE = [
    (127, 0), (1672, 0), (1672, 698), (1590, 721), (1500, 748),
    (1400, 775), (1315, 796), (1307, 774), (1294, 729), (1262, 638),
    (1232, 548), (1213, 495), (1194, 550), (1161, 635), (1129, 726),
    (1101, 800), (1000, 782), (900, 765), (800, 745), (700, 720),
    (600, 691), (500, 656), (400, 612), (320, 570), (240, 518),
    (175, 466), (124, 407), (87, 368), (86, 360), (93, 332),
    (104, 229), (117, 110),
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
    draw.ellipse((1199, 138, 1275, 213), fill=0)
    # Retain the reference's subtle fabric shading without shifting the swatch hue.
    # Keep fabric-only lighting subtle around the reference midtone.
    shade = base.convert('L').point(
        lambda value: round(255 * max(0.88, min(1.03, 1 + (value - 228) / 500)) / 1.03)
    )
    texture = ImageChops.multiply(texture, Image.merge('RGB', (shade, shade, shade)))
    texture = ImageEnhance.Brightness(texture).enhance(1.03)
    result = Image.composite(texture, base, mask)
    output = io.BytesIO()
    result.save(output, format='PNG')
    return output.getvalue()
