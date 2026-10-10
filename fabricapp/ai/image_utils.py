"""
Stage: Image preparation helpers.
Resizes uploaded images to fit Cloudflare's size limit, and works out
output dimensions from the person photo's aspect ratio. Same logic as
the original tested scripts, just adapted to work with Django's
in-memory uploaded files instead of file paths on disk.
"""

import io
from PIL import Image


def resize_to_fit(image_file, max_dim, crop_box=None):
    """
    Resize an uploaded image to fit inside max_dim x max_dim (keeping
    aspect ratio), and return it as an in-memory JPEG buffer.
    Uses LANCZOS resampling for sharper results on fine repeating
    patterns like checks/stripes (same choice as the tested scripts).
    """
    image_file.seek(0)
    img = Image.open(image_file).convert("RGB")
    if crop_box is not None:
        img = img.crop(crop_box)
    img.thumbnail((max_dim, max_dim), resample=Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    buffer.seek(0)
    return buffer


def find_main_fabric_pattern_crop(image_file):
    """Return a full-width crop around a fabric's repeated main pattern.

    Some catalog fabric photos contain a large decorative scene or a wide
    border below an otherwise repeating textile pattern.  When used for an
    upper-body garment, image models often treat that scene as wall art.  This
    function finds a broad horizontal region with the dominant fabric ground
    colour and excludes a visually different border/artwork region.

    A crop is returned only when the distinction is clear.  Uniform, striped,
    checked, and all-over printed fabrics continue to use the full image.
    """
    image_file.seek(0)
    with Image.open(image_file) as source:
        image = source.convert("RGB")

    width, height = image.size
    if width < 64 or height < 128:
        return None

    sample = image.copy()
    sample.thumbnail((192, 320), resample=Image.LANCZOS)
    sample_width, sample_height = sample.size
    if sample_height < 32:
        return None

    # Eight palette colours are enough to identify a fabric's broad ground
    # colour while keeping small repeated motifs out of the background bucket.
    indexed = sample.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    colors = indexed.getcolors(sample_width * sample_height) or []
    if not colors:
        return None
    dominant_index = max(colors, key=lambda item: item[0])[1]

    pixels = indexed.load()
    row_scores = [
        sum(pixels[x, y] == dominant_index for x in range(sample_width))
        / sample_width
        for y in range(sample_height)
    ]

    # Smooth small motif rows so that a repeating print remains one region.
    radius = max(2, sample_height // 50)
    smoothed = []
    for index in range(sample_height):
        start = max(0, index - radius)
        end = min(sample_height, index + radius + 1)
        smoothed.append(sum(row_scores[start:end]) / (end - start))

    overall = sum(smoothed) / len(smoothed)
    threshold = min(0.92, overall + 0.10)
    best_start = best_end = 0
    best_quality = 0.0
    start = None
    for index, score in enumerate(smoothed + [0.0]):
        if score >= threshold and start is None:
            start = index
        elif score < threshold and start is not None:
            end = index
            length = end - start
            quality = length * (sum(smoothed[start:end]) / length)
            if quality > best_quality:
                best_start, best_end, best_quality = start, end, quality
            start = None

    minimum_height = max(24, int(sample_height * 0.30))
    if best_end - best_start < minimum_height:
        return None

    selected = smoothed[best_start:best_end]
    selected_mean = sum(selected) / len(selected)
    outside = smoothed[:best_start] + smoothed[best_end:]
    outside_mean = sum(outside) / len(outside) if outside else overall
    # Do not crop when the fabric is visually uniform from top to bottom.
    if selected_mean - outside_mean < 0.12:
        return None

    top = max(0, round(best_start * height / sample_height))
    bottom = min(height, round(best_end * height / sample_height))
    if bottom - top < height * 0.30:
        return None
    return (0, top, width, bottom)


def get_output_dimensions(image_file, max_side):
    """
    Work out output width/height from the person photo's original
    aspect ratio, so the model does not need to change body proportions.
    Clamped to Cloudflare's allowed range (256-1920) and rounded to the
    nearest multiple of 8.
    """
    image_file.seek(0)
    with Image.open(image_file) as img:
        orig_w, orig_h = img.size

    if orig_w >= orig_h:
        out_w = max_side
        out_h = round(max_side * orig_h / orig_w)
    else:
        out_h = max_side
        out_w = round(max_side * orig_w / orig_h)

    out_w = max(256, min(1920, (out_w // 8) * 8))
    out_h = max(256, min(1920, (out_h // 8) * 8))
    return out_w, out_h


def get_portrait_dimensions(max_side, aspect_ratio=3 / 4):
    """
    Returns fixed portrait width/height (independent of any input
    image's own aspect ratio). Used on the own-model paths, where the
    output must always be a portrait shape.
    aspect_ratio is width/height — 3/4 is a standard portrait ratio.
    Clamped to Cloudflare's allowed range (256-1920) and rounded to a
    multiple of 8.
    """
    out_h = max_side
    out_w = round(max_side * aspect_ratio)

    out_w = max(256, min(1920, (out_w // 8) * 8))
    out_h = max(256, min(1920, (out_h // 8) * 8))
    return out_w, out_h


def make_blank_canvas(width, height):
    """
    Creates a plain neutral-grey JPEG canvas in memory (no file on
    disk). Used as image_0 when no person photo and no face is given,
    so the prompt still has an image_0 to refer to.
    """
    img = Image.new("RGB", (width, height), (200, 200, 200))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    buffer.seek(0)
    return buffer
