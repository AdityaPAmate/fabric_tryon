"""Shared scenario composition for garment prompt packages.

The API router selects a garment builder. Garment packages own their edit
prompts, garment specifications, pose data, detail rules, and generation
settings. This module combines that local data with reusable scenario
composition and returns a prompt configuration; image generation happens
later in the engine.
"""

import logging
import sys
from importlib import import_module
from .backgrounds import BACKGROUND_DESCRIPTIONS
from .camera_data import get_framing, get_camera_view_instruction
from .garment_image import GARMENT_IMAGE_PROMPT
from .pose_registry import get_pose_sentence
from .detail_engine import apply_garment_details, MODE_EDIT, MODE_OWN
from .prompt_runtime_rules import POSE_PHRASE_REPLACEMENTS

logger = logging.getLogger("fabricapp")

SCENARIO_PERSON_PHOTO = "person_photo"
SCENARIO_PERSON_POSE = "person_pose"
SCENARIO_FACE_PHOTO = "face_photo"
SCENARIO_GENERATED_PERSON = "generated_person"
SCENARIO_POSE_REFERENCE = "pose_reference"

# Scenarios that start from a blank canvas and build a brand-new photo.
OWN_MODEL_SCENARIOS = (
    SCENARIO_GENERATED_PERSON,
    SCENARIO_FACE_PHOTO,
    SCENARIO_PERSON_POSE,
)

# Own-model scenarios that use the generic short prompt when the garment
# package opts into it.
OWN_MODEL_SPEC_SCENARIOS = (SCENARIO_FACE_PHOTO, SCENARIO_GENERATED_PERSON)
# Report 7: three hands (stated once, right after the POSE line).
OWN_MODEL_LIMBS_LINE = (
    "LIMBS: exactly two arms, two hands, two legs and two feet in total in "
    "the pose above — never a third hand, an extra arm or a duplicate limb. "
)

# Report 5: two bodies for two legs (seated pose).
SINGLE_PERSON_RULE = (
    "ONE PERSON: exactly one person, with one head, one torso and exactly "
    "two legs in total — never two bodies, a mirrored copy or a second "
    "person. "
)

# Report 6: body_type ignored when face_choice is sent (image 2 is a slim
# face photo and "copy exactly from image 2" wins over a short build hint).
BODY_LINES = {
    "plus": (
        "BODY BUILD (image 2 gives only the face and hair, never the body): "
        "the body is clearly PLUS-SIZE — a heavy, broad build with a full "
        "rounded belly, wide chest and shoulders, thick arms and thick "
        "thighs. The face keeps image 2's features and may look "
        "proportionally fuller. The garment is cut larger to fit this body. "
    ),
    "trim": (
        "BODY BUILD (image 2 gives only the face and hair, never the body): "
        "the body is clearly ATHLETIC and toned — broad shoulders, a "
        "V-shaped torso, defined arms and a flat stomach. The garment fits "
        "this body. "
    ),
}


def _body_line(body_type):
    return BODY_LINES.get(body_type, "")


def _short_background(description, pose=None):
    """
    Report 4 ("cinematic" image): short background text with plain catalog
    lighting. Used by garment packages that request short spec prompts.
    When pose == cross_leg_chair_recline a chair-retention note is added so
    the model does not seat the person on the bare floor of the new scene.
    """
    if not description:
        return ""
    chair_note = (
        "An upholstered armchair from the seated pose must be present in "
        "this setting; the person is seated in the chair, never on the "
        "bare ground or floor. "
        if pose == "cross_leg_chair_recline"
        else ""
    )
    return (
        "BACKGROUND: replace the whole area behind the person with this "
        "scene: " + description + ". " + chair_note + "The person is lit "
        "by plain, natural daylight with neutral white balance and no "
        "colour cast; it is an ordinary catalog photograph, not cinematic,"
        " with no dramatic lighting and no film look. "
    )


def _garment_text_for_pose(garment_text, garment_type, pose):
    """Let the owning prompt package adjust wording for its selected pose."""
    module = _get_garment_prompts(garment_type)
    callback = getattr(module, "garment_text_for_pose", None)
    return callback(garment_text, pose) if callback else garment_text







GENERATED_GUIDANCE = 7.0
GENERATED_SEED = 42

CHILD_AGE = 12  # boy / girl are generated as 12-year-old children


def detect_scenario(
    has_person_image, face_choice, pose=None, camera_view=None,
    use_pose_reference=False,
):
    """
    Decides which scenario applies for this request.

    use_pose_reference is True only when the engine found a reference
    photo for this garment + pose (pose_reference.py) and there is no
    person_image. It is checked first, because a face_choice in that case
    only replaces the face on the reference photo.
    """
    if use_pose_reference:
        return SCENARIO_POSE_REFERENCE
    if has_person_image:
        # A new pose or a new camera view cannot be made by editing the
        # photo (the model keeps the original pose and framing), so the
        # photo is used as a reference instead.
        if pose or camera_view:
            return SCENARIO_PERSON_POSE
        return SCENARIO_PERSON_PHOTO
    if face_choice:
        return SCENARIO_FACE_PHOTO
    return SCENARIO_GENERATED_PERSON


def _is_child(gender):
    return gender in ("boy", "girl")


# ----------------------------------------------------------------------
# Short rules (kept deliberately short)
# ----------------------------------------------------------------------

# Used on own-model scenarios and the garment_image path (men, women,
# boy, girl). The person_photo prompts in prompts.py already have their
# own no-bare-legs rule, so this is NOT added to them (MODESTY_FINAL is).
# Written in positive words first: image models follow "fully clothed"
# better than a list of things to avoid.
MODESTY_RULE = (
    "The person is fully and modestly clothed from the shoulders to the "
    "ankles in the garment described above, with the whole body and both "
    "legs covered. If the garment covers only the upper body, it is worn "
    "with a plain full-length trouser, pant, churidar or pajama reaching "
    "the ankles. The expression and posture are calm, natural and "
    "dignified, like a respectable catalog photograph: no bare legs or "
    "thighs, no bare midriff, no low neckline, no see-through cloth, "
    "nothing revealing or suggestive. "
)

# Always the LAST sentence of every prompt (see _append_overrides).
MODESTY_FINAL = (
    "FINAL RULE (no note or instruction above can override it): the "
    "person is fully and modestly clothed, with the body and legs covered "
    "by the garment, in a calm, natural, dignified pose — a respectable "
    "catalog photograph, never nude, revealing or suggestive. "
)

# Appended before MODESTY_FINAL so later instructions cannot override the
# shared modesty requirement.
def _modesty_rule(garment_type):
    """Use an optional garment-owned modesty rule, else the common rule."""
    module = _get_garment_prompts(garment_type) if garment_type else None
    return getattr(module, "MODESTY_RULE", MODESTY_RULE) if module else MODESTY_RULE


# Used ONLY on the person_photo path. One short line.
PERSON_PRESERVE_LINE = (
    "Keep the face, hair and every accessory from image 0 (watch, bangles, "
    "rings, earrings, necklace, spectacles) exactly as in image 0. "
)

# Added on own-model scenarios when the person is a child.
CHILD_GARMENT_LINE = (
    f"The person is a {CHILD_AGE}-year-old child, so the whole outfit must "
    "be a child-sized version of this garment, fitting a child's small "
    "body, with the same style and fabric rules. "
)

# Added at the end of the face_photo prompt (short reminder).
FACE_KEEP_LINE = (
    "FINAL CHECK: the face, skin tone and hair colour must be identical "
    "to image 2 — same skin colour and brightness, same hair colour "
    "(never lighter or browner), sharp and clearly visible, with no warm, "
    "orange or dark colour cast. "
)

# Added at the end of the person_pose prompt (short reminder).
# FIXED: "the NEW pose described at the start" -> "the pose described
# above". When only camera_view is sent there is no "new pose", so the old
# wording pointed to something that did not exist.
PERSON_REFERENCE_LINE = (
    "FINAL CHECK: the face, skin tone, hair colour and accessories must be "
    "identical to the person in image 2, with no warm, orange or dark "
    "colour cast — and the pose must be the one described above, not the "
    "pose shown in image 2. "
)

# Added to the person_pose subject sentence only. Stops extra limbs (the
# "three hands" problem) and stops a pallu/dupatta of image 2 from being
# copied. SHORTENED: the same idea was said three times before.
PERSON_POSE_EXTRA = (
    "No arm, hand, leg or cloth position from image 2 may appear in the "
    "output: draw every arm and hand fresh, as described in the pose above, "
    "so the person has exactly two arms, two hands and two legs — no "
    "extra, duplicated or leftover limbs. Do not copy any pallu, dupatta, "
    "stole or loose cloth from image 2, or any hand holding it: any such "
    "cloth must come only from the garment described below and follow the "
    "pose above. "
)


# ----------------------------------------------------------------------
# Pose handling
# ----------------------------------------------------------------------

def _own_model_pose_text(
    pose, garment_type=None, garment_style=None, garment_details=None,
    camera_view=None,
):
    """
    Pose wording for the own-model prompts. A pose can have its own
    wording per garment / style / detail (see pose_data.POSE_OVERRIDES).
    No pose requested -> the default pose of the camera view.
    """
    sentence = get_pose_sentence(pose, garment_type, garment_style, garment_details)
    if sentence and camera_view == "side" and pose == "pocket_walk":
        return (
            "walking at a relaxed, gentle pace viewed from a side angle, taking a small natural step "
            "with feet close together (not a wide stride, not running), exactly two arms and two hands in total, "
            "the left elbow bent with the hand resting on the hip, the right arm hanging relaxed beside the torso"
        )
    return sentence or get_framing(camera_view)["pose_default"]


def _apply_pose_to_tested_prompt(prompt, pose):
    """
    Old edit-mode path (person_photo + pose). No longer used by the
    engine (person_photo + pose now goes to person_pose), kept so the
    offline check script and any later experiment still work.
    Works on the in-memory string; prompts.py is never modified.
    Returns (new_prompt, number_of_phrases_replaced).
    """
    pose_sentence = get_pose_sentence(pose)
    if pose_sentence is None:
        return prompt, 0

    replaced = 0
    for old_text, new_text in POSE_PHRASE_REPLACEMENTS:
        if old_text in prompt:
            prompt = prompt.replace(old_text, new_text)
            replaced += 1

    intro = (
        "NEW POSE (this overrides any instruction to keep the original "
        "pose): the person is " + pose_sentence + ". "
    )
    start = "Edit image 0. "
    if prompt.startswith(start):
        prompt = start + intro + prompt[len(start):]
    else:
        prompt = intro + prompt
    return prompt, replaced


# ----------------------------------------------------------------------
# Background text (built here so lighting cannot tint the person)
# ----------------------------------------------------------------------

def _background_instruction(background):
    """Returns the background override text, or None if not requested."""
    if not background:
        return None
    description = BACKGROUND_DESCRIPTIONS.get(background)
    if description is None:
        return None
    return (
        "BACKGROUND OVERRIDE: this replaces any earlier background "
        "instruction (keep the original background, or a plain studio "
        "background). Replace the entire "
        "area behind the person with this scene: " + description + ". "
        "Keep the person, face, pose and garment exactly as specified. "
        "LIGHTING RULE: any warm sunset, dusk, lantern or golden colours "
        "belong ONLY to the background scene and sky. The person is lit "
        "by soft, bright, neutral white daylight with neutral white "
        "balance, as if photographed with a white softbox: NO orange, "
        "golden, pink or warm colour cast and no dark shadow on the face, "
        "skin, hair or clothes. Skin tone, hair colour and fabric colours "
        "must stay exactly as in the source images, never darker, never "
        "tanned, never tinted. "
    )


# ----------------------------------------------------------------------
# Helpers for the own-model scenarios
# ----------------------------------------------------------------------

def _gender_word(gender):
    return {"men": "man", "women": "woman", "boy": "boy", "girl": "girl"}.get(gender, "person")


def _build_word(body_type):
    return {"slim": "slim", "trim": "athletic, toned", "plus": "plus-size"}.get(body_type, "slim")


def _person_description(gender, body_type):
    """Who the model must generate. Children get a clear age and support body_type."""
    if _is_child(gender):
        build_desc = ""
        if body_type == "plus":
            build_desc = ", with a noticeably chubby, plus-size build"
        elif body_type in ("slim", "trim"):
            build_desc = ", with a slim build"
        return (
            f"a {CHILD_AGE}-year-old Indian {_gender_word(gender)}{build_desc} — clearly "
            "a child, with a child's soft rounded face, a short child's "
            "height and small child's body proportions; not a teenager and "
            "not an adult"
        )
    return f"a young, {_build_word(body_type)} Indian {_gender_word(gender)}"


def _subject_block(gender, body_type, pose_text, framing):
    """Describes the new person the model must generate (no reference)."""
    return (
        "SUBJECT SETUP: image 0 is only a blank, plain neutral canvas that "
        "sets the frame size — there is no person on it. Generate a "
        f"brand-new, realistic, {framing['shot']} photograph of "
        f"{_person_description(gender, body_type)}, with a natural, "
        "realistic, sharp face with clearly visible eyes, "
        "in the exact pose given in the POSE line above, on a plain neutral studio "
        "background (unless a different background is requested at the end "
        "of this prompt), "
        f"{framing['shown']}{framing['fill']}. "
    )


def _subject_block_with_face(gender, body_type, pose_text, framing):
    """Same as _subject_block, but image 2 is a reference photo of the face."""
    return (
        "SUBJECT SETUP: image 0 is only a blank, plain neutral canvas that "
        "sets the frame size — there is no person on it. Image 2 is a "
        "reference photo of a real person's face. Generate a brand-new, "
        f"realistic, {framing['shot'].upper()} photograph of this SAME person, "
        f"{_person_description(gender, body_type)}, "
        "in the exact pose given in the POSE line above, on a plain neutral studio "
        "background (unless a different background is requested at the end "
        "of this prompt), "
        f"{framing['shown']}. "
        "FACE AND HAIR MUST BE COPIED EXACTLY FROM IMAGE 2: same facial "
        "structure, eyes, eyebrows, nose, lips, same skin tone and "
        "brightness, same hair colour, hair length and hairstyle, and the "
        "same facial hair if any (if image 2 has jet-black hair, the "
        "output must have jet-black hair, not brown). The face must be "
        "evenly lit with soft, neutral white light — no warm or orange "
        "cast, no dark shadow — sharp, with clearly visible eyes. "
        + framing["output_rule_face"]
    )


def _subject_block_with_person(pose_text, framing, keep_background=True):
    """
    person_pose scenario: image 2 is the user's own person photo, used as
    a reference for WHO the person is and WHERE the person is.
    keep_background=True  -> the background of image 2 is kept (default);
                             the face follows the lighting of image 2.
    keep_background=False -> a plain studio background is used here, and
                             the BACKGROUND OVERRIDE at the end replaces it;
                             the face gets neutral white light.

    What is copied from image 2 (must match the TASK line in _task_line):
        face, hair, skin tone, age, body build, accessories,
        and (only when keep_background) the background.
    What is NOT copied: clothes, loose cloth, pose.
    """
    if keep_background:
        background_text = (
            "in the SAME place as image 2: keep the original background of "
            "image 2 — same location, objects, colours, lighting and depth "
            "of field — continued naturally to fill the new frame (a wall, "
            "ledge or chair that the pose above needs may be added)"
        )
        ignore_text = (
            "Copy nothing else from image 2: its clothes, any loose cloth "
            "and its pose are NOT copied"
        )
        face_light_text = (
            "The face is sharp, with clearly visible eyes, lit to match "
            "the natural lighting of image 2. "
        )
    else:
        background_text = (
            "on a plain neutral studio background (unless a different "
            "background is requested at the end of this prompt; a wall, "
            "ledge or chair that the pose above needs may be added)"
        )
        ignore_text = (
            "Copy nothing else from image 2: its clothes, any loose cloth, "
            "its pose and its background are NOT copied"
        )
        face_light_text = (
            "The face must be evenly lit with soft, neutral white light, "
            "sharp, with clearly visible eyes. "
        )

    return (
        "SUBJECT SETUP: image 0 is only a blank, plain neutral canvas that "
        "sets the frame size — there is no person on it. Image 2 is a "
        "photo of a real person. Generate a brand-new, realistic, "
        f"{framing['shot'].upper()} photograph of this SAME person, "
        f"in the exact pose given in the POSE line above, {background_text}, "
        f"{framing['shown']}. "
        "IDENTITY AND BODY PROPORTIONS: match the person in image 2 as "
        "closely as possible: same face, eyes, eyebrows, nose, lips, skin "
        "tone, hair colour and style, age, and accessories. Preserve the "
        "same body build and scale: keep the original shoulder, waist and "
        "hip widths, torso length, height-to-width ratio, and arm and leg "
        "thickness. Do not make the person slimmer, wider, taller, shorter, "
        "or more muscular. Change only the pose and outfit. "
        "The face should remain recognizably the same person. "
        "Keep every "
        "accessory worn in image 2 (watch, bangles, rings, earrings, "
        "necklace, spectacles) in the same place. "
        f"{ignore_text} — the pose "
        "described above is required, do not repeat the pose of image 2. "
        + PERSON_POSE_EXTRA
        + face_light_text
        + framing["output_rule_person"]
    )


FABRIC_RULES = (
    "Use only the exact colors and pattern shown in image 1 for the {target} "
    "fabric — same type (check, stripe, print, weave, or plain), same scale "
    "and proportions — do not invent, add, brighten, darken, or alter any "
    "color or design element not visible in image 1. The motifs must repeat "
    "as densely and closely spaced as they appear in image 1, with the same "
    "small amount of empty space between them — do not spread them further "
    "apart. "
)

BORDER_RULES = (
    "First examine image 1: if it has one uniform pattern, apply it evenly "
    "over the whole {target}. If it has two distinct zones — a main body "
    "pattern plus a separate, denser decorative border strip — reproduce "
    "BOTH: main pattern on the body of the {target}, and the border design "
    "(with its own colors and motifs, not blended into the main pattern) as "
    "a clearly visible accent band along the hem and sleeve cuffs, as a "
    "real garment made from this fabric would be tailored. "
)

CLOSING = (
    "Sleeves, where the garment has them, must be full-length down to the "
    "wrist, straight and unrolled, unless the garment description above "
    "says otherwise. Generate realistic shading, folds, and shadows. The "
    "result must look like one real, unedited photograph. "
)

GENERATED_GARMENT_IMAGE_BODY = (
    "Dress this new person in the exact garment shown in image 1 — same "
    "cut, style, color, pattern, and length as image 1 — fitted naturally "
    "to the body and pose. Do not invent or alter any design element not "
    "visible in image 1. If the garment in image 1 covers only the upper or "
    "lower body, complete the outfit with a plain, modest, coordinating "
    "garment. Generate realistic shading, folds, and shadows. The result "
    "must look like one real, unedited photograph. "
)


# ----------------------------------------------------------------------
# GARMENT_SPECS — one entry per garment (and style). Add new garments here.
# ----------------------------------------------------------------------

# Garment descriptions are read from each garment package at runtime.

def _get_garment_spec(garment_type, garment_style):
    """Read scenario garment wording from this garment's own prompts module."""
    module = _get_garment_prompts(garment_type)
    specs = getattr(module, "GARMENT_SPECS", {})
    styled_key = (garment_type, garment_style)
    default_key = (garment_type, "default")
    spec = specs.get(styled_key) or specs.get(default_key)
    if spec is None:
        return None
    return {**spec, "garment_type": garment_type}


def _get_garment_prompts(garment_type):
    return import_module(f".{garment_type}.prompts", package=__package__)


def _pose_line(pose_text):
    """
    The pose gets its OWN short sentence right after the TASK line, so it
    is not buried inside the long subject sentence (the face / background
    / lighting rules). The pose wording itself comes from pose_data.py.
    """
    return (
        "POSE (follow it exactly; after the garment it is the most "
        "important instruction): the person is " + pose_text + ". "
    )


def _task_line(scenario, garment_type, use_garment_image, keep_background=True):
    """
    First sentence of every own-model prompt: says WHAT garment is wanted
    and WHAT each image is, so the garment is not buried after hundreds of
    words about the person and the pose, and image 1 (a fabric swatch) is
    never mistaken for a garment or a person.

    FIXED: image 2 used to be called "identity only" here, while the
    subject block copies body build, accessories and the background from
    it too. The role now says exactly what is taken and what is not.
    """
    if use_garment_image:
        what = "the garment shown in image 1"
        image_1 = "image 1 = the garment to copy"
    else:
        prompts_module = _get_garment_prompts(garment_type) if garment_type else None
        what = getattr(prompts_module, "TASK_PHRASE", None)
        if not what:
            noun = garment_type.replace("_", " ") if garment_type else "garment"
            what = f"a {noun} made from the fabric in image 1"
        image_1 = (
            "image 1 = the FABRIC swatch (only its colors and pattern are "
            "used; it is not a garment shape)"
        )
    roles = ["image 0 = blank canvas (frame size only)", image_1]
    if scenario == SCENARIO_PERSON_POSE:
        if keep_background:
            roles.append(
                "image 2 = photo of the person (take the face, hair, skin "
                "tone, body build, accessories and the background; do NOT "
                "take the clothes or the pose)"
            )
        else:
            roles.append(
                "image 2 = photo of the person (take the face, hair, skin "
                "tone, body build and accessories; do NOT take the "
                "clothes, the pose or the background)"
            )
    elif scenario == SCENARIO_FACE_PHOTO:
        roles.append("image 2 = face reference")
    return (
        f"TASK: generate one realistic photograph of a person wearing {what}. "
        "IMAGES: " + "; ".join(roles) + ". "
    )


def _build_own_model_prompt(
    scenario, garment_type, garment_style, use_garment_image, gender,
    body_type, pose=None, camera_view=None, garment_details=None, background=None,
):
    """
    Builds the dedicated prompt used by generated_person, face_photo and
    person_pose.
    """
    pose_text = _own_model_pose_text(
        pose, garment_type, garment_style, garment_details, camera_view
    )
    framing = get_framing(camera_view)

    keep_background = not background

    if scenario == SCENARIO_FACE_PHOTO:
        subject = _subject_block_with_face(gender, body_type, pose_text, framing)
    elif scenario == SCENARIO_PERSON_POSE:
        subject = _subject_block_with_person(
            pose_text, framing, keep_background=keep_background
        )
    else:
        subject = _subject_block(gender, body_type, pose_text, framing)

    # NEW: the limbs rule is stated right after the POSE line when a pose is requested.
    pose_part = _pose_line(pose_text)
    if pose and getattr(_get_garment_prompts(garment_type), "POSE_LIMBS_RULE", False):
        pose_part += OWN_MODEL_LIMBS_LINE

    # The garment and the role of every image come FIRST.
    subject = (
        _task_line(scenario, garment_type, use_garment_image, keep_background)
        + pose_part
        + subject
    )

    if use_garment_image:
        prompt = subject + GENERATED_GARMENT_IMAGE_BODY
    else:
        spec = _get_garment_spec(garment_type, garment_style)
        if spec is None:
            return None

        target = spec["fabric_target"]
        # NEW (report 8): a back view hides every front detail.
        prompt = subject + "Dress this person in " + _garment_text_for_pose(
            spec["garment"], garment_type, pose
        )
        prompt += spec.get("color_note", "")
        prompt += FABRIC_RULES.format(target=target)
        if spec["border"]:
            prompt += BORDER_RULES.format(target=target)
        elif spec.get("border_rules"):
            prompt += spec["border_rules"]
        prompt += getattr(_get_garment_prompts(garment_type), "CLOSING", CLOSING)

    # person_pose has no gender field (the person comes from the photo).
    if _is_child(gender):
        prompt += CHILD_GARMENT_LINE
        if body_type == "plus":
            prompt += (
                "BODY BUILD: the child has a noticeably chubby, plus-size build with fuller "
                "cheeks, a rounded belly and thicker arms and legs, fitted in comfortably loose-fitting clothing. "
            )
    return prompt


def _build_base(
    scenario, garment_type, garment_style, use_garment_image, gender,
    body_type, pose=None, camera_view=None, garment_details=None, background=None,
):
    """Returns {"prompt","guidance","seed"} for the scenario, or None."""
    if scenario in OWN_MODEL_SCENARIOS:
        prompt = _build_own_model_prompt(
            scenario,
            garment_type,
            garment_style,
            use_garment_image,
            gender,
            body_type,
            pose=pose,
            camera_view=camera_view,
            garment_details=garment_details,
            background=background,
        )
        if prompt is None:
            return None
        return {"prompt": prompt, "guidance": GENERATED_GUIDANCE, "seed": GENERATED_SEED}

    # person_photo: start from the selected garment package's prompt data.
    if use_garment_image:
        return {
            "prompt": GARMENT_IMAGE_PROMPT,
            "guidance": 7.0,
            "seed": 42,
        }

    from importlib import import_module

    module = import_module(f".{garment_type}.prompts", package=__package__)
    garment_prompts = getattr(module, "GARMENT_PROMPTS", {})
    styles = garment_prompts.get(garment_type, {})
    base = styles.get(garment_style) or styles.get("default")
    if not base:
        return None
    return dict(base)  # copy — never modify the stored data




# CHANGED (report 5): SINGLE_PERSON_RULE added (two bodies for two legs).
PERSON_POSE_SPEC_RULES = (
    "POSE PRIORITY: Change the person's posture to exactly the pose above. "
    "Do not retain the posture in image 2. "
    "LIMBS: Do not copy arms, hands, legs or feet from image 2. Draw "
    "exactly two arms, two hands, two legs and two feet in the pose above; "
    "never add, duplicate or leave an extra limb. "
) + SINGLE_PERSON_RULE

PERSON_POSE_SPEC_IDENTITY = (
    "IDENTITY: Copy the person in image 2 exactly: the same face shape, "
    "eyes, eyebrows, nose, lips, skin tone, hair, age category, apparent "
    "gender presentation, accessories and natural body build. Do not turn "
    "a man or boy into a woman or girl, or a woman or girl into a man or "
    "boy. Keep the original shoulder, waist and hip widths, torso length, "
    "height-to-width ratio, and arm and leg thickness; do not slim or "
    "widen the person. Replace every source garment and any loose cloth "
    "completely, including shorts, trousers or jeans; do not copy their "
    "colour, print, cut or fabric. "
)

PERSON_POSE_KEEP_BACKGROUND = (
    "BACKGROUND: Keep the original place, objects, colours and lighting "
    "from image 2; extend it naturally and add a simple chair or low "
    "ledge only when the selected pose requires it. "
)


def _spec_person_pose_text(
    pose, garment_type, garment_style, garment_details, camera_view,
):
    """Resolve pose wording from the selected garment package."""
    module = import_module(f".{garment_type}.poses", package=__package__)
    resolver = getattr(module, "get_spec_pose_prompt", None)
    if resolver:
        sentence = resolver(pose, garment_style, garment_details)
        if sentence:
            return sentence
    return _own_model_pose_text(
        pose, garment_type, garment_style, garment_details, camera_view
    )


def _build_person_pose_spec_prompt(
    garment_type, garment_style, pose, camera_view=None, background=None,
    garment_details=None,
):
    """
    Build a short, priority-ordered prompt using the selected garment spec.
    """
    spec = _get_garment_spec(garment_type, garment_style)
    if spec is None:
        return None

    pose_text = _spec_person_pose_text(
        pose, garment_type, garment_style, garment_details, camera_view
    )
    framing = get_framing(camera_view)
    keep_background = not background
    target = spec["fabric_target"]

    # 1. Garment + role of every image, then the pose (highest priority).
    prompt = _task_line(
        SCENARIO_PERSON_POSE, garment_type, False, keep_background
    )
    prompt += _pose_line(pose_text)
    prompt += PERSON_POSE_SPEC_RULES

    # 2. Who the person is (identity and body build from image 2).
    prompt += (
        "SUBJECT: Generate one realistic " + framing["shot"]
        + " photograph of the same person in image 2, "
        + framing["shown"] + ". " + PERSON_POSE_SPEC_IDENTITY
    )

    # 3. The outfit (wording owned by GARMENT_SPECS; a back view hides the
    #    front details).
    prompt += "OUTFIT: Dress the person in " + _garment_text_for_pose(
        spec["garment"], garment_type, pose
    )
    prompt += spec.get("color_note", "")

    # 4. The fabric. Package-specific fabric boundaries come from its prompt
    #    module, while the image-role and output rules are shared.
    prompt += (
        "FABRIC: Use image 1 only as the " + target + " fabric reference. "
        "Apply its actual colours, print, motif size and density across "
        "the entire " + target + " (including the full body and both full-length sleeves all the way to the wrists), "
        "with its original hue, brightness and saturation. " + _fabric_forbidden_text(spec)
        + FABRIC_RULES.format(target=target)
    )
    if spec["border"]:
        prompt += BORDER_RULES.format(target=target)

    # 5. Background. A kept background is described here. CHANGED (report 4):
    #    a NEW background is now also written here, as a short text with
    #    plain catalog lighting (no "cinematic" look), and no longer at the
    #    end of the prompt by _append_overrides.
    if keep_background:
        prompt += PERSON_POSE_KEEP_BACKGROUND
    else:
        prompt += _short_background(BACKGROUND_DESCRIPTIONS.get(background), pose=pose)

    # 6. Closing. Holds the anchors used by garment-specific details.
    prompt += CLOSING
    return prompt


def _build_own_model_spec_prompt(
    scenario, garment_type, garment_style, gender, body_type, pose=None,
    camera_view=None, garment_details=None, background=None,
):
    """
    Build the shared short own-model prompt selected by a garment package.
    Order = importance: pose, limbs, one person, subject, body build,
    background, outfit, fabric, closing.
    Returns the prompt text, or None if the garment spec does not exist.
    """
    spec = _get_garment_spec(garment_type, garment_style)
    if spec is None:
        return None

    pose_text = _spec_person_pose_text(
        pose, garment_type, garment_style, garment_details, camera_view
    )
    framing = get_framing(camera_view)
    target = spec["fabric_target"]

    prompt = _task_line(scenario, garment_type, False)
    prompt += _pose_line(pose_text) + OWN_MODEL_LIMBS_LINE + SINGLE_PERSON_RULE

    if scenario == SCENARIO_FACE_PHOTO:
        prompt += (
            "SUBJECT: image 0 is only a blank canvas (frame size). Image 2 "
            "is a reference photo of a real person's face. Generate a "
            f"brand-new, realistic {framing['shot']} photograph of this SAME "
            f"person, {_person_description(gender, body_type)}, "
            f"{framing['shown']}{framing['fill']}. Copy the face and hair "
            "exactly from image 2: same facial structure, eyes, eyebrows, "
            "nose, lips, skin tone and brightness, hair colour and style, "
            "and facial hair if any (jet-black hair stays jet-black); the "
            "face is sharp and evenly lit. " + framing["output_rule_face"]
        )
        if not _is_child(gender):
            prompt += _body_line(body_type)
        elif body_type == "plus":
            prompt += (
                "BODY BUILD: the child has a noticeably chubby, plus-size build with fuller "
                "cheeks, a rounded belly and thicker arms and legs, while remaining clearly a 12-year-old child. "
            )
    else:
        prompt += (
            "SUBJECT: image 0 is only a blank canvas (frame size). Generate "
            f"a brand-new, realistic {framing['shot']} photograph of "
            f"{_person_description(gender, body_type)}, with a sharp, "
            f"natural face, {framing['shown']}{framing['fill']}. "
        )
        if _is_child(gender) and body_type == "plus":
            prompt += (
                "BODY BUILD: the child has a noticeably chubby, plus-size build with fuller "
                "cheeks, a rounded belly and thicker arms and legs, while remaining clearly "
                "a 12-year-old child. "
            )

    description = BACKGROUND_DESCRIPTIONS.get(background) if background else None
    if description:
        prompt += _short_background(description, pose=pose)
    else:
        prompt += "BACKGROUND: a plain neutral studio background. "

    prompt += "OUTFIT: Dress the person in " + _garment_text_for_pose(
        spec["garment"], garment_type, pose
    )
    prompt += spec.get("color_note", "")
    prompt += (
        "FABRIC: Use image 1 only as the " + target + " fabric reference, "
        "with its actual colours, print, motif size and density across the "
        "entire " + target + " (including the full body and both full-length sleeves all the way to the wrists). "
        + _fabric_forbidden_text(spec) + FABRIC_RULES.format(target=target)
    )
    if spec["border"]:
        prompt += BORDER_RULES.format(target=target)

    prompt += CLOSING  # holds the anchors used by garment-specific details
    if _is_child(gender):
        prompt += CHILD_GARMENT_LINE
    return prompt








def _fabric_forbidden_text(spec):
    """Use optional garment-owned wording; retain a neutral shared fallback."""
    module = _get_garment_prompts(spec.get("garment_type")) if spec.get("garment_type") else None
    callback = getattr(module, "fabric_forbidden_text", None) if module else None
    if callback:
        return callback(spec)
    return (
        "Do not use image 1's fabric, pattern or colour on the trousers "
        "or pajama, any shirt or tie, footwear, accessories, skin or "
        "background. "
    )




def _append_overrides(prompt, background, additional_style_note):
    """
    Adds background / style-note text at the very end, and then the final
    modesty rule as the LAST sentence, so no note can override it.
    (camera_view is NOT added here: it is part of the subject sentence,
    see camera_data.py.)
    """
    background_text = _background_instruction(background)
    if background_text:
        prompt += " " + background_text

    if additional_style_note:
        note = additional_style_note.strip().rstrip(".")
        prompt += (
            " USER STYLE NOTE (highest priority for style, color and fit "
            "details — apply it): " + note + ". "
            "Where this note differs from any garment or style wording "
            "above, follow the note, except for the person's face, skin "
            "tone, body shape and the final modesty rule. "
        )

    prompt += " " + MODESTY_FINAL
    return prompt


def build_prompt(
    scenario,
    garment_type=None,
    garment_style=None,
    use_garment_image=False,
    gender=None,
    body_type=None,
    camera_view=None,
    background=None,
    additional_style_note=None,
    pose=None,
    garment_details=None,
    use_face_reference=False,
    use_spec_person_pose=False,
    use_short_own_model=False,
    person_pose_hook=None,
    edit_prompt_hook=None,
):
    """
    Main function used by the engine. Returns
    {"prompt", "guidance", "seed"}, or None if no prompt exists for the
    given garment_type / garment_style.

    use_face_reference is used only by the pose_reference scenario: True
    when a face_choice was sent (image 2 = the face to put on the photo).
    """
    if scenario == SCENARIO_POSE_REFERENCE:
        # Saree pose-reference requests are fully handled by its package above.
        return None

    if scenario == SCENARIO_PERSON_POSE and not use_garment_image and person_pose_hook:
        special_config = person_pose_hook(
            sys.modules[__name__], scenario=scenario, garment_type=garment_type,
            garment_style=garment_style, gender=gender, body_type=body_type,
            pose=pose, camera_view=camera_view, background=background,
            additional_style_note=additional_style_note,
            garment_details=garment_details,
        )
        if special_config is not None:
            return special_config

    # The owning package opts into the shared short spec route when needed.
    if (
        scenario == SCENARIO_PERSON_POSE
        and use_spec_person_pose
        and not use_garment_image
    ):
        prompt = _build_person_pose_spec_prompt(
            garment_type, garment_style, pose, camera_view=camera_view,
            background=background, garment_details=garment_details,
        )
        if prompt is None:
            return None
        prompt = apply_garment_details(
            prompt, garment_type, garment_style, garment_details, MODE_OWN
        )
        base = {
            "prompt": _append_overrides(
                prompt, None, additional_style_note
            ),
            "guidance": GENERATED_GUIDANCE,
            "seed": GENERATED_SEED,
        }
        logger.info(
            "Prompt built: scenario=%s garment=%s/%s pose=%s camera_view=%s "
            "details=%s words=%s",
            scenario, garment_type, garment_style, pose, camera_view,
            garment_details, len(base["prompt"].split()),
        )
        logger.info("FINAL PROMPT: %s", base["prompt"])
        return base

    # The owning package opts into the shared short own-model route.
    if (
        scenario in OWN_MODEL_SPEC_SCENARIOS
        and use_short_own_model
        and not use_garment_image
    ):
        prompt = _build_own_model_spec_prompt(
            scenario, garment_type, garment_style, gender, body_type,
            pose=pose, camera_view=camera_view,
            garment_details=garment_details, background=background,
        )
        if prompt is None:
            return None
        prompt = apply_garment_details(
            prompt, garment_type, garment_style, garment_details, MODE_OWN
        )
        base = {
            "prompt": _append_overrides(
                prompt, None, additional_style_note
            ),
            "guidance": GENERATED_GUIDANCE,
            "seed": GENERATED_SEED,
        }
        logger.info(
            "Prompt built (own-model spec): scenario=%s garment=%s/%s pose=%s "
            "camera_view=%s background=%s details=%s words=%s",
            scenario, garment_type, garment_style, pose, camera_view,
            background, garment_details, len(base["prompt"].split()),
        )
        logger.info("FINAL PROMPT: %s", base["prompt"])
        return base

    base = _build_base(
        scenario, garment_type, garment_style, use_garment_image, gender,
        body_type, pose, camera_view, garment_details, background,
    )
    if base is None:
        return None

    prompt = base["prompt"]
    replaced = 0
    # Old edit-mode pose path (only if someone calls person_photo + pose
    # directly; the engine routes that case to person_pose instead).
    if scenario == SCENARIO_PERSON_PHOTO and pose:
        prompt, replaced = _apply_pose_to_tested_prompt(prompt, pose)

    # Movable garment parts (sleeves / tuck / dupatta), defaults included.
    if not use_garment_image:
        mode = MODE_EDIT if scenario == SCENARIO_PERSON_PHOTO else MODE_OWN
        prompt = apply_garment_details(
            prompt, garment_type, garment_style, garment_details, mode
        )

    prompt = prompt.rstrip() + " "

    if scenario == SCENARIO_PERSON_PHOTO:
        # The owning builder applies any garment-specific edit constraints.
        if edit_prompt_hook and not use_garment_image:
            prompt = edit_prompt_hook(prompt, garment_style, scenario)
        # The prompts in prompts.py already forbid bare legs. Only one short line added.
        prompt += PERSON_PRESERVE_LINE
        if use_garment_image:
            # GARMENT_IMAGE_PROMPT has no leg rule, so add the modesty rule.
            prompt += _modesty_rule(garment_type)
    else:
        # Own-model scenarios: modesty rule that fits the garment.
        prompt += _modesty_rule(garment_type)
        if scenario == SCENARIO_FACE_PHOTO:
            prompt += FACE_KEEP_LINE
        elif scenario == SCENARIO_PERSON_POSE:
            prompt += PERSON_REFERENCE_LINE

    # Background, style note, then MODESTY_FINAL as the last sentence.
    base["prompt"] = _append_overrides(prompt, background, additional_style_note)
    logger.info(
        "Prompt built: scenario=%s pose=%s camera_view=%s details=%s "
        "pose_phrases_replaced=%s words=%s",
        scenario, pose, camera_view, garment_details, replaced,
        len(base["prompt"].split()),
    )
    logger.info("FINAL PROMPT: %s", base["prompt"])
    return base

