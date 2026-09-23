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