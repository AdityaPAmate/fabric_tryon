"""Prompt entry point for blazer requests.

This package owns its prompt data, pose definitions, detail rules, and
generation settings. The shared scenario composer handles common assembly.
"""

from ..router import PromptRoutingError
from ..scenario_composer import build_prompt as _compose_prompt
from .settings import get_generation_settings


GARMENT_TYPE = 'blazer'
# garment_image is an input mode (use_garment_image=True), not a scenario.
SUPPORTED_SCENARIOS = {
    "person_photo",
    "person_pose",
    "face_photo",
    "generated_person",
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
    )

    if not isinstance(config, dict) or not config.get("prompt"):
        raise PromptRoutingError(
            f"No existing prompt is configured for garment '{GARMENT_TYPE}' "
            f"and scenario '{scenario}'."
        )

    result = dict(config)
    result.update(get_generation_settings(seed=seed, guidance=guidance))
    return result

