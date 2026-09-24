"""
Stage: Core engine that talks to Cloudflare Workers AI.
Flow: pick prompt -> resize images -> compute output size -> call
Cloudflare (with retry) -> parse response -> return image bytes.
This module knows nothing about Django views/HTTP — that stays in
views.py. Retry/backoff/parsing logic is unchanged from the tested
scripts, only restructured and logged in English.
"""

import base64
import gc
import logging
import time

import requests
from django.conf import settings

from .prompts import get_prompt_config
from .image_utils import resize_to_fit, get_output_dimensions
from .debug_utils import save_debug_copy, save_output_copy

logger = logging.getLogger("fabricapp")

MAX_INPUT_DIM = 511            # Cloudflare requires input images under 512x512
MAX_ATTEMPTS = 2               # retry once on a transient server error
REQUEST_TIMEOUT_SECONDS = 180


class CloudflareGenerationError(Exception):
    """Raised when Cloudflare fails to generate an image after retries."""
    pass


def generate_tryon_image(person_image, fabric_image, garment_type, garment_style=None, options=None):
    """
    Main entry point for the pipeline.
    person_image / fabric_image: Django uploaded file objects.
    garment_type: must be a key in prompts.GARMENT_PROMPTS.
    garment_style: required only for garment_types that have subtypes
                   (see prompts.GARMENT_STYLE_OPTIONS, e.g. "blazer").
                   None for garment_types that don't use styles.
    options: optional dict, currently supports "draft_mode" (bool)
             and "fabric_crop_box" (tuple), both optional.
    Returns: generated image as raw bytes.
    """
    options = options or {}

    garment_config = get_prompt_config(garment_type, garment_style)
    if garment_config is None:
        logger.error(
            "No prompt config found for garment_type=%s garment_style=%s",
            garment_type, garment_style,
        )
        raise CloudflareGenerationError(
            f"No prompt configuration for garment_type='{garment_type}' "
            f"garment_style='{garment_style}'"
        )

    draft_mode = options.get("draft_mode", True)
    max_output_side = 512 if draft_mode else 1024

    # Stage 1: resize both images to fit Cloudflare's input size limit
    logger.info(
        "Stage 1: resizing images for garment_type=%s garment_style=%s",
        garment_type, garment_style,
    )
    person_buffer = resize_to_fit(person_image, max_dim=MAX_INPUT_DIM)
    fabric_buffer = resize_to_fit(
        fabric_image, max_dim=MAX_INPUT_DIM, crop_box=options.get("fabric_crop_box")
    )
    save_debug_copy(person_buffer, f"sent_person_{garment_type}.jpg")
    save_debug_copy(fabric_buffer, f"sent_fabric_{garment_type}.jpg")

    # Stage 2: compute output dimensions from the person photo's aspect ratio
    logger.info("Stage 2: computing output size (draft_mode=%s)", draft_mode)
    out_w, out_h = get_output_dimensions(person_image, max_side=max_output_side)

    # Stage 3: send the request to Cloudflare, retrying on transient errors
    logger.info(
        "Stage 3: calling Cloudflare model=%s size=%sx%s",
        settings.CLOUDFLARE_MODEL, out_w, out_h,
    )
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.CLOUDFLARE_ACCOUNT_ID}/ai/run/{settings.CLOUDFLARE_MODEL}"
    )
    headers = {"Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}"}
    files = {
        "input_image_0": ("person.jpg", person_buffer, "image/jpeg"),
        "input_image_1": ("fabric.jpg", fabric_buffer, "image/jpeg"),
    }
    data = {
        "prompt": garment_config["prompt"],
        "width": out_w,
        "height": out_h,
        "guidance": garment_config["guidance"],
        "seed": garment_config["seed"],
    }

    response = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info("Sending request to Cloudflare (attempt %s/%s)", attempt, MAX_ATTEMPTS)
        response = requests.post(
            url, headers=headers, files=files, data=data, timeout=REQUEST_TIMEOUT_SECONDS
        )

        if response.status_code == 200:
            break

        internal_code = None
        try:
            internal_code = response.json().get("errors", [{}])[0].get("code")
        except Exception:
            pass

        if response.status_code in (500, 429) and attempt < MAX_ATTEMPTS:
            wait_seconds = 2 ** attempt
            logger.warning(
                "Cloudflare returned status %s (code %s). Retrying in %s seconds.",
                response.status_code, internal_code, wait_seconds,
            )
            time.sleep(wait_seconds)
            continue

        logger.error(
            "Cloudflare request failed. status=%s code=%s body=%s",
            response.status_code, internal_code, response.text[:500],
        )
        raise CloudflareGenerationError(
            f"Cloudflare request failed with status {response.status_code}"
        )

    # Stage 4: parse the response into raw image bytes
    logger.info("Stage 4: parsing Cloudflare response")
    content_type = response.headers.get("Content-Type", "")

    if "application/json" in content_type:
        result = response.json()
        image_b64 = result.get("result", {}).get("image", "")
        if not image_b64:
            logger.error("No image field found in Cloudflare response: %s", result)
            raise CloudflareGenerationError("Cloudflare response did not contain an image")
        image_bytes = base64.b64decode(image_b64)

    elif "image" in content_type:
        image_bytes = response.content

    else:
        logger.error("Unexpected content type from Cloudflare: %s", content_type)
        raise CloudflareGenerationError(f"Unexpected response content type: {content_type}")

    save_output_copy(image_bytes, f"output_{garment_type}.png")

    # Stage 5: free memory used by this request's image buffers
    del person_buffer, fabric_buffer, response
    gc.collect()
    logger.info("Stage 5: request finished, memory released")

    return image_bytes