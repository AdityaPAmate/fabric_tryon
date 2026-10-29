"""A compact, fully clothed blazer composition for the single 3030 retry."""

from ..scenario_composer import (
    BACKGROUND_DESCRIPTIONS, _garment_text_for_pose, _is_child,
    _person_description, _short_background, _spec_person_pose_text, get_framing,
)
from . import prompts


VERSION = "blazer-retry-v2"


def build_retry_prompt(scenario, style, context):
    """Resolve the same outfit and references without repeating the long prompt."""
    spec = prompts.GARMENT_SPECS.get(("blazer", style))
    if spec is None:
        return None
    pose = context.get("pose")
    camera = context.get("camera_view")
    background = context.get("background")
    framing = get_framing(camera)
    parts = [
        "TASK: create one realistic clothing-catalogue photograph of one fully "
        "clothed person in an opaque blazer outfit. Image 1 supplies only the "
        "jacket fabric colours and pattern. ",
    ]
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
        else:
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
        parts.append("POSE: " + _spec_person_pose_text(
            pose, "blazer", style, context.get("garment_details") or [], camera
        ) + ". ")
    parts.append("OUTFIT: " + _garment_text_for_pose(spec["garment"], "blazer", pose))
    parts.append(
        "FABRIC: reproduce image 1's colours, pattern, motif scale and density "
        "on the entire jacket and sleeves, preserving hue and brightness. "
        "Keep the inner shirt opaque, covering the chest and torso. Trousers "
        "are opaque, full-length and plain solid, with the colour specified "
        "above. Shirt, trousers and accessories retain their specified solid "
        "colours, separate from the jacket pattern. "
    )
    if background:
        parts.append(_short_background(BACKGROUND_DESCRIPTIONS.get(background), pose=pose))
    elif scenario in ("person_photo", "person_pose"):
        source = "0" if scenario == "person_photo" else "2"
        parts.append("BACKGROUND: preserve the setting and lighting from image " + source + ". ")
    else:
        parts.append("BACKGROUND: a plain neutral studio with soft neutral lighting. ")
    note = (context.get("additional_style_note") or "").strip()
    if note:
        parts.append("STYLE NOTE: " + note.rstrip(".") + ". Retain the outfit coverage and selected attributes. ")
    parts.append(
        "FINAL: one person with natural anatomy, two arms and two legs, "
        "in the selected pose and framing, fully clothed in a realistic catalogue photograph. "
    )
    return "".join(parts)
