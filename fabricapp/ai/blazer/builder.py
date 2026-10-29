"""Prompt entry point for blazer requests.

This package owns its prompt data, pose definitions, detail rules, and
generation settings. The shared scenario composer handles common assembly.
"""

from ..router import PromptRoutingError
from ..scenario_composer import build_prompt as _compose_prompt
from .settings import get_generation_settings
from . import prompts as prompt_data
import logging

logger = logging.getLogger("fabricapp")


GARMENT_TYPE = 'blazer'
# garment_image is an input mode (use_garment_image=True), not a scenario.
SUPPORTED_SCENARIOS = {
    "person_photo",
    "person_pose",
    "face_photo",
    "generated_person",
}



def _apply_blazer_edit_changes(prompt, garment_type, garment_style, use_garment_image):
    """
    person_photo (edit) route only, blazer fabric requests. Replaces the
    exact phrases listed in prompt_data.BLAZER_EDIT_REPLACEMENTS in memory (jacket
    length, the business tie colour, and the wedding shirt / bow tie /
    pocket square wording), then adds the TROUSERS line for business and
    wedding and the TIE line for business. Other garments and
    garment_image requests are returned unchanged.
    """
    if use_garment_image or garment_type != "blazer":
        return prompt
    for old_text, new_text in prompt_data.BLAZER_EDIT_REPLACEMENTS.get(garment_style, []):
        if old_text in prompt:
            prompt = prompt.replace(old_text, new_text, 1)
        else:
            logger.warning(
                "blazer edit: phrase not found in the edit prompt "
                "(style=%s): %.60s", garment_style, old_text,
            )
    if garment_style in prompt_data.BLAZER_TROUSER_STYLES:
        prompt = prompt.rstrip() + " " + prompt_data.BLAZER_TROUSER_LINE
    if garment_style == "business":
        prompt = prompt.rstrip() + " " + prompt_data.BLAZER_TIE_LINE
    return prompt


def _apply_local_edit_prompt(prompt, style, scenario):
    if scenario != "person_photo":
        return prompt
    return _apply_blazer_edit_changes(prompt, GARMENT_TYPE, style, False)

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
        use_spec_person_pose=True,
        use_short_own_model=True,
        edit_prompt_hook=_apply_local_edit_prompt,
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

