"""Source provenance for video only; never edits or regenerates the image."""
import hashlib
from io import BytesIO
from PIL import Image


def metadata(image_bytes):
    with Image.open(BytesIO(image_bytes)) as image:
        width, height = image.size
    return {'sha256': hashlib.sha256(image_bytes).hexdigest(), 'width': width, 'height': height}
