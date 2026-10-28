"""
Stage: Core engine that talks to Cloudflare Workers AI.

Image-slot convention:
    input_image_0 = SUBJECT
                    - person_photo      : the uploaded person photo
                    - person_pose       : a blank neutral canvas
                    - face_photo        : a blank neutral canvas
                    - generated_person  : a blank neutral canvas
                    - pose_reference    : the POSE REFERENCE PHOTO (it is
                                          edited: only the fabric changes,
                                          plus camera_view / face /
                                          background when they are sent)
    input_image_1 = GARMENT SOURCE — fabric_image or garment_image
    input_image_2 = REFERENCE (only when there is one)
                    - face_photo     : the chosen face photo
                    - person_pose    : the uploaded person photo
                    - pose_reference : the chosen face photo (only when a
                                       face_choice was sent)

Which prompt is used is decided by the request coordinator and the selected
garment builder — this module only prepares images, calls Cloudflare, and
returns the generated result.

Pose reference photos (pose_reference.py): for a garment + pose that has a
reference photo (today saree + pallu_on_head) and no person_image, the
photo is sent as image 0 instead of describing the pose in the prompt.
A camera_view does NOT switch this off: the selected prompt builder controls
the reference prompt, while the original background of the photo is kept.
"""

import base64
import gc
import hashlib
import io
import json
import logging
import os
import re
import time
from uuid import uuid4
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from django.conf import settings

from ..timing import timed_stage
from .faces import get_face_image_path
from .router import (
    SCENARIO_PERSON_PHOTO,
    SCENARIO_PERSON_POSE,
    SCENARIO_POSE_REFERENCE,
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
SAFETY_RETRY_COUNT = 1
REQUEST_TIMEOUT_SECONDS = 180
FINAL_OUTPUT_SIDE = 1536  # draft_mode=false साठी output ची मोठी बाजू (पूर्वी 1024)



class CloudflareGenerationError(Exception):
    """Raised when Cloudflare fails to generate an image after retries."""

    def __init__(self, message, *, status_code=None, provider_code=None, diagnostics=None):
        super().__init__(message)
        self.status_code = status_code
        self.provider_code = provider_code
        self.diagnostics = diagnostics


@dataclass(frozen=True)
class GenerationResult:
    """Image bytes and seed submitted on the successful provider attempt.

    Cloudflare does not return its internal sampler seed for this model.
    """

    image_bytes: bytes
    effective_seed: int
    diagnostics: dict | None = None


def _load_face_buffer(face_choice):
    path = get_face_image_path(face_choice)
    if path is None:
        raise CloudflareGenerationError(f"No face image file found for '{face_choice}'")
    try:
        with open(path, "rb") as f:
            return resize_to_fit(io.BytesIO(f.read()), max_dim=MAX_INPUT_DIM)
    except FileNotFoundError:
        raise CloudflareGenerationError(f"Face image file not found on disk: {path}")


def _load_uploaded_face_buffer(face_image):
    """Prepare the user-uploaded face photo as the reference image."""
    if face_image is None:
        return None
    # Read into a fresh stream so earlier validation/resizing cannot leave
    # the uploaded file pointer at EOF.
    face_image.seek(0)
    image_bytes = face_image.read()
    face_image.seek(0)
    return resize_to_fit(io.BytesIO(image_bytes), max_dim=MAX_INPUT_DIM)


def _load_pose_reference_bytes(path):
    """Reads the pose reference photo; a missing file gives a clear error."""
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        raise CloudflareGenerationError(
            f"Pose reference image not found on disk: {path}"
        )


def _build_pose_reference_subject(pose_reference_path, face_choice, face_image, max_output_side):
    """
    pose_reference scenario: image_0 is the reference PHOTO itself (it is
    edited), so the output has the same shape as the photo. The chosen face
    (if any) goes in as image_2.
    Returns (subject_buffer, reference_buffer_or_None, out_w, out_h).
    """
    photo_bytes = _load_pose_reference_bytes(pose_reference_path)

    # A fresh BytesIO for every call, so no function sees a stream that
    # another function has already read to the end.
    subject_buffer = resize_to_fit(io.BytesIO(photo_bytes), max_dim=MAX_INPUT_DIM)
    out_w, out_h = get_output_dimensions(
        io.BytesIO(photo_bytes), max_side=max_output_side
    )

    reference_buffer = (
        _load_face_buffer(face_choice) if face_choice
        else _load_uploaded_face_buffer(face_image) if face_image
        else None
    )
    return subject_buffer, reference_buffer, out_w, out_h


def _build_subject(
    scenario, person_image, face_choice, face_image, max_output_side, pose_reference_path=None,
):
    """
    Prepares image_0 (subject), the optional reference image (image_2)
    and the output size for the scenario.
    Returns (subject_buffer, reference_buffer_or_None, out_w, out_h).
    """
    if scenario == SCENARIO_POSE_REFERENCE:
        return _build_pose_reference_subject(
            pose_reference_path, face_choice, face_image, max_output_side
        )

    if scenario == SCENARIO_PERSON_PHOTO:
        subject_buffer = resize_to_fit(person_image, max_dim=MAX_INPUT_DIM)
        out_w, out_h = get_output_dimensions(person_image, max_side=max_output_side)
        return subject_buffer, None, out_w, out_h

    # Pose generation uses the original stable 3:4 portrait frame. It gives
    # the model enough space for the complete head-to-feet pose and keeps the
    # fabric rendering at the same scale as the earlier sharp outputs.
    out_w, out_h = get_portrait_dimensions(max_side=max_output_side)
    canvas_w, canvas_h = get_portrait_dimensions(max_side=MAX_INPUT_DIM)
    subject_buffer = make_blank_canvas(canvas_w, canvas_h)

    reference_buffer = None
    if scenario == SCENARIO_PERSON_POSE:
        # The uploaded person photo goes in as a REFERENCE (image_2):
        # editing it directly would keep its original pose.
        reference_buffer = resize_to_fit(person_image, max_dim=MAX_INPUT_DIM)
    elif face_choice or face_image:
        # The selected or uploaded face goes in image_2 as a reference.
        reference_buffer = (
            _load_face_buffer(face_choice) if face_choice
            else _load_uploaded_face_buffer(face_image)
        )
    return subject_buffer, reference_buffer, out_w, out_h


def _rewind_uploads(files):
    """Reset in-memory multipart streams before sending another request."""
    for _, file_tuple in files.items():
        file_tuple[1].seek(0)


def generate_tryon_image(
    person_image=None,
    fabric_image=None,
    garment_image=None,
    garment_type=None,
    garment_style=None,
    gender=None,
    body_type=None,
    face_choice=None,
    face_image=None,
    camera_view=None,
    background=None,
    additional_style_note=None,
    pose=None,
    garment_details=None,
    options=None,
    scenario=None,
    pose_reference_path=None,
    prompt_config=None,
):
    """
    Main entry point. The serializer has already validated the
    combination of inputs, so it is not re-checked here.
    """
    options = options or {}
    draft_mode = options.get("draft_mode", True)
    max_output_side = 512 if draft_mode else FINAL_OUTPUT_SIDE
    use_garment_image = garment_image is not None

    # Routing and prompt selection belong to ai.main/router. This module
    # only prepares the model inputs and sends the already selected config.
    if not scenario or not isinstance(prompt_config, dict):
        raise CloudflareGenerationError(
            "The generation coordinator must provide scenario and prompt_config."
        )

    # Stage 0: prepare the subject image (image_0) for the chosen scenario.
    logger.info(
        "Scenario=%s gender=%s body_type=%s face_choice=%s face_image=%s pose=%s "
        "camera_view=%s pose_reference=%s",
        scenario, gender, body_type, face_choice, bool(face_image), pose, camera_view,
        pose_reference_path,
    )
    with timed_stage("input_preparation", scenario=scenario):
        subject_buffer, reference_buffer, out_w, out_h = _build_subject(
            scenario, person_image, face_choice, face_image, max_output_side, pose_reference_path
        )

        # Stage 1: prepare the garment source image (image_1)
        if use_garment_image:
            garment_source_buffer = resize_to_fit(garment_image, max_dim=MAX_INPUT_DIM)
        else:
            garment_source_buffer = resize_to_fit(
                fabric_image, max_dim=MAX_INPUT_DIM, crop_box=options.get("fabric_crop_box")
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

    logger.info(
        "Stage 3: calling Cloudflare model=%s size=%sx%s images=%s",
        settings.CLOUDFLARE_MODEL, out_w, out_h, len(files),
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
        "seed": prompt_config["seed"],
    }
    safety_fallback_prompt = prompt_config.get("safety_fallback_prompt")

    # Trace the prepared provider inputs, not only the original uploaded files.
    # Hashes contain neither image contents nor credentials. Other garments keep
    # their existing response shape and request behaviour.
    diagnostics = None
    if garment_type == "shirt":
        diagnostics = {
            "version": "shirt-trace-v1",
            "request_id": uuid4().hex,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "deployment_revision": os.getenv("RENDER_GIT_COMMIT") or "unknown",
            "model": settings.CLOUDFLARE_MODEL,
            "scenario": scenario,
            "requested_seed": data["seed"],
            "effective_seed": None,
            "guidance": data["guidance"],
            "width": out_w,
            "height": out_h,
            "input_hashes": {
                slot: hashlib.sha256(file_tuple[1].getvalue()).hexdigest()
                for slot, file_tuple in files.items()
            },
            "attempts": [],
        }

    def generation_error(message, **kwargs):
        if diagnostics is not None:
            logger.info("Shirt failed generation trace: %s", json.dumps(diagnostics, sort_keys=True))
        return CloudflareGenerationError(message, diagnostics=diagnostics, **kwargs)

    response = None
    requested_seed = data["seed"]
    # Internal diagnostic override: controlled tests can use one exact
    # prompt/seed without silently sampling the alternate safety fallback.
    # Normal requests keep the existing retry policy.
    safety_retry_count = prompt_config.get("safety_retry_count", SAFETY_RETRY_COUNT)
    for safety_attempt in range(safety_retry_count + 1):
        # The garment setting remains the configured seed. A different seed is
        # used only after Cloudflare has rejected the first sampled output.
        # A garment builder may also supply a conservative, route-specific
        # prompt for this retry. This is needed because 3030 is based on the
        # sampled output, not on request validation.
        data["seed"] = requested_seed + safety_attempt
        using_safety_fallback = bool(safety_attempt and safety_fallback_prompt)
        data["prompt"] = (
            safety_fallback_prompt if using_safety_fallback else prompt_config["prompt"]
        )
        for attempt in range(1, MAX_ATTEMPTS + 1):
            attempt_trace = None
            started = time.monotonic()
            if diagnostics is not None:
                signature = {
                    "model": settings.CLOUDFLARE_MODEL,
                    "inputs": diagnostics["input_hashes"],
                    "parameters": data,
                }
                attempt_trace = {
                    "seed": data["seed"],
                    "network_attempt": attempt,
                    "fallback_prompt": using_safety_fallback,
                    "prompt_sha256": hashlib.sha256(data["prompt"].encode()).hexdigest(),
                    "request_sha256": hashlib.sha256(
                        json.dumps(signature, sort_keys=True).encode()
                    ).hexdigest(),
                }
                diagnostics["attempts"].append(attempt_trace)
            logger.info(
                "Sending request to Cloudflare (network attempt %s/%s, generation seed=%s, "
                "safety_fallback=%s)",
                attempt, MAX_ATTEMPTS, data["seed"], using_safety_fallback,
            )
            try:
                with timed_stage(
                    "cloudflare_attempt", network_attempt=attempt,
                    safety_attempt=safety_attempt, seed=data["seed"],
                    width=out_w, height=out_h,
                ) as timing:
                    response = requests.post(
                        url, headers=headers, files=files, data=data,
                        timeout=REQUEST_TIMEOUT_SECONDS,
                    )
                    timing["http_status"] = response.status_code
            except requests.exceptions.RequestException as e:
                if attempt_trace is not None:
                    attempt_trace.update(
                        outcome="network_error",
                        duration_ms=round((time.monotonic() - started) * 1000),
                    )
                if attempt < MAX_ATTEMPTS:
                    wait_seconds = 2 ** attempt
                    logger.warning(
                        "Network error calling Cloudflare (%s). Retrying in %s seconds.",
                        e, wait_seconds,
                    )
                    with timed_stage("retry_wait", reason="network_error", seconds=wait_seconds):
                        time.sleep(wait_seconds)
                    _rewind_uploads(files)
                    continue
                logger.error("Cloudflare request failed after network error: %s", e)
                raise generation_error(f"Network error calling Cloudflare: {e}")

            if attempt_trace is not None:
                attempt_trace.update(
                    http_status=response.status_code,
                    cf_ray=response.headers.get("cf-ray"),
                    provider_date=response.headers.get("date"),
                    duration_ms=round((time.monotonic() - started) * 1000),
                )

            if response.status_code == 200:
                if attempt_trace is not None:
                    attempt_trace["outcome"] = "provider_success"
                break

            internal_code = None
            try:
                internal_code = response.json().get("errors", [{}])[0].get("code")
            except Exception:
                pass

            if attempt_trace is not None:
                match = re.search(r"\(([0-9a-fA-F-]{36})\)", response.text)
                attempt_trace.update(
                    outcome="provider_rejection" if internal_code == 3030 else "provider_error",
                    provider_code=internal_code,
                    provider_request_id=match.group(1) if match else None,
                )
                logger.info(
                    "Shirt provider attempt request_id=%s trace=%s",
                    diagnostics["request_id"], json.dumps(attempt_trace, sort_keys=True),
                )

            if response.status_code in (500, 429) and attempt < MAX_ATTEMPTS:
                wait_seconds = 2 ** attempt
                logger.warning(
                    "Cloudflare returned status %s (code %s). Retrying in %s seconds.",
                    response.status_code, internal_code, wait_seconds,
                )
                with timed_stage("retry_wait", reason="provider_status", seconds=wait_seconds):
                    time.sleep(wait_seconds)
                _rewind_uploads(files)
                continue

            # Error 3030 means the provider rejected the sampled output. The
            # inputs and the configured garment defaults are valid; request
            # one controlled alternate sample before returning an error.
            if internal_code == 3030 and safety_attempt < safety_retry_count:
                logger.warning(
                    "Cloudflare rejected generated output (3030) with seed=%s; "
                    "retrying once with seed=%s.",
                    data["seed"], requested_seed + safety_attempt + 1,
                )
                _rewind_uploads(files)
                break

            logger.error(
                "Cloudflare request failed. status=%s code=%s body=%s",
                response.status_code, internal_code, response.text[:500],
            )
            raise generation_error(
                f"Cloudflare request failed with status {response.status_code}",
                status_code=response.status_code,
                provider_code=internal_code,
            )
        else:
            # The inner loop only exhausts after an exception, which is
            # raised above. Keep the branch explicit for future changes.
            raise generation_error("Cloudflare request did not complete")

        if response is not None and response.status_code == 200:
            break

    with timed_stage("response_processing"):
        logger.info("Stage 4: parsing Cloudflare response")
        content_type = response.headers.get("Content-Type", "")

        if "application/json" in content_type:
            result = response.json()
            image_b64 = result.get("result", {}).get("image", "")
            if not image_b64:
                logger.error("No image field found in Cloudflare response: %s", result)
                raise generation_error("Cloudflare response did not contain an image")
            image_bytes = base64.b64decode(image_b64)
        elif "image" in content_type:
            image_bytes = response.content
        else:
            logger.error("Unexpected content type from Cloudflare: %s", content_type)
            raise generation_error(f"Unexpected response content type: {content_type}")

        save_output_copy(image_bytes, f"output_{debug_tag}.png")

        del subject_buffer, garment_source_buffer, reference_buffer, files, response
        gc.collect()
        logger.info("Stage 5: request finished, memory released")

    if diagnostics is not None:
        diagnostics["effective_seed"] = data["seed"]
        logger.info("Shirt generation trace: %s", json.dumps(diagnostics, sort_keys=True))

    return GenerationResult(
        image_bytes=image_bytes,
        effective_seed=data["seed"],
        diagnostics=diagnostics,
    )
