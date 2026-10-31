"""Public AI entry point used by the API view."""

from ..timing import timed_stage
from .cloudflare_engine import (
    CloudflareGenerationError,
    generate_tryon_image as _generate_with_engine,
)
from .pose_reference import get_pose_reference_path
from .router import PromptRoutingError, build_prompt_config
from .router import detect_scenario
from .fabric_material import validate_fabric_type


def generate_tryon_image(
    *,
    person_image=None,
    fabric_image=None,
    garment_image=None,
    garment_type=None,
    garment_style=None,
    fabric_type="unspecified",
    gender=None,
    body_type=None,
    face_choice=None,
    face_image=None,
    camera_view=None,
    background=None,
    additional_style_note=None,
    pose=None,
    garment_details=None,
    options=None,
    seed=None,
    guidance=None,
):
    """
    Coordinate scenario detection, prompt routing, and image generation.

    The selected garment builder supplies default seed/guidance values.
    Non-None request values override those defaults for this request only.
    """
    options = options or {}
    garment_details = garment_details or []
    use_garment_image = garment_image is not None
    material_error = validate_fabric_type(fabric_type, garment_type, use_garment_image)
    if material_error:
        raise CloudflareGenerationError(material_error)
    has_face_reference = bool(face_choice or face_image)

    pose_reference_path = None
    if (
        person_image is None
        and not use_garment_image
        and garment_type
        and pose
    ):
        pose_reference_path = get_pose_reference_path(garment_type, pose)

    scenario = detect_scenario(
        has_person_image=person_image is not None,
        has_face_reference=has_face_reference,
        pose=pose,
        camera_view=camera_view,
        use_pose_reference=pose_reference_path is not None,
    )

    context = {
        "person_image": person_image,
        "fabric_image": fabric_image,
        "garment_image": garment_image,
        "garment_type": garment_type,
        "garment_style": garment_style,
        "fabric_type": fabric_type,
        "gender": gender,
        "body_type": body_type,
        "face_choice": face_choice,
        "face_image": face_image,
        "camera_view": camera_view,
        "background": background,
        "additional_style_note": additional_style_note,
        "pose": pose,
        "garment_details": garment_details,
        "options": options,
        "use_face_reference": has_face_reference,
        "pose_reference_path": pose_reference_path,
    }

    try:
        with timed_stage("prompt_building"):
            prompt_config = build_prompt_config(
                scenario=scenario,
                garment_type=garment_type,
                garment_style=garment_style,
                use_garment_image=use_garment_image,
                context=context,
                seed=seed,
                guidance=guidance,
            )
    except PromptRoutingError as exc:
        raise CloudflareGenerationError(str(exc)) from exc

    # Target interface for the refactored engine:
    # it prepares images and calls the model, but does not build prompts.
    return _generate_with_engine(
        person_image=person_image,
        fabric_image=fabric_image,
        garment_image=garment_image,
        garment_type=garment_type,
        garment_style=garment_style,
        gender=gender,
        body_type=body_type,
        face_choice=face_choice,
        face_image=face_image,
        camera_view=camera_view,
        background=background,
        additional_style_note=additional_style_note,
        pose=pose,
        garment_details=garment_details,
        options=options,
        scenario=scenario,
        pose_reference_path=pose_reference_path,
        prompt_config=prompt_config,
    )
