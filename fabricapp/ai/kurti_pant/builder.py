"""Prompt entry point for kurti_pant requests.

This package owns its prompt data, pose definitions, detail rules, and
generation settings. The shared scenario composer handles common assembly.
"""

from ..router import PromptRoutingError
from ..scenario_composer import build_prompt as _compose_prompt
from ..scenario_composer import (
    BACKGROUND_DESCRIPTIONS, _own_model_pose_text, get_framing,
    _task_line, _pose_line, _short_background,
)
from .settings import get_generation_settings
from . import prompts as prompt_data


GARMENT_TYPE = 'kurti_pant'
SCENARIO_PERSON_POSE = "person_pose"
# garment_image is an input mode (use_garment_image=True), not a scenario.
SUPPORTED_SCENARIOS = {
    "person_photo",
    "person_pose",
    "face_photo",
    "generated_person",
}



def _build_person_pose_prompt(
    pose, camera_view=None, background=None, gender=None,
):
    """Short, priority-ordered instructions for person-photo kurti edits."""
    pose_text = _own_model_pose_text(
        pose, garment_type="kurti_pant", camera_view=camera_view
    )
    framing = get_framing(camera_view)
    keep_background = not background
    prompt = _task_line(
        SCENARIO_PERSON_POSE, "kurti_pant", False, keep_background
    )
    prompt += _pose_line(pose_text)
    dupatta_rule = (
        "For this pose, include a plain white dupatta draped over the head; "
        "keep it solid white and do not apply image 1's fabric to it. "
        if pose == "pallu_on_head"
        else "No dupatta. "
    )
    # A chair pose changes the person's perspective more than the standing
    # poses. Keep this lock local to that pose so the proven prompt for the
    # other kurti-pant poses remains byte-for-byte the same.
    cross_leg_identity_lock = (
        "CROSS-CHAIR IDENTITY LOCK: Copy the exact facial structure from image 2 "
        "— same eyes, eyebrows, nose, lips and face shape — and preserve the "
        "same slim shoulder, waist and hip widths when seated. Keep the same "
        "arm and leg thickness; do not make her fuller or wider because she is "
        "sitting. The kurti and plain white pants are the only garments visible; "
        "do not retain any source clothing or loose cloth from image 2. "
        if pose == "cross_leg_chair_recline"
        else ""
    )
    prompt += (
        "POSE PRIORITY: Change the person's posture to exactly the pose above. "
        "Do not retain their original posture. "
        "LIMBS: Do not copy the arms, hands, legs or feet from image 2. Draw "
        "exactly two arms, two hands, two legs and two feet in the pose above; "
        "never add, duplicate or leave an extra hand, arm, leg or foot. "
        "SUBJECT: Generate one realistic " + framing["shot"]
        + " photograph of the same person in image 2, "
        + framing["shown"] + ". Copy the face accurately from image 2 — "
        "same eyes, eyebrows, nose, lips and face shape — preserving their "
        "recognizable face, exact age (if image 2 is a child or girl, keep her "
        "clearly as a child/girl, do not age her into an adult), hair, skin "
        "tone, accessories and natural body build. Keep their original "
        "shoulder, waist and hip widths, torso length, height-to-width ratio, "
        "and arm and leg thickness; do not slim or widen them. Replace the "
        "clothes in image 2 completely; do not copy their color, print or "
        "garment design. "
        + cross_leg_identity_lock +
        "OUTFIT: Dress this person in a modest Indian kurti with full-length sleeves "
        "reaching the wrists, paired with plain, solid white, full-length "
        "pants visible below the kurti and reaching the ankles. The pants are "
        "white and have no print. " + dupatta_rule +
        "FABRIC: Use image 1 only as the kurti fabric reference. Apply its "
        "actual colors, print, motif size and density across the kurti. Do "
        "not use image 1's fabric or pattern on the white pants. If image 1 "
        "has a distinct border, use it only as a narrow kurti hem and sleeve "
        "cuff trim; do not invent a border when none is shown. "
    )
    if keep_background:
        prompt += (
            "BACKGROUND: Keep the original place, objects, colors and lighting "
            "from image 2; extend it naturally and add a simple chair or low "
            "ledge only when the selected pose requires it. "
        )
    else:
        # Background requested: embed it here (short + catalog lighting).
        # Reinforce fabric for the seated pose where drape-vs-background
        # can cause the model to skip applying the fabric swatch.
        bg_desc = BACKGROUND_DESCRIPTIONS.get(background) if background else None
        if bg_desc:
            prompt += _short_background(bg_desc, pose=pose)
        if pose == "cross_leg_chair_recline":
            prompt += (
                "FABRIC PRIORITY: the kurti must clearly be made from image 1's "
                "fabric, with its actual colours, print and motifs across the "
                "whole kurti — never plain or blank, even when seated. "
            )
    prompt += "Make the result a natural, realistic photograph. "
    return prompt


def _compose_person_pose_prompt(core, **context):
    prompt = _build_person_pose_prompt(
        context.get("pose"), camera_view=context.get("camera_view"),
        background=context.get("background"), gender=context.get("gender"),
    )
    prompt = core.apply_garment_details(
        prompt, GARMENT_TYPE, context.get("garment_style"),
        context.get("garment_details"), core.MODE_OWN,
    )
    return {
        "prompt": core._append_overrides(
            prompt, None, context.get("additional_style_note")
        ),
        "guidance": core.GENERATED_GUIDANCE,
        "seed": core.GENERATED_SEED,
    }

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
        use_short_own_model=True,
        person_pose_hook=_compose_person_pose_prompt,
    )

    if not isinstance(config, dict) or not config.get("prompt"):
        raise PromptRoutingError(
            f"No existing prompt is configured for garment '{GARMENT_TYPE}' "
            f"and scenario '{scenario}'."
        )

    result = dict(config)
    result["safety_fallback_prompt"] = result["prompt"].rstrip() + " " + prompt_data.RETRY_PRESENTATION
    result.update(get_generation_settings(seed=seed, guidance=guidance))
    return result

