"""Deterministic Pillow renderer shared by every garment and edition."""
import io
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"


def _font(kind, size):
    if kind == "serif":
        return ImageFont.truetype(str(FONT_DIR / "CormorantGaramond.ttf"), size)
    return ImageFont.load_default(size=size)


def render_catalog(shots, swatch, layout):
    required = {panel.shot for panel in layout.panels}
    if not required.issubset(shots):
        raise ValueError("All required catalog images must be available")
    canvas = Image.new("RGB", layout.size, layout.background)

    def place(payload, box, fit):
        with Image.open(io.BytesIO(payload)) as source:
            source = ImageOps.exif_transpose(source).convert("RGB")
            size = (box[2] - box[0], box[3] - box[1])
            tile = (ImageOps.fit(source, size, method=Image.Resampling.LANCZOS)
                    if fit == "cover" else ImageOps.pad(source, size, color=layout.background,
                                                       method=Image.Resampling.LANCZOS))
            canvas.paste(tile, box[:2])

    for panel in layout.panels:
        place(shots[panel.shot], panel.box, panel.fit)
    if layout.swatch_box:
        place(swatch, layout.swatch_box, "cover")
    draw = ImageDraw.Draw(canvas)
    for line in layout.lines:
        draw.line(line, fill="#a49b95", width=2)
    for text in layout.texts:
        if not text.value:
            continue
        size = text.size
        font = _font(text.font, size)
        while draw.textlength(text.value, font=font) > text.width and size > 12:
            size -= 1
            font = _font(text.font, size)
        value = text.value
        while value and draw.textlength(value, font=font) > text.width:
            value = value[:-1]
        draw.text(text.position, value, font=font, fill=text.fill, anchor=text.anchor)
    output = io.BytesIO()
    canvas.save(output, "PNG")
    return output.getvalue()
