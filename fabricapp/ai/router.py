"""Routes a request to the correct garment prompt builder."""

from importlib import import_module
from .fabric_material import validate_fabric_type


SCENARIO_PERSON_PHOTO = "person_photo"
SCENARIO_PERSON_POSE = "person_pose"
SCENARIO_FACE_PHOTO = "face_photo"
SCENARIO_GENERATED_PERSON = "generated_person"
SCENARIO_POSE_REFERENCE = "pose_reference"


def detect_scenario(
    has_person_image, has_face_reference, pose=None, camera_view=None,
    use_pose_reference=False,
):
    """Select the generation route from already validated request inputs."""
    if use_pose_reference:
        return SCENARIO_POSE_REFERENCE
    if has_person_image:
        if pose or camera_view:
            return SCENARIO_PERSON_POSE
        return SCENARIO_PERSON_PHOTO
    if has_face_reference:
        return SCENARIO_FACE_PHOTO
    return SCENARIO_GENERATED_PERSON


IMPLEMENTED_GARMENT_TYPES = {
    "kurta",
    "kurti_pant",
    "pant",
    "saree",
    "shirt",
    "blazer",
}

GARMENT_STYLE_OPTIONS = {
    "blazer": ["business", "wedding", "casual"],
    "kurta": ["plain", "sherwani", "pathani", "jodhpuri"],
}

BUILDER_MODULES = {
    "kurta": "fabricapp.ai.kurta.builder",
    "kurti_pant": "fabricapp.ai.kurti_pant.builder",
    "pant": "fabricapp.ai.pant.builder",
    "saree": "fabricapp.ai.saree.builder",
    "shirt": "fabricapp.ai.shirt.builder",
    "blazer": "fabricapp.ai.blazer.builder",
}


class PromptRoutingError(Exception):
    """Raised when a request has no matching prompt builder."""


def _validate_builder_result(result, garment_type):
    if not isinstance(result, dict):
        raise PromptRoutingError(
            f"Builder for '{garment_type}' must return a prompt config."
        )

    prompt = result.get("prompt")
    seed = result.get("seed")
    guidance = result.get("guidance")

    if not isinstance(prompt, str) or not prompt.strip():
        raise PromptRoutingError(
            f"Builder for '{garment_type}' returned an empty prompt."
        )

    if seed is None or guidance is None:
        raise PromptRoutingError(
            f"Builder for '{garment_type}' must return seed and guidance."
        )

    return result


def build_prompt_config(
    *,
    scenario,
    garment_type,
    garment_style=None,
    use_garment_image=False,
    context,
    seed=None,
    guidance=None,
):
    """
    Ask the correct builder for a config shaped like:
    {"prompt": str, "seed": int, "guidance": float}

    Each garment builder owns its defaults and applies request overrides.
    """
    error = validate_fabric_type((context or {}).get("fabric_type", "unspecified"), garment_type, use_garment_image)
    if error:
        raise PromptRoutingError(error)
    if use_garment_image:
        module = import_module("fabricapp.ai.garment_image")
        builder = getattr(module, "build_prompt", None)
        if builder is None:
            raise PromptRoutingError(
                "The common garment-image builder is not available."
            )

        result = builder(
            scenario=scenario,
            context=context,
            seed=seed,
            guidance=guidance,
        )
        return _validate_builder_result(result, "garment_image")

    if garment_type not in IMPLEMENTED_GARMENT_TYPES:
        raise PromptRoutingError(
            f"No implemented builder for garment_type '{garment_type}'."
        )

    module_path = BUILDER_MODULES[garment_type]
    try:
        module = import_module(module_path)
    except ImportError as exc:
        raise PromptRoutingError(
            f"Could not load builder for garment_type '{garment_type}': {exc}"
        ) from exc

    # All garment packages must expose this same public function.
    builder = getattr(module, "build_prompt", None)
    if builder is None:
        raise PromptRoutingError(
            f"'{module_path}' must export build_prompt()."
        )

    result = builder(
        scenario=scenario,
        garment_type=garment_type,
        garment_style=garment_style,
        use_garment_image=use_garment_image,
        context=context,
        seed=seed,
        guidance=guidance,
    )
    return _validate_builder_result(result, garment_type)
