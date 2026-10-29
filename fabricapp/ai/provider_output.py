"""Validate image transport integrity, not garment appearance or pose quality."""

import io

from PIL import Image


def validate_generated_image(image_bytes, expected_size):
    """Reject corrupt or incorrectly sized provider output before uploading it."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.size != expected_size:
            raise ValueError("Provider image dimensions differ from the requested size")
        image.verify()
