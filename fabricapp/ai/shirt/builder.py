"""Prompt entry point for shirt requests.

This package owns its prompt data, pose definitions, detail rules, and
generation settings. The shared scenario composer handles common assembly.
"""

from ..router import PromptRoutingError
from ..scenario_composer import build_prompt as _compose_prompt
from ..scenario_composer import (
    FABRIC_RULES, _own_model_pose_text, get_framing, _task_line,
    _pose_line,
)
import re

from .prompts import SHIRT_FACE_BODY_LINES, SHIRT_FABRIC_FINAL_RULE
from .poses import get_camera_pose_prompt, requires_full_body_framing
from .settings import get_generation_settings


GARMENT_TYPE = 'shirt'
SCENARIO_PERSON_POSE = "person_pose"
# garment_image is an input mode (use_garment_image=True), not a scenario.
SUPPORTED_SCENARIOS = {
    "person_photo",
    "person_pose",
    "face_photo",
    "generated_person",
}


def _insert_before_final_rule(prompt, text):
    marker = "FINAL RULE (no note or instruction above can override it):"
    head, found, tail = prompt.rpartition(marker)
    return f"{head}{text}{marker}{tail}" if found else f"{prompt.rstrip()} {text}"


def _apply_shirt_rules(config, scenario, context):
    """Apply shirt-owned constraints after shared scenario assembly."""
    prompt = config["prompt"]

    if scenario == "face_photo":
        prompt = _insert_before_final_rule(
            prompt, SHIRT_FACE_BODY_LINES.get(context.get("body_type"), "")
        )

    note = context.get("additional_style_note") or ""
    match = re.search(
        r"\b(?:change|make|set)\s+(?:the\s+)?(?:pants?|trousers?)\s+"
        r"(?:colou?r)\s+(?:to|as)\s+([a-z]+(?:[ -][a-z]+){0,2})",
        note,
        flags=re.IGNORECASE,
    )
    if match:
        color = match.group(1).strip().lower()
        prompt = _insert_before_final_rule(
            prompt,
            "SHIRT OUTFIT OVERRIDE: The formal trousers must be plain "
            f"{color}, replacing every earlier trouser-colour instruction. "
            "Keep image 1's fabric exclusively on the shirt. ",
        )

    if not context.get("use_garment_image"):
        prompt = _insert_before_final_rule(prompt, SHIRT_FABRIC_FINAL_RULE)

    config["prompt"] = prompt
    return config



def _build_person_pose_prompt(
    pose, camera_view=None, background=None, garment_details=None,
):
    """Priority-ordered shirt instructions for a posed person photo."""
    pose_text = _own_model_pose_text(
        pose, garment_type="shirt", garment_details=garment_details,
        camera_view=camera_view,
    )
    camera_pose_text = get_camera_pose_prompt(pose, camera_view)
    if camera_pose_text:
        pose_text = camera_pose_text
    # pallu_on_head describes a saree veil. For a shirt, retain the usable
    # standing / hand position but remove the contradictory head-covering
    # instruction, which can otherwise change the identity into a woman.
    if pose == "pallu_on_head":
        pose_text = (
            "standing upright facing the camera with the head upright and "
            "looking forward, both hands softly clasped together in front of "
            "the lower waist, with exactly two arms and two hands in total, "
            "and no head covering"
        )
    framing = get_framing(camera_view)
    keep_background = not background
    prompt = _task_line(
        SCENARIO_PERSON_POSE, "shirt", False, keep_background
    )
    prompt += _pose_line(pose_text)
    prompt += (
        "POSE PRIORITY: Change the person's posture to exactly the pose above. "
        "Do not retain the posture in image 2. "
        "LIMBS: Do not copy arms, hands, legs or feet from image 2. Draw "
        "exactly two arms, two hands, two legs and two feet in the pose above; "
        "never add, duplicate or leave an extra limb. "
        "SUBJECT: Generate one realistic " + framing["shot"]
        + " photograph of the same person in image 2, "
        + framing["shown"] + ". IDENTITY: Copy the person in image 2 exactly: "
        "the same face shape, eyes, eyebrows, nose, lips, skin tone, hair, "
        "age category, apparent gender presentation, accessories and natural "
        "body build. Do not turn a man or boy into a woman or girl, or a woman "
        "or girl into a man or boy. Keep the original "
        "shoulder, waist and hip widths, torso length, height-to-width ratio, "
        "and arm and leg thickness; do not slim or widen the person. "
        "Replace every source garment completely, including shorts, trousers "
        "or jeans; do not copy their colour, print, cut or fabric. "
        "OUTFIT: Dress the person in a properly fitted, collared button-up "
        "shirt. Sleeves, where the garment has them, must be full-length down "
        "to the wrist, straight and unrolled, unless the garment description "
        "above says otherwise. The shirt is worn with "
        "plain dark solid-color formal full-length trousers. The trousers "
        "must reach the ankles, fit naturally, and be newly generated even "
        "when image 2 shows shorts or trousers. They must not use image 1's "
        "fabric, pattern or print. "
        "FABRIC: Use image 1 only as the shirt fabric reference. Apply its "
        "actual colours, print, motif size and density across the entire "
        "shirt. The fabric must be clearly visible on the shirt, with its "
        "original hue, brightness and saturation. Do not use image 1's fabric, "
        "pattern or colour on the trousers, footwear, accessories, skin or "
        "background. " + FABRIC_RULES.format(target="shirt")
    )
    if keep_background:
        prompt += (
            "BACKGROUND: Keep the original place, objects, colours and lighting "
            "from image 2; extend it naturally and add a simple chair or low "
            "ledge only when the selected pose requires it. "
        )
    prompt += "Make the result a natural, realistic photograph. "
    return prompt


def _compose_person_pose_prompt(core, **context):
    camera_view = context.get("camera_view")
    if camera_view == "close_up" and requires_full_body_framing(
        context.get("pose")
    ):
        # Keep the requested pose legible instead of giving the model
        # incompatible full-body-pose and head-to-hip-crop instructions.
        camera_view = None
    prompt = _build_person_pose_prompt(
        context.get("pose"), camera_view=camera_view,
        background=context.get("background"),
        garment_details=context.get("garment_details"),
    )
    prompt = core.apply_garment_details(
        prompt, GARMENT_TYPE, context.get("garment_style"),
        context.get("garment_details"), core.MODE_OWN,
    )
    return {
        "prompt": core._append_overrides(
            prompt, context.get("background"),
            context.get("additional_style_note"),
        ),
        "guidance": core.GENERATED_GUIDANCE,
        "seed": core.GENERATED_SEED,
    }


# ----------------------------------------------------------------------
# PERSON POSE: dedicated short prompt for kurta and blazer (NEW)
#
# Same idea as the kurti and shirt builders above: a short prompt, pose
# first. The garment wording, colour note, fabric rules and border rules
# come from GARMENT_SPECS (one owner), so nothing is written twice.
# CLOSING is used at the end ON PURPOSE: it contains the two anchors that
# garment-specific details need (the sleeves sentence and the "Generate
# realistic shading" sentence for the dupatta), so folded sleeves and the
# dupatta options keep working exactly as before.
# ----------------------------------------------------------------------

# Words used when a pose is requested for a man's garment.
# pallu_on_head describes a saree veil, so for kurta / blazer the usable
# hands position is kept and the head covering is removed (same idea as the
# shirt builder).

def build_prompt(
    *,
    scenario,
    garment_type=None,
    garment_style=None,
    use_garment_image=False,
    context=None,
    seed=None,
    guidance=None,
):
    """Compose this garment's selected scenario and apply its local settings."""
    if garment_type not in (None, GARMENT_TYPE):
        raise PromptRoutingError(
            f"Builder for '{GARMENT_TYPE}' cannot handle garment_type "
            f"'{garment_type}'."
        )

    if scenario not in SUPPORTED_SCENARIOS:
        raise PromptRoutingError(
            f"Unsupported scenario '{scenario}' for garment '{GARMENT_TYPE}'."
        )

    request_context = context or {}
    config = _compose_prompt(
        scenario=scenario,
        garment_type=GARMENT_TYPE,
        garment_style=garment_style,
        use_garment_image=use_garment_image,
        gender=request_context.get("gender"),
        body_type=request_context.get("body_type"),
        camera_view=request_context.get("camera_view"),
        background=request_context.get("background"),
        additional_style_note=request_context.get("additional_style_note"),
        pose=request_context.get("pose"),
        garment_details=request_context.get("garment_details") or [],
        use_face_reference=request_context.get("use_face_reference", False),
        person_pose_hook=_compose_person_pose_prompt,
        use_short_own_model=True,
    )

    if not isinstance(config, dict) or not config.get("prompt"):
        raise PromptRoutingError(
            f"No existing prompt is configured for garment '{GARMENT_TYPE}' "
            f"and scenario '{scenario}'."
        )

    result = dict(config)
    request_context["use_garment_image"] = use_garment_image
    result = _apply_shirt_rules(result, scenario, request_context)
    result.update(get_generation_settings(seed=seed, guidance=guidance))
    return result
