"""Resolve Blazer attributes once for the initial and alternate prompts."""

from ..router import PromptRoutingError
from .settings import get_generation_settings
from .retry import VERSION, build_retry_prompt
from ..fabric_colour import measure_fabric_colours, has_single_colour_family
from .materials import validate_fabric_type

GARMENT_TYPE = "blazer"
SUPPORTED_SCENARIOS = {"person_photo", "person_pose", "face_photo", "generated_person"}


def build_prompt(*, scenario, garment_type=None, garment_style=None,
                 use_garment_image=False, context=None, seed=None, guidance=None):
    if garment_type not in (None, GARMENT_TYPE):
        raise PromptRoutingError(f"Blazer builder cannot handle {garment_type!r}.")
    if scenario not in SUPPORTED_SCENARIOS:
        raise PromptRoutingError(f"Unsupported blazer scenario {scenario!r}.")
    fabric_type = (context or {}).get("fabric_type", "unspecified")
    material_error = validate_fabric_type(fabric_type, GARMENT_TYPE, use_garment_image)
    if material_error:
        raise PromptRoutingError(material_error)
    if use_garment_image:
        from ..garment_image import build_prompt as build_garment_image_prompt
        return build_garment_image_prompt(
            scenario=scenario, context=context or {}, seed=seed, guidance=guidance,
        )
    request_context = dict(context or {})
    colour_profile = None
    if request_context.get("fabric_image") is not None:
        measured = measure_fabric_colours(
            request_context["fabric_image"],
            (request_context.get("options") or {}).get("fabric_crop_box"),
        )
        # Single-family swatches improved in paired tests. Multi-colour prints
        # remain experimental because live tests showed rejections/regressions.
        if has_single_colour_family(measured) or request_context.get("_colour_reference_experiment"):
            colour_profile = measured
            request_context["_fabric_colour_profile"] = colour_profile
    prompt = build_retry_prompt(scenario, garment_style, request_context, compact=False)
    if not prompt:
        raise PromptRoutingError(f"Unsupported blazer style {garment_style!r}.")
    if fabric_type != "unspecified":
        prompt_version = "blazer-material-v1-" + fabric_type
    elif colour_profile:
        prompt_version = "blazer-colour-v5" if has_single_colour_family(colour_profile) else "blazer-colour-experiment-v2"
    elif request_context.get("_lighting_experiment"):
        prompt_version = "blazer-lighting-experiment-v2"
    else:
        prompt_version = VERSION
    return {
        "prompt": prompt,
        "safety_fallback_prompt": build_retry_prompt(scenario, garment_style, request_context),
        "prompt_version": prompt_version,
        "fabric_type": fabric_type,
        **({"fabric_colour_reference": colour_profile} if colour_profile else {}),
        **get_generation_settings(seed=seed, guidance=guidance),
    }
