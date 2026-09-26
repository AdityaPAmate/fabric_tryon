"""
Stage: Core engine that talks to Cloudflare Workers AI.

Unified image-slot convention (both paths use the SAME two slots, so
every existing tested prompt's "image 0 / image 1" wording stays
literally correct on both paths):
    input_image_0 = SUBJECT — person_image if given, otherwise the
                    selected face photo (face_choice)
    input_image_1 = GARMENT SOURCE — fabric_image or garment_image

When no person_image is given, an own-model addendum sentence is
prepended to the (unmodified) garment prompt, telling the model to
extend the face in image 0 into a full body first — see
prompts.get_own_model_instruction(). No existing GARMENT_PROMPTS /
GARMENT_IMAGE_PROMPT text is ever changed.

This module knows nothing about Django views/HTTP — that stays in
views.py.
"""

import base64
import gc
import io
import logging
import time

import requests
from django.conf import settings

from .prompts import (
    get_prompt_config,
    get_camera_view_instruction,
    get_background_instruction,
    get_face_image_path,
    get_own_model_instruction,
    GARMENT_IMAGE_PROMPT,
    GARMENT_IMAGE_GUIDANCE,
    GARMENT_IMAGE_SEED,
)
from .image_utils import resize_to_fit, get_output_dimensions
from .debug_utils import save_debug_copy, save_output_copy

logger = logging.getLogger("fabricapp")

MAX_INPUT_DIM = 511
MAX_ATTEMPTS = 2
REQUEST_TIMEOUT_SECONDS = 180


class CloudflareGenerationError(Exception):
    """Raised when Cloudflare fails to generate an image after retries."""
    pass


def _load_face_buffer(face_choice):
    path = get_face_image_path(face_choice)
    if path is None:
        raise CloudflareGenerationError(f"No face image file found for '{face_choice}'")
    try:
        with open(path, "rb") as f:
            return resize_to_fit(io.BytesIO(f.read()), max_dim=MAX_INPUT_DIM)
    except FileNotFoundError:
        raise CloudflareGenerationError(f"Face image file not found on disk: {path}")


def generate_tryon_image(
    person_image=None,
    fabric_image=None,
    garment_image=None,
    garment_type=None,
    garment_style=None,
    gender=None,
    body_type=None,
    face_choice=None,
    camera_view=None,
    background=None,
    additional_style_note=None,
    options=None,
):
    """
    Main entry point. See module docstring for the unified image-slot
    convention. Exactly one of fabric_image/garment_image, and either
    person_image OR (gender+face_choice), are already enforced by the
    serializer before this is called — not re-checked here.
    """
    options = options or {}
    draft_mode = options.get("draft_mode", True)
    max_output_side = 512 if draft_mode else 1024
    is_own_model_path = person_image is None

    # ---------------------------------------------------------
    # Stage 0a: SUBJECT slot (image_0) — person photo or face photo
    # ---------------------------------------------------------
    if is_own_model_path:
        logger.info("Own-model path: gender=%s body_type=%s face_choice=%s", gender, body_type, face_choice)
        subject_buffer = _load_face_buffer(face_choice)
        subject_buffer.seek(0)
        out_w, out_h = get_output_dimensions(subject_buffer, max_side=max_output_side)
        subject_buffer.seek(0)
    else:
        subject_buffer = resize_to_fit(person_image, max_dim=MAX_INPUT_DIM)
        out_w, out_h = get_output_dimensions(person_image, max_side=max_output_side)

    # ---------------------------------------------------------
    # Stage 0b: GARMENT SOURCE slot (image_1) — fabric or garment photo
    # ---------------------------------------------------------
    if garment_image is not None:
        logger.info("garment_image path (NOT yet tested against real API)")
        garment_source_buffer = resize_to_fit(garment_image, max_dim=MAX_INPUT_DIM)
        final_prompt = GARMENT_IMAGE_PROMPT
        guidance = GARMENT_IMAGE_GUIDANCE
        seed = GARMENT_IMAGE_SEED
    else:
        garment_config = get_prompt_config(garment_type, garment_style)
        if garment_config is None:
            raise CloudflareGenerationError(
                f"No prompt configuration for garment_type='{garment_type}' garment_style='{garment_style}'"
            )
        garment_source_buffer = resize_to_fit(
            fabric_image, max_dim=MAX_INPUT_DIM, crop_box=options.get("fabric_crop_box")
        )
        final_prompt = garment_config["prompt"]
        guidance = garment_config["guidance"]
        seed = garment_config["seed"]

    # ---------------------------------------------------------
    # Stage 0c: own-model addendum — prepended, never edits the base prompt
    # ---------------------------------------------------------
    if is_own_model_path:
        addendum = get_own_model_instruction(gender, body_type)
        final_prompt = addendum + " " + final_prompt
        logger.info("Prepended own-model addendum (NOT yet tested against real API)")

    # ---------------------------------------------------------
    # Stage 0d: camera_view / background / style-note overrides (unchanged logic)
    # ---------------------------------------------------------
    camera_instruction = get_camera_view_instruction(camera_view)
    if camera_instruction:
        final_prompt = final_prompt + " " + camera_instruction
        logger.info("Applied camera_view override: %s", camera_view)

    background_instruction = get_background_instruction(background)
    if background_instruction:
        final_prompt = final_prompt + " " + background_instruction
        logger.info("Applied background override: %s", background)

    if additional_style_note:
        final_prompt = final_prompt + (
            " ADDITIONAL USER INSTRUCTION (apply only if it does not "
            "contradict the rules above): " + additional_style_note
        )
        logger.info("Applied additional_style_note")

    # ---------------------------------------------------------
    # Stage 1: debug copies
    # ---------------------------------------------------------
    debug_tag = garment_type or "garment_image"
    save_debug_copy(subject_buffer, f"sent_subject_{debug_tag}.jpg")
    save_debug_copy(garment_source_buffer, f"sent_garment_source_{debug_tag}.jpg")

    # ---------------------------------------------------------
    # Stage 2: call Cloudflare, retry on transient errors
    # ---------------------------------------------------------
    files = {
        "input_image_0": ("subject.jpg", subject_buffer, "image/jpeg"),
        "input_image_1": ("garment_source.jpg", garment_source_buffer, "image/jpeg"),
    }
    logger.info(
        "Stage 2: calling Cloudflare model=%s size=%sx%s own_model_path=%s",
        settings.CLOUDFLARE_MODEL, out_w, out_h, is_own_model_path,
    )
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.CLOUDFLARE_ACCOUNT_ID}/ai/run/{settings.CLOUDFLARE_MODEL}"
    )
    headers = {"Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}"}
    data = {
        "prompt": final_prompt,
        "width": out_w,
        "height": out_h,
        "guidance": guidance,
        "seed": seed,
    }

    response = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        logger.info("Sending request to Cloudflare (attempt %s/%s)", attempt, MAX_ATTEMPTS)
        try:
            response = requests.post(
                url, headers=headers, files=files, data=data, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.exceptions.RequestException as e:
            # Network-level failure (connection dropped, timeout, DNS, etc.)
            # — no response was received at all, so retry the same way we
            # already retry on a 500/429 status code.
            if attempt < MAX_ATTEMPTS:
                wait_seconds = 2 ** attempt
                logger.warning(
                    "Network error calling Cloudflare (%s). Retrying in %s seconds.",
                    e, wait_seconds,
                )
                time.sleep(wait_seconds)
                continue
            logger.error("Cloudflare request failed after network error: %s", e)
            raise CloudflareGenerationError(f"Network error calling Cloudflare: {e}")

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
        raise CloudflareGenerationError(f"Cloudflare request failed with status {response.status_code}")

    # ---------------------------------------------------------
    # Stage 3: parse response
    # ---------------------------------------------------------
    logger.info("Stage 3: parsing Cloudflare response")
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

    save_output_copy(image_bytes, f"output_{debug_tag}.png")

    # ---------------------------------------------------------
    # Stage 4: free memory
    # ---------------------------------------------------------
    del subject_buffer, garment_source_buffer, response
    gc.collect()
    logger.info("Stage 4: request finished, memory released")

    return image_bytes