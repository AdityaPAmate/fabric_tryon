"""Shared Blazer constraints for the primary prompt and compact 3030 retry."""

from ..scenario_composer import (
    BACKGROUND_DESCRIPTIONS, _garment_text_for_pose, _is_child,
    _person_description, _short_background, _spec_person_pose_text, get_framing,
)
from . import prompts
from .framing import composition_rule
from .lighting import scene_and_lighting
from ..fabric_colour import colour_reference_prompt
from .materials import material_prompt


VERSION = "blazer-structured-v4"


def build_retry_prompt(scenario, style, context, *, compact=True):
    """Resolve the same outfit and references without repeating the long prompt."""
    spec = prompts.GARMENT_SPECS.get(("blazer", style))
    if spec is None:
        return None
    pose = context.get("pose")
    camera = context.get("camera_view")
    background = context.get("background")
    # A selected pose owns orientation; camera still owns close-up cropping.
    framing = get_framing(camera if not pose or camera == "close_up" else None)
    parts = [
        "TASK: create one realistic clothing-catalogue photograph of one fully "
        "clothed person in an opaque blazer outfit. Image 1 supplies only the "
        "jacket fabric colours and pattern. ",
    ]
    parts.append(colour_reference_prompt(context.get("_fabric_colour_profile")))
    parts.append(material_prompt(context.get("fabric_type", "unspecified")))
    composition = composition_rule(scenario, camera)
    parts.append(composition)
    if not compact:
        parts.append(
            "Resolve this as a single outfit: the jacket uses the supplied fabric, "
            "while the shirt and trousers follow their separate descriptions. "
            "Keep fabric colour, garment construction, identity and pose consistent "
            "throughout the photograph. "
        )
    if scenario == "person_photo":
        parts.append(
            "SUBJECT: edit the person in image 0. Preserve their face, hair, "
            "skin tone, apparent age, gender presentation, accessories, body "
            "build, pose and framing. Replace their clothing with the outfit below. "
        )
    else:
        parts.append("IMAGES: image 0 is a blank canvas setting the portrait frame. ")
        if scenario == "person_pose":
            parts.append(
                "SUBJECT: image 2 supplies the person's identity, face, hair, "
                "skin tone, apparent age, gender presentation, accessories and "
                "body proportions. Preserve these in the requested new pose. "
            )
        if scenario in ("face_photo", "generated_person"):
            parts.append("SUBJECT: " + _person_description(
                context.get("gender"), context.get("body_type")
            ) + ". ")
            build = {"slim": "slim", "trim": "athletic and toned", "plus": "visibly plus-size"}.get(
                context.get("body_type")
            )
            if build:
                parts.append("BODY BUILD: " + build + ", with comfortably fitted clothing. ")
            if _is_child(context.get("gender")):
                parts.append("Keep child-sized clothing and age-appropriate proportions. ")
            if scenario == "face_photo":
                parts.append(
                    "Image 2 supplies facial identity, skin tone and hairstyle; "
                    "preserve these and the apparent age. "
                )
        parts.append("FRAMING: " + framing["shot"] + ", " + framing["shown"] + ". ")
        pose_text = _spec_person_pose_text(
            pose, "blazer", style, context.get("garment_details") or [], camera
        )
        if camera == "close_up":
            pose_text = pose_text.replace(
                ", with the whole chair and both full legs and feet visible", ""
            )
        parts.append("POSE (follow the selected posture exactly): " + pose_text + ". ")
    if scenario in ("person_pose", "person_photo"):
        parts.append(
            "IDENTITY: retain the source shoulder, waist and hip widths and arm "
            "and leg thickness; keep the same body build. Replace source clothing "
            "with the complete selected outfit while retaining personal accessories. "
        )
    parts.append("OUTFIT: " + _garment_text_for_pose(spec["garment"], "blazer", pose))
    parts.append(
        "COVERAGE: an opaque inner shirt covers the chest and torso beneath the "
        "jacket, including when the casual jacket is open. Jacket sleeves reach "
        "the wrists, straight and unrolled. Trousers have side pockets and are "
        "opaque, full-length and plain solid in the specified colour. "
    )
    parts.append(
        "FABRIC: reproduce image 1's colours, pattern, motif scale and density "
        "on the entire jacket and sleeves, preserving hue, saturation, brightness "
        "and motif spacing. Use only the supplied colours and design. The inner "
        "shirt, trousers and any specified tie keep their solid colours; the jacket "
        "pattern stays exclusively on the jacket. Preserve personal accessories. "
    )
    # Internal evaluation only: live paired tests did not establish a reliable
    # colour improvement. The API serializer exposes no such request option.
    if context.get("_lighting_experiment"):
        parts.append(scene_and_lighting(scenario, background, pose))
    elif background:
        parts.append(_short_background(BACKGROUND_DESCRIPTIONS.get(background), pose=pose))
    elif scenario in ("person_photo", "person_pose"):
        source = "0" if scenario == "person_photo" else "2"
        parts.append("BACKGROUND: preserve the setting and lighting from image " + source + ". ")
    else:
        parts.append("BACKGROUND: a plain neutral studio with soft neutral lighting. ")
    if not background and pose == "cross_leg_chair_recline":
        parts.append("Include an upholstered armchair supporting the seated pose. ")
    if pose == "rail_wide_arm_side_look":
        parts.append("Include a stable hip-height ledge supporting both hands. ")
    note = (context.get("additional_style_note") or "").strip()
    if note:
        parts.append("STYLE NOTE: " + note.rstrip(".") + ". Retain the outfit coverage and selected attributes. ")
    parts.append(
        "FINAL: one person with natural anatomy, exactly two arms, two hands, "
        "two legs and two feet, showing only what fits the selected crop. "
        "Render natural fabric folds and shadows. Keep the person "
        "in the selected pose and framing, fully clothed in a realistic catalogue photograph. "
    )
    parts.append(composition)
    return "".join(parts)
