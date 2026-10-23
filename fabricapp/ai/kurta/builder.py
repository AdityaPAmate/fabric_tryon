"""Prompt entry point for kurta requests.

This package owns its prompt data, pose definitions, detail rules, and
generation settings. The shared scenario composer handles common assembly.
"""

from ..router import PromptRoutingError
from ..scenario_composer import build_prompt as _compose_prompt
from .settings import get_generation_settings
from . import prompts as prompt_data
import logging

logger = logging.getLogger("fabricapp")


GARMENT_TYPE = 'kurta'
# garment_image is an input mode (use_garment_image=True), not a scenario.
SUPPORTED_SCENARIOS = {
    "person_photo",
    "person_pose",
    "face_photo",
    "generated_person",
}



def _replace_phrases(prompt, pairs, label):
    """In-memory replace of exact phrases; a phrase not found is logged."""
    for old_text, new_text in pairs:
        if old_text in prompt:
            prompt = prompt.replace(old_text, new_text, 1)
        else:
            logger.warning("%s: phrase not found: %.70s", label, old_text)
    return prompt

def _apply_kurta_edit_changes(prompt, garment_type, garment_style, use_garment_image):
    """person_photo (edit) route: kurta length, two-hands lock, and trouser colour phrases."""
    if use_garment_image or garment_type != "kurta":
        return prompt
    pairs = [
        (
            "hands, arms, background, and body pose from image 0 completely unchanged",
            "background and body pose from image 0 completely unchanged, with exactly two arms and two hands in total and never a third or duplicate hand",
        ),
    ]
    if garment_style == "plain":
        pairs.append((prompt_data.KURTA_PLAIN_LENGTH_OLD, prompt_data.KURTA_PLAIN_LENGTH_NEW))
    pairs += prompt_data.KURTA_PANT_COLOUR_EDIT.get(garment_style, [])
    return _replace_phrases(prompt, pairs, "kurta edit")

def _kurta_edit_extra_lines(garment_type, garment_style, use_garment_image):
    """person_photo (edit) route: the short extra lines for kurta only."""
    if use_garment_image or garment_type != "kurta":
        return ""
    text = prompt_data.KURTA_EDIT_LIMBS_LINE
    if garment_style == "plain":
        text += prompt_data.KURTA_PLAIN_LENGTH_LINE
    if garment_style in prompt_data.KURTA_COLOURED_PANT_STYLES:
        text += prompt_data.KURTA_PANT_COLOUR_LINE
    return text

def _uses_kurta_white_pant(garment_type, garment_style, use_garment_image):
    """True for the kurta styles in prompt_data.KURTA_WHITE_PANT_STYLES (fabric swatch only)."""
    return (
        not use_garment_image
        and garment_type == "kurta"
        and garment_style in prompt_data.KURTA_WHITE_PANT_STYLES
    )

def _replace_kurta_pant_phrase(prompt, garment_type, garment_style, use_garment_image):
    """
    person_photo (edit) route only. The tested kurta/plain prompt in
    prompts.py lets the pajama be "white, off-white, or a solid shade
    picked from the kurta's own color palette". That exact phrase is
    replaced in memory (prompts.py is never edited), so the prompt does not
    contain two different instructions for the pajama colour.
    If the phrase is not found (prompts.py was edited), a warning is
    logged and the prompt is returned unchanged.
    """
    if not _uses_kurta_white_pant(garment_type, garment_style, use_garment_image):
        return prompt
    if prompt_data.KURTA_PANT_OLD_PHRASE not in prompt:
        logger.warning(
            "kurta white pant: old phrase not found in the edit prompt "
            "(garment=%s style=%s)", garment_type, garment_style,
        )
        return prompt
    return prompt.replace(prompt_data.KURTA_PANT_OLD_PHRASE, prompt_data.KURTA_PANT_NEW_PHRASE, 1)

def _kurta_white_pant_line(garment_type, garment_style, use_garment_image):
    """
    person_photo (edit) route only: the one-sentence white pajama rule for
    the kurta styles in prompt_data.KURTA_WHITE_PANT_STYLES. Empty string otherwise.
    """
    if _uses_kurta_white_pant(garment_type, garment_style, use_garment_image):
        return prompt_data.KURTA_PANT_WHITE_LINE
    return ""


def _apply_local_edit_prompt(prompt, style, scenario):
    if scenario != "person_photo":
        return prompt
    prompt = _apply_kurta_edit_changes(prompt, GARMENT_TYPE, style, False)
    prompt = _replace_kurta_pant_phrase(prompt, GARMENT_TYPE, style, False)
    prompt += _kurta_white_pant_line(GARMENT_TYPE, style, False)
    prompt += _kurta_edit_extra_lines(GARMENT_TYPE, style, False)
    return prompt

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
    result.update(get_generation_settings(seed=seed, guidance=guidance))
    return result
