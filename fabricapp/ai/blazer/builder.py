"""Resolve Blazer attributes once for the initial and alternate prompts."""

from ..router import PromptRoutingError
from .settings import get_generation_settings
from .retry import VERSION, build_retry_prompt

GARMENT_TYPE = "blazer"
SUPPORTED_SCENARIOS = {"person_photo", "person_pose", "face_photo", "generated_person"}


def build_prompt(*, scenario, garment_type=None, garment_style=None,
                 use_garment_image=False, context=None, seed=None, guidance=None):
    if garment_type not in (None, GARMENT_TYPE):
        raise PromptRoutingError(f"Blazer builder cannot handle {garment_type!r}.")
    if scenario not in SUPPORTED_SCENARIOS:
        raise PromptRoutingError(f"Unsupported blazer scenario {scenario!r}.")
    if use_garment_image:
        from ..garment_image import build_prompt as build_garment_image_prompt
        return build_garment_image_prompt(
            scenario=scenario, context=context or {}, seed=seed, guidance=guidance,
        )
    request_context = context or {}
    prompt = build_retry_prompt(scenario, garment_style, request_context, compact=False)
    if not prompt:
        raise PromptRoutingError(f"Unsupported blazer style {garment_style!r}.")
    return {
        "prompt": prompt,
        "safety_fallback_prompt": build_retry_prompt(scenario, garment_style, request_context),
        "prompt_version": VERSION,
        **get_generation_settings(seed=seed, guidance=guidance),
    }
