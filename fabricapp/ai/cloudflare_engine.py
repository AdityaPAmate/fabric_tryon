"""
Stage: Core engine that talks to Cloudflare Workers AI.

Image-slot convention:
    input_image_0 = SUBJECT
                    - person_photo     : the uploaded person photo
                    - person_pose      : a blank neutral canvas
                    - face_photo       : a blank neutral canvas
                    - generated_person : a blank neutral canvas
    input_image_1 = GARMENT SOURCE — fabric_image or garment_image
    input_image_2 = REFERENCE (only when there is one)
                    - face_photo  : the chosen face photo
                    - person_pose : the uploaded person photo

Which prompt is used is decided entirely by prompt_builder.py — this
module only sends images + the prompt and returns the result.

Seed: prompt_builder.py gives a fixed default seed (42). A fixed seed
makes different poses start from the same random noise, so the layouts
can look alike. For testing, send options={"seed": 7} (any integer) to
use a different seed. Not sent => the default seed, exactly as before.
"""

import base64
import gc
import io
import logging
import time

import requests
from django.conf import settings

from .prompts import get_face_image_path
from .prompt_builder import (
    SCENARIO_PERSON_PHOTO,
    SCENARIO_PERSON_POSE,
    detect_scenario,
    build_prompt,
)
from .image_utils import (
    resize_to_fit,
    get_output_dimensions,
    get_portrait_dimensions,
    make_blank_canvas,
)
from .debug_utils import save_debug_copy, save_output_copy

logger = logging.getLogger("fabricapp")

MAX_INPUT_DIM = 511
MAX_ATTEMPTS = 2
REQUEST_TIMEOUT_SECONDS = 180
FINAL_OUTPUT_SIDE = 1536  # draft_mode=false साठी output ची मोठी बाजू (पूर्वी 1024)



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


def _pick_seed(options, default_seed):
    """
    Returns options["seed"] when it is a valid integer, otherwise the
    default seed from the prompt config.
    """
    seed = options.get("seed")
    if seed is None:
        return default_seed
    try:
        return int(seed)
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid options.seed=%r, using default seed", seed)
        return default_seed


def _build_subject(scenario, person_image, face_choice, max_output_side):
    """
    Prepares image_0 (subject), the optional reference image (image_2)
    and the output size for the scenario.
    Returns (subject_buffer, reference_buffer_or_None, out_w, out_h).
    """
    if scenario == SCENARIO_PERSON_PHOTO:
        subject_buffer = resize_to_fit(person_image, max_dim=MAX_INPUT_DIM)
        out_w, out_h = get_output_dimensions(person_image, max_side=max_output_side)
        return subject_buffer, None, out_w, out_h

    # Own-model scenarios always output a portrait shape, and always
    # use a blank canvas as image_0.
    out_w, out_h = get_portrait_dimensions(max_side=max_output_side)
    canvas_w, canvas_h = get_portrait_dimensions(max_side=MAX_INPUT_DIM)
    subject_buffer = make_blank_canvas(canvas_w, canvas_h)

    reference_buffer = None
    if scenario == SCENARIO_PERSON_POSE:
        # The uploaded person photo goes in as a REFERENCE (image_2):
        # editing it directly would keep its original pose.
        reference_buffer = resize_to_fit(person_image, max_dim=MAX_INPUT_DIM)
    elif face_choice:
        # The chosen face goes in as a REFERENCE image (image_2),
        # not as image_0, so the model builds a full-body photo.
        reference_buffer = _load_face_buffer(face_choice)
    return subject_buffer, reference_buffer, out_w, out_h


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
    pose=None,
    garment_details=None,
    options=None,
):
    """
    Main entry point. The serializer has already validated the
    combination of inputs, so it is not re-checked here.
    """
    options = options or {}
    draft_mode = options.get("draft_mode", True)
    max_output_side = 512 if draft_mode else FINAL_OUTPUT_SIDE

    # Stage 0: decide the scenario and prepare the subject image (image_0)
    scenario = detect_scenario(person_image is not None, face_choice, pose, camera_view)
    logger.info(
        "Scenario=%s gender=%s body_type=%s face_choice=%s pose=%s",
        scenario, gender, body_type, face_choice, pose,
    )
    subject_buffer, reference_buffer, out_w, out_h = _build_subject(
        scenario, person_image, face_choice, max_output_side
    )

    # Stage 1: prepare the garment source image (image_1)
    use_garment_image = garment_image is not None
    if use_garment_image:
        garment_source_buffer = resize_to_fit(garment_image, max_dim=MAX_INPUT_DIM)
    else:
        garment_source_buffer = resize_to_fit(
            fabric_image, max_dim=MAX_INPUT_DIM, crop_box=options.get("fabric_crop_box")
        )

    # Stage 2: build the prompt (all prompt logic lives in prompt_builder.py)
    prompt_config = build_prompt(
        scenario=scenario,
        garment_type=garment_type,
        garment_style=garment_style,
        use_garment_image=use_garment_image,
        gender=gender,
        body_type=body_type,
        camera_view=camera_view,
        background=background,
        additional_style_note=additional_style_note,
        pose=pose,
        garment_details=garment_details,
    )
    if prompt_config is None:
        raise CloudflareGenerationError(
            f"No prompt available for garment_type='{garment_type}' garment_style='{garment_style}'"
        )

    # Debug file names include the pose so different poses do not overwrite each other.
    debug_tag = garment_type or "garment_image"
    if pose:
        debug_tag = f"{debug_tag}_{pose}"
    if camera_view:
        debug_tag = f"{debug_tag}_{camera_view}"
    save_debug_copy(subject_buffer, f"sent_subject_{debug_tag}.jpg")
    save_debug_copy(garment_source_buffer, f"sent_garment_source_{debug_tag}.jpg")
    if reference_buffer is not None:
        save_debug_copy(reference_buffer, f"sent_reference_{debug_tag}.jpg")

    # Stage 3: call Cloudflare, retrying on transient errors
    files = {
        "input_image_0": ("subject.jpg", subject_buffer, "image/jpeg"),
        "input_image_1": ("garment_source.jpg", garment_source_buffer, "image/jpeg"),
    }
    if reference_buffer is not None:
        files["input_image_2"] = ("reference.jpg", reference_buffer, "image/jpeg")

    seed = _pick_seed(options, prompt_config["seed"])
    logger.info(
        "Stage 3: calling Cloudflare model=%s size=%sx%s images=%s seed=%s",
        settings.CLOUDFLARE_MODEL, out_w, out_h, len(files), seed,
    )
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.CLOUDFLARE_ACCOUNT_ID}/ai/run/{settings.CLOUDFLARE_MODEL}"
    )
    headers = {"Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}"}
    data = {
        "prompt": prompt_config["prompt"],
        "width": out_w,
        "height": out_h,
        "guidance": prompt_config["guidance"],
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
            if attempt < MAX_ATTEMPTS:
                wait_seconds = 2 ** attempt
                logger.warning(
                    "Network error calling Cloudflare (%s). Retrying in %s seconds.",
                    e, wait_seconds,
                )
                time.sleep(wait_seconds)
                for _, file_tuple in files.items():
                    file_tuple[1].seek(0)  # rewind so the retry sends full images
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
            for _, file_tuple in files.items():
                file_tuple[1].seek(0)
            continue

        logger.error(
            "Cloudflare request failed. status=%s code=%s body=%s",
            response.status_code, internal_code, response.text[:500],
        )
        raise CloudflareGenerationError(f"Cloudflare request failed with status {response.status_code}")

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

    save_output_copy(image_bytes, f"output_{debug_tag}.png")

    # Stage 5: free memory
    del subject_buffer, garment_source_buffer, reference_buffer, files, response
    gc.collect()
    logger.info("Stage 5: request finished, memory released")

    return image_bytes