"""Map a swatch onto the panels of the packaged shirt sleeve reference."""
import io
from hashlib import sha256
from math import ceil, cos, radians, sin

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageOps


REFERENCE_SHA256 = '5428c3a4726b9806d96f78c2c8a3993385c6f8b60cd7177b868ff6a9785adbb7'
SLEEVE = [(0, 0), (375, 0), (476, 81), (565, 160), (645, 237), (744, 309),
          (685, 351), (620, 416), (550, 504), (489, 610), (436, 713),
          (394, 820), (270, 768), (126, 702), (0, 662)]
CUFF = [(744, 309), (1030, 523), (993, 554), (948, 613), (902, 684),
        (849, 780), (791, 890), (760, 947), (732, 965), (693, 970),
        (655, 963), (610, 944), (394, 820), (436, 713), (489, 610),
        (550, 504), (620, 416), (685, 351)]
BUTTONS = [(1015, 121, 1102, 205), (1025, 481, 1107, 560), (622, 690, 723, 786)]


def _panel_texture(fabric, size, angle):
    width, height = size
    turn = radians(abs(angle))
    # Size the texture for the inverse rotation so every corner has coverage.
    expanded = (ceil(width * cos(turn) + height * sin(turn)) + 4,
                ceil(width * sin(turn) + height * cos(turn)) + 4)
    tile = ImageOps.fit(fabric, expanded, Image.Resampling.LANCZOS)
    tile = tile.rotate(angle, Image.Resampling.BICUBIC)
    left, top = (tile.width - width) // 2, (tile.height - height) // 2
    return tile.crop((left, top, left + width, top + height))


def render_shirt_sleeve(reference, swatch, crop_box=None):
    reference_bytes = reference.read_bytes()
    if sha256(reference_bytes).hexdigest() != REFERENCE_SHA256:
        raise ValueError('Shirt sleeve reference changed and needs a matching fabric mask.')
    with Image.open(io.BytesIO(reference_bytes)) as source:
        base = source.convert('RGB')
    with Image.open(io.BytesIO(swatch)) as source:
        fabric = ImageOps.exif_transpose(source).convert('RGB')
    if crop_box:
        fabric = fabric.crop(crop_box)

    texture = _panel_texture(fabric, base.size, 0)
    for outline, angle in ((SLEEVE, -35), (CUFF, 29)):
        panel = Image.new('L', base.size)
        ImageDraw.Draw(panel).polygon(outline, fill=255)
        texture.paste(_panel_texture(fabric, base.size, angle), (0, 0), panel)

    # In this fixed reference the exposed wrist is warm and the cloth is neutral.
    red, _, blue = base.split()
    fabric_mask = ImageChops.subtract(red, blue).point(
        lambda difference: max(0, min(255, (24 - difference) * 16))
    )
    draw = ImageDraw.Draw(fabric_mask)
    for button in BUTTONS:
        draw.ellipse(button, fill=0)

    # Multiply by neutral shading to retain folds without boosting saturation.
    # Keep fabric-only lighting subtle around the reference midtone.
    shade = base.convert('L').point(
        lambda value: round(255 * max(0.88, min(1.03, 1 + (value - 222) / 500)) / 1.03)
    )
    shaded_texture = ImageChops.multiply(texture, Image.merge('RGB', (shade, shade, shade)))
    shaded_texture = ImageEnhance.Brightness(shaded_texture).enhance(1.03)
    output = io.BytesIO()
    Image.composite(shaded_texture, base, fabric_mask).save(output, format='PNG')
    return output.getvalue()
