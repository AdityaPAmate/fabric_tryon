"""Apply common fabric attributes without rewriting garment construction rules."""
from .fabric_colour import measure_fabric_colours, has_single_colour_family, colour_reference_prompt
from .fabric_material import validate_fabric_type, material_prompt, fabric_target
from .router import PromptRoutingError


def apply_fabric_conditioning(config, context, garment_type, garment_style=None,
                              use_garment_image=False, legacy_colour_text=""):
    context = context or {}
    fabric_type = context.get("fabric_type", "unspecified")
    error = validate_fabric_type(fabric_type, garment_type, use_garment_image)
    if error:
        raise PromptRoutingError(error)
    if use_garment_image:
        return config
    profile = None
    source = context.get("fabric_image")
    if source is not None:
        measured = measure_fabric_colours(source, (context.get("options") or {}).get("fabric_crop_box"))
        if has_single_colour_family(measured) or context.get("_colour_reference_experiment"):
            profile = measured
    target = fabric_target(garment_type, garment_style, context.get("garment_details"), context.get("pose"))
    prefix = colour_reference_prompt(profile, target) + material_prompt(
        fabric_type, garment_type, garment_style, context.get("garment_details"), context.get("pose"))
    if not prefix:
        return config
    result = dict(config)
    for key in ("prompt", "safety_fallback_prompt"):
        if result.get(key):
            original = result[key]
            if profile and legacy_colour_text:
                original = original.replace(legacy_colour_text, "", 1)
            result[key] = prefix + original
    result["fabric_type"] = fabric_type
    if profile:
        result["fabric_colour_reference"] = profile
    result["prompt_version"] = (garment_type + "-material-v1-" + fabric_type
                                if fabric_type != "unspecified" else garment_type + "-colour-v1")
    return result
