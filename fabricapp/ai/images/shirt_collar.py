"""Apply the swatch to the traced fabric of the packaged collar photograph."""
import io
from hashlib import sha256

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


REFERENCE_SHA256 = '5721478cd3cf16600278a81f35b945860dd1e419cbdf874bb9a3b72d4bea70bb'
FABRIC_OUTLINE = [
    (0, 461), (187, 371), (255, 208), (270, 181), (293, 162), (329, 149),
    (331, 255), (313, 283), (331, 329), (364, 393), (401, 461),
    (432, 501), (471, 511), (518, 523), (553, 544), (580, 572),
    (600, 601), (617, 640), (669, 692), (700, 731), (714, 755),
    (736, 728), (780, 686), (793, 663), (798, 636), (796, 613),
    (805, 594), (837, 567), (880, 543), (930, 527), (961, 467),
    (997, 395), (1024, 332), (1039, 287), (1017, 264), (1011, 147),
    (1039, 160), (1064, 182), (1082, 215), (1100, 264), (1161, 376),
    (1387, 489), (1387, 1134), (0, 1134),
]


def render_shirt_collar(reference, swatch, crop_box=None):
    reference_bytes = reference.read_bytes()
    if sha256(reference_bytes).hexdigest() != REFERENCE_SHA256:
        raise ValueError('Shirt collar reference changed and needs a matching fabric mask.')
    with Image.open(io.BytesIO(reference_bytes)) as source:
        base = source.convert('RGB')
    with Image.open(io.BytesIO(swatch)) as source:
        fabric = ImageOps.exif_transpose(source).convert('RGB')
    if crop_box:
        fabric = fabric.crop(crop_box)

    mask = Image.new('L', base.size)
    draw = ImageDraw.Draw(mask)
    draw.polygon(FABRIC_OUTLINE, fill=255)
    # Recover narrow blue cloth edges between the traced points.
    red, _, blue = base.split()
    blue_cloth = ImageChops.subtract(blue, red).point(lambda value: 255 if value >= 20 else 0)
    mask = ImageChops.lighter(mask, ImageChops.multiply(mask.filter(ImageFilter.MaxFilter(21)), blue_cloth))
    draw = ImageDraw.Draw(mask)
    # The top button is tilted, so trace its rim instead of cutting out a box.
    draw.polygon([(454, 558), (460, 549), (473, 544), (487, 544),
                  (500, 550), (509, 561), (513, 575), (509, 588),
                  (499, 596), (485, 597), (471, 591), (460, 582),
                  (454, 571)], fill=0)
    draw.ellipse((679, 857, 738, 921), fill=0)
    texture = ImageOps.fit(fabric, base.size, Image.Resampling.LANCZOS)
    shade = base.convert('L').point(lambda value: min(255, round(value * 255 / 210)))
    texture = ImageChops.multiply(texture, Image.merge('RGB', (shade, shade, shade)))
    output = io.BytesIO()
    Image.composite(texture, base, mask).save(output, format='PNG')
    return output.getvalue()
