"""Compose shirt instructions once, with explicit body, fit and sleeve choices."""

import hashlib
import logging
import re

from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.ai.scene.camera_data import get_framing
from fabricapp.ai.pipeline.router import PromptRoutingError
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.pipeline.scenario_composer import _own_model_pose_text, _person_description
from fabricapp.ai.garments.shirt import prompts
from fabricapp.ai.garments.shirt.details import get_shirt_detail_prompt
from fabricapp.ai.garments.shirt.poses import get_camera_pose_prompt, requires_full_body_framing
from fabricapp.ai.garments.shirt.settings import get_generation_settings

GARMENT_TYPE = "shirt"
SUPPORTED_SCENARIOS = {"person_photo", "person_pose", "face_photo", "generated_person"}


def build_prompt(
    *, scenario, garment_type=None, garment_style=None, use_garment_image=False,
    context=None, seed=None, guidance=None,
):
    """Resolve each selected attribute before adding pose and scenery."""
    if garment_type not in (None, GARMENT_TYPE):
        raise PromptRoutingError(f"Shirt builder cannot handle '{garment_type}'.")
    if scenario not in SUPPORTED_SCENARIOS or use_garment_image:
        raise PromptRoutingError(f"Unsupported shirt scenario '{scenario}'.")
    context = context or {}
    camera = context.get("camera_view")
    pose = context.get("pose")
    details = context.get("garment_details") or []
    if camera == "close_up" and requires_full_body_framing(pose):
        camera = None
    framing = get_framing(camera)
    is_person = scenario in {"person_photo", "person_pose"}
    reference = 0 if scenario == "person_photo" else 2

    # The selected shirt construction belongs next to the task, before
    # face, pose and scene instructions compete for model attention.
    parts = [prompts.TASK, get_shirt_detail_prompt(details)]
    if scenario == "person_photo":
        parts.append(prompts.PERSON_EDIT_SUBJECT)
    elif scenario == "person_pose":
        parts.append(prompts.PERSON_POSE_SUBJECT)
    elif scenario == "face_photo":
        parts.append(prompts.FACE_SUBJECT)
    else:
        parts.append("SUBJECT: Generate " + _person_description(
            context.get("gender"), context.get("body_type")
        ) + ". ")

    if not is_person:
        body_type = context.get("body_type") or "slim"
        child = context.get("gender") in {"boy", "girl"}
        if child:
            parts.append(prompts.CHILD_SUBJECT)
        elif scenario == "face_photo":
            parts.append("Generate an adult " + {
                "men": "man", "women": "woman",
            }.get(context.get("gender"), "person") + ". ")
        parts.append(prompts.BODY_BUILD[body_type])
        parts.append(prompts.BODY_FIT)
        if scenario == "face_photo":
            parts.append("The face reference determines facial identity only. ")

    parts.append(prompts.OUTFIT)
    if "folded_sleeves" not in details:
        parts.append(prompts.PRESSED_SLEEVES)
    parts.append(prompts.FABRIC)

    if scenario != "person_photo":
        parts.append("FRAMING: " + framing["shown"] + framing["fill"] + ". ")
        pose_text = get_camera_pose_prompt(pose, camera) or _own_model_pose_text(
            pose, garment_type="shirt", garment_details=details, camera_view=camera,
        )
        parts.append("POSE: the person is " + pose_text + ". ")
        if camera != "close_up":
            parts.append(prompts.ANATOMY)
        if scenario == "person_pose":
            parts.append("Use the requested pose rather than the posture in image 2. ")

    background = context.get("background")
    if background:
        parts.append("BACKGROUND: " + get_background_description(background, garment_type="shirt") + ". ")
    elif is_person:
        parts.append(f"BACKGROUND: preserve the original setting in image {reference}. ")
    else:
        parts.append("BACKGROUND: a plain neutral studio. ")
    if pose == "cross_leg_chair_recline":
        parts.append("Include the upholstered armchair supporting the seated person. ")
    parts.append(prompts.LIGHTING)

    note = (context.get("additional_style_note") or "").strip()
    # Retain the supported trouser-colour note without allowing it to
    # silently replace the explicit body, sleeve and tuck selections.
    match = re.search(
        r"\b(?:change|make|set)\s+(?:the\s+)?(?:pants?|trousers?)\s+"
        r"(?:colou?r)\s+(?:to|as)\s+([a-z]+(?:[ -][a-z]+){0,2})",
        note, flags=re.IGNORECASE,
    )
    if match:
        parts = [part.replace("plain dark solid-colour trousers",
                 "plain " + match.group(1).strip().lower() + " solid-colour trousers")
                 for part in parts]
    if note:
        parts.append("STYLE NOTE: " + note.rstrip(".") + ". " + prompts.NOTE_PRIORITY)
    parts.append(prompts.PRESSED_FINISH)
    parts.append(prompts.FINAL)
    parts.append(prompts.output_contract(scenario, camera, details))
    prompt = "".join(parts)
    result = {"prompt": prompt}
    if scenario == "face_photo":
        result["safety_fallback_prompt"] = prompt + prompts.RETRY_PRESENTATION
    result.update(get_generation_settings(seed=seed, guidance=guidance))
    result = apply_fabric_conditioning(result, context, GARMENT_TYPE, garment_style)
    logging.getLogger("fabricapp").info(
        "Shirt final prompt version=%s scenario=%s body=%s "
        "pose=%s background=%s details=%s words=%s sha256=%s seed=%s guidance=%s",
        result.get("prompt_version", "resolved-attributes-v3"), scenario, context.get("body_type"), pose, background, details,
        len(result["prompt"].split()), hashlib.sha256(result["prompt"].encode()).hexdigest()[:16],
        result["seed"], result["guidance"],
    )
    return result
