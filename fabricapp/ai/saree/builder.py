"""
Saree route: prompt builder (logic only; wording is in texts.py, pose and
pallu data are in poses.py).

Two steps, always:
    1. RESOLVE: Python decides every known condition (pose, pallu,
       camera, background, lighting, face, body build, style note) and
       produces ONE final text per requirement.
    2. COMPOSE: the resolved texts are joined in a fixed order.

Scenarios handled here (names are the same strings prompt_builder.py uses;
they are repeated here so this package never imports prompt_builder.py):
    generated_person  no person photo, no face
    face_photo        no person photo, a predefined face (image 2)
    person_pose       person photo (image 2) + a pose and/or a camera_view
    pose_reference    a reference PHOTO of the pose is edited (image 0)

Not handled here (returns None, prompt_builder.py keeps its old path):
    person_photo      plain edit of the uploaded photo, no pose/camera_view

Public entry point: build_saree_prompt().
"""

import logging

from ..camera_data import get_framing
from ..prompts import BACKGROUND_DESCRIPTIONS, get_camera_view_instruction
from . import texts as T
from .poses import get_pose_parts

logger = logging.getLogger("fabricapp")

SCENARIO_PERSON_POSE = "person_pose"
SCENARIO_FACE_PHOTO = "face_photo"
SCENARIO_GENERATED_PERSON = "generated_person"
SCENARIO_POSE_REFERENCE = "pose_reference"

OWN_MODEL_SCENARIOS = (
    SCENARIO_GENERATED_PERSON,
    SCENARIO_FACE_PHOTO,
    SCENARIO_PERSON_POSE,
)

# A saree is worn by a woman or a girl.
UNSUPPORTED_GENDERS = ("men", "boy")

GUIDANCE = 7.0
SEED = 42
CHILD_AGE = 12

# Fixed order of the final prompt. The final modesty rule is always last.
OWN_MODEL_ORDER = (
    "task", "images", "pose", "pallu", "limbs", "subject", "body",
    "garment", "fabric", "border", "camera", "background", "lighting",
    "realism", "style", "final",
)

REFERENCE_ORDER = (
    "task", "images", "keep", "camera", "change", "fabric", "border",
    "extras", "face", "background", "lighting", "realism", "style",
    "final",
)

# Extra KEEP-style rules that belong to ONE reference photo (by pose name).
# A pose without an entry gets REF_EXTRAS_DEFAULT.
REF_EXTRAS_DEFAULT = (T.REF_BLOUSE,)
REF_EXTRAS_BY_POSE = {
    "pallu_on_head": (T.REF_BLOUSE, T.REF_RIGHT_SIDE),
}


# ----------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------

def _join(resolved, order):
    return " ".join(
        resolved[key].strip() for key in order if resolved.get(key)
    ) + " "


def _clean_note(note):
    return (note or "").strip().rstrip(".")


def _capitalize(text):
    return text[:1].upper() + text[1:] if text else text


def _person_description(gender, body_type):
    """Who is generated (generated_person / face_photo)."""
    if gender == "girl":
        build = ""
        if body_type == "plus":
            build = ", with a noticeably chubby, plus-size build"
        elif body_type in ("slim", "trim"):
            build = ", with a slim build"
        return (
            f"a {CHILD_AGE}-year-old Indian girl{build} — clearly a child, "
            "with a child's soft rounded face, a short child's height and "
            "small child's body proportions; not a teenager and not an adult"
        )
    build = {"slim": "slim", "trim": "athletic, toned", "plus": "plus-size"}.get(
        body_type, "slim"
    )
    return f"a young, {build} Indian woman"


def _body_text(gender, body_type, is_face):
    """BODY BUILD line (empty for slim / not sent)."""
    if gender == "girl":
        return T.BODY_CHILD_PLUS if body_type == "plus" else ""
    text = {"plus": T.BODY_PLUS, "trim": T.BODY_TRIM}.get(body_type, "")
    if text and is_face:
        text = T.BODY_FACE_NOTE + text
    return text


def _garment_text(gender, close_up):
    text = T.GARMENT_CLOSE if close_up else T.GARMENT_FULL
    if gender == "girl":
        text += " " + T.CHILD_GARMENT_LINE.format(age=CHILD_AGE)
    return text


def _framing(camera_view, pose):
    """
    With a pose, the POSE owns the body direction, so camera_view "front"
    and "side" would contradict it ("facing the camera directly" against a
    back view). Only "close_up" (a framing change) is kept next to a pose.
    """
    effective = camera_view
    if pose and camera_view in ("front", "side"):
        logger.info(
            "Saree: camera_view '%s' ignored because pose '%s' owns the "
            "body direction", camera_view, pose,
        )
        effective = None
    return get_framing(effective)


# ----------------------------------------------------------------------
# generated_person / face_photo / person_pose
# ----------------------------------------------------------------------

def _build_own_model(
    scenario, gender, body_type, pose, camera_view, background,
    additional_style_note,
):
    if gender in UNSUPPORTED_GENDERS:
        logger.error(
            "Saree route: gender '%s' is not supported (saree is for "
            "women / girl)", gender,
        )
        return None

    is_face = scenario == SCENARIO_FACE_PHOTO
    is_person = scenario == SCENARIO_PERSON_POSE
    close_up = camera_view == "close_up"

    framing = _framing(camera_view, pose)
    parts = get_pose_parts(pose, camera_view)

    description = BACKGROUND_DESCRIPTIONS.get(background) if background else None
    new_background = bool(description)

    # IMAGES + SUBJECT
    if is_face:
        images = T.IMAGES_FACE
        subject = T.SUBJECT_FACE.format(
            person=_person_description(gender, body_type)
        )
    elif is_person:
        images = T.IMAGES_PERSON_NEW_BG if new_background else T.IMAGES_PERSON_KEEP_BG
        subject = T.SUBJECT_PERSON
    else:
        images = T.IMAGES_GENERATED
        subject = T.SUBJECT_GENERATED.format(
            person=_person_description(gender, body_type)
        )

    # CAMERA (+ "do not copy the crop of image 2" when image 2 exists)
    camera = T.CAMERA.format(
        shot=framing["shot"], shown=framing["shown"], fill=framing["fill"]
    )
    if is_face:
        camera += " " + framing["output_rule_face"].strip()
    elif is_person:
        camera += " " + framing["output_rule_person"].strip()

    # BACKGROUND: ONE of three texts, then the prop the pose needs.
    if new_background:
        background_text = T.BACKGROUND_SCENE.format(description=description)
    elif is_person:
        background_text = T.BACKGROUND_KEEP_PERSON
    else:
        background_text = T.BACKGROUND_DEFAULT
    if parts["prop"]:
        background_text += " " + parts["prop"]

    # LIGHTING: follows image 2 only while image 2's background is kept.
    lighting = (
        T.LIGHTING_MATCH_PHOTO
        if is_person and not new_background
        else T.LIGHTING_NEUTRAL
    )

    limbs = T.LIMBS
    if parts["one_person"]:
        limbs += " " + T.ONE_PERSON

    note = _clean_note(additional_style_note)

    resolved = {
        "task": T.TASK,
        "images": images,
        "pose": T.POSE.format(pose_text=parts["pose_text"]),
        "pallu": T.PALLU.format(pallu_text=_capitalize(parts["pallu_text"])),
        "limbs": limbs,
        "subject": subject,
        "body": "" if is_person else _body_text(gender, body_type, is_face),
        "garment": _garment_text(gender, close_up),
        "fabric": T.FABRIC_RULES,
        "border": T.BORDER_RULES,
        "camera": camera,
        "background": background_text,
        "lighting": lighting,
        "realism": T.REALISM,
        "style": T.STYLE_NOTE.format(note=note) if note else "",
        "final": T.MODESTY_FINAL_CLOSE if close_up else T.MODESTY_FINAL_FULL,
    }
    prompt = _join(resolved, OWN_MODEL_ORDER)

    logger.info(
        "Saree prompt built: version=%s scenario=%s pose=%s camera_view=%s "
        "background=%s gender=%s body_type=%s words=%s",
        T.PROMPT_VERSION, scenario, pose, camera_view, background, gender,
        body_type, len(prompt.split()),
    )
    logger.info("FINAL PROMPT: %s", prompt)
    return {"prompt": prompt, "guidance": GUIDANCE, "seed": SEED}


# ----------------------------------------------------------------------
# pose_reference (a photo is edited; only the fabric changes)
# ----------------------------------------------------------------------

def _build_pose_reference(
    pose, use_face_reference, background, camera_view, additional_style_note,
    gender, body_type,
):
    if gender or body_type:
        logger.warning(
            "Saree reference route: gender/body_type are NOT applied, the "
            "person comes from the reference photo (pose=%s)", pose,
        )

    description = BACKGROUND_DESCRIPTIONS.get(background) if background else None
    camera_text = get_camera_view_instruction(camera_view)
    use_camera = bool(camera_text)

    # What stays exactly as in the photo. A piece that is replaced by the
    # FACE / BACKGROUND line is left out, so KEEP never contradicts them.
    kept = [T.REF_KEPT_BASE_CAMERA if use_camera else T.REF_KEPT_BASE]
    if not use_face_reference:
        kept.append(T.REF_KEPT_FACE)
    if not description:
        kept.append(T.REF_KEPT_SCENE_CAMERA if use_camera else T.REF_KEPT_SCENE)

    extras = REF_EXTRAS_BY_POSE.get(pose, REF_EXTRAS_DEFAULT)
    note = _clean_note(additional_style_note)

    resolved = {
        "task": T.REF_TASK,
        "images": T.REF_IMAGES_FACE if use_face_reference else T.REF_IMAGES,
        "keep": T.REF_KEEP.format(kept=", ".join(kept)),
        "camera": (
            T.REF_CAMERA.format(instruction=camera_text) if use_camera else ""
        ),
        "change": T.REF_CHANGE,
        "fabric": T.FABRIC_RULES,
        "border": T.REF_BORDER_RULES,
        "extras": " ".join(extras),
        "face": T.REF_FACE if use_face_reference else "",
        "background": (
            T.REF_BACKGROUND.format(description=description) if description else ""
        ),
        # Lighting is changed only when the background is changed.
        "lighting": T.LIGHTING_NEUTRAL if description else "",
        "realism": T.REALISM,
        "style": T.STYLE_NOTE.format(note=note) if note else "",
        "final": T.MODESTY_FINAL_FULL,
    }
    prompt = _join(resolved, REFERENCE_ORDER)

    logger.info(
        "Saree reference prompt built: version=%s pose=%s face_reference=%s "
        "camera_view=%s background=%s words=%s",
        T.REFERENCE_PROMPT_VERSION, pose, use_face_reference, camera_view,
        background, len(prompt.split()),
    )
    logger.info("FINAL PROMPT: %s", prompt)
    return {"prompt": prompt, "guidance": GUIDANCE, "seed": SEED}


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------

def build_saree_prompt(
    scenario,
    gender=None,
    body_type=None,
    pose=None,
    camera_view=None,
    background=None,
    additional_style_note=None,
    use_face_reference=False,
):
    """
    Returns {"prompt", "guidance", "seed"} for a saree request made from a
    fabric swatch, or None when this route does not handle the scenario
    (person_photo) or the request is not valid for a saree. A None result
    means: use the old path (person_photo) / fail (invalid gender).
    """
    if scenario == SCENARIO_POSE_REFERENCE:
        return _build_pose_reference(
            pose, use_face_reference, background, camera_view,
            additional_style_note, gender, body_type,
        )
    if scenario in OWN_MODEL_SCENARIOS:
        return _build_own_model(
            scenario, gender, body_type, pose, camera_view, background,
            additional_style_note,
        )
    return None