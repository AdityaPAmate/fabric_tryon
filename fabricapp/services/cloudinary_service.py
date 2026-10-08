"""Upload generated try-on images to Cloudinary without changing their format."""

import io
import logging
from uuid import uuid4

import cloudinary.uploader
from PIL import Image, UnidentifiedImageError


logger = logging.getLogger("fabricapp")


class CloudinaryUploadError(Exception):
    """Raised when a generated image cannot be identified or uploaded."""


def upload_generated_image(image_bytes):
    """
    Upload Cloudflare's original output bytes to Cloudinary.

    The image is not converted. Its detected format is only used to provide a
    correct filename and to return accurate metadata to the API client.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            source_format = (image.format or "JPEG").upper()
    except (UnidentifiedImageError, OSError) as exc:
        raise CloudinaryUploadError("Generated output is not a valid image.") from exc

    extension_by_format = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "AVIF": "avif"}
    extension = extension_by_format.get(source_format, source_format.lower())
    content_type = Image.MIME.get(source_format, f"image/{extension}")

    image_stream = io.BytesIO(image_bytes)
    image_stream.name = f"generated.{extension}"

    try:
        result = cloudinary.uploader.upload(
            image_stream,
            resource_type="image",
            folder="fabric-tryon/outputs",
            public_id=uuid4().hex,
            overwrite=False,
        )
    except Exception as exc:
        logger.exception("Cloudinary upload failed")
        raise CloudinaryUploadError("Could not upload generated image.") from exc

    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "format": result.get("format", extension).lower(),
        "mime_type": content_type,
        "width": result.get("width"),
        "height": result.get("height"),
        "bytes": result.get("bytes"),
    }
