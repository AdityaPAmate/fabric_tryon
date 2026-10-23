"""Prompt adapter for requests that supply a ready-made garment image."""

from importlib import import_module

GARMENT_IMAGE_PROMPT = (
    "Edit image 0. Keep the same person/subject, face, skin tone, hairstyle, "
    "expression, hands, arms, background, and body pose from image 0 "
    "completely unchanged — sharp, fully in focus, not altered in any way. "
    "Replace whatever garment the subject in image 0 is currently wearing "
    "with the exact garment shown in image 1 — same cut, style, color, "
    "pattern, and length as image 1, fitted naturally to the subject's body "
    "and pose in image 0. Do not invent or alter any design element not "
    "visible in image 1. Generate realistic new shading, folds, and shadows "
    "consistent with the lighting in image 0. Result must look like one "
    "real, unedited photograph."
)

DEFAULT_SEED = 42
DEFAULT_GUIDANCE = 7.0


def build_prompt(*, scenario, context, seed=None, guidance=None):
    """Use garment-image input with the right edit or own-model scenario."""
    from .scenario_composer import build_prompt as compose_prompt

    context = context or {}
    config = compose_prompt(
        scenario=scenario,
        garment_type=None,
        garment_style=None,
        use_garment_image=True,
        gender=context.get("gender"),
        body_type=context.get("body_type"),
        camera_view=context.get("camera_view"),
        background=context.get("background"),
        additional_style_note=context.get("additional_style_note"),
        pose=context.get("pose"),
        garment_details=context.get("garment_details") or [],
        use_face_reference=context.get("use_face_reference", False),
    )
    if not config or not config.get("prompt"):
        return None

    return {
        **config,
        "seed": DEFAULT_SEED if seed is None else seed,
        "guidance": DEFAULT_GUIDANCE if guidance is None else guidance,
    }
