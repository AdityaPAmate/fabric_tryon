"""Apply common fabric attributes without rewriting garment construction rules."""
from fabricapp.ai.fabric.fabric_colour import (
    measure_fabric_colours, has_single_colour_family, colour_reference_prompt,
    patterned_fabric_colour_prompt, SHIRT_COLOUR_PRIORITY,
)
from fabricapp.ai.fabric.fabric_material import validate_fabric_type, material_prompt, fabric_target
from fabricapp.ai.pipeline.router import PromptRoutingError


def apply_fabric_conditioning(config, context, garment_type, garment_style=None,
                              use_garment_image=False, legacy_colour_text="", *,
                              match_pattern_colours=False):
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
        crop = (context.get("options") or {}).get("fabric_crop_box")
        if match_pattern_colours:
            profile = measure_fabric_colours(source, crop, palette_size=24, min_coverage=.005)
        else:
            measured = measure_fabric_colours(source, crop)
            if garment_type == "shirt" or has_single_colour_family(measured) or context.get("_colour_reference_experiment"):
                profile = measured
    target = fabric_target(garment_type, garment_style, context.get("garment_details"), context.get("pose"))
    preserve_palette = bool(garment_type == "shirt" and profile and
                            not all(c["name"] == "deep orange-brown" for c in profile["colours"]))
    colour_text = (patterned_fabric_colour_prompt(profile, target) if match_pattern_colours and profile
                   else colour_reference_prompt(profile, target, preserve_palette=preserve_palette))
    prefix = colour_text + material_prompt(
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
            if garment_type == "shirt" and profile:
                result[key] += SHIRT_COLOUR_PRIORITY
    primary = config.get("prompt", "")
    fallback = config.get("safety_fallback_prompt", "")
    if garment_type == "shirt" and profile and primary and fallback.startswith(primary):
        result["safety_fallback_prompt"] = result["prompt"] + fallback[len(primary):]
    result["fabric_type"] = fabric_type
    if profile:
        result["fabric_colour_reference"] = profile
    result["prompt_version"] = (garment_type + "-material-v1-" + fabric_type
                                if fabric_type != "unspecified" else garment_type + "-colour-v1")
    if garment_type == "shirt" and profile:
        result["prompt_version"] += "-palette-v2"
    if "COLOUR PRIORITY:" in prefix:
        result["prompt_version"] += "-brown-v2"
    return result
