"""
Stage: Prompt builder.
Single place that decides WHICH prompt is used for a request, based on
the situation (scenario). The engine only calls build_prompt() and
never needs to know how prompts are made.

Scenarios:
    person_photo      -> user uploaded a person photo and NO pose and NO
                         camera_view. The prompts from prompts.py
                         (GARMENT_PROMPTS) are used, plus the movable parts
                         (garment details) and ONE short preserve line at
                         the end.
    person_pose       -> user uploaded a person photo AND a pose and/or a
                         camera_view. image 0 = blank canvas, image 2 =
                         the person photo as a REFERENCE (face, body,
                         accessories, and - when no background is asked -
                         the background come from it).
    face_photo        -> no person photo, but a predefined face was
                         chosen. image 0 = blank canvas, image 2 = face
                         reference.
    generated_person  -> no person photo and no face. The model makes the
                         face. Dedicated own-model prompt from GARMENT_SPECS.

Movable parts (variables):
    pose            -> pose_data.py (text) AND, when a pose image exists, a
                       pose GUIDE (flat grey silhouette made by
                       pose_images.py) sent in image slot `pose_slot`.
                       The guide has no face / clothes / fabric / background,
                       so only the pose can be taken from it.
    camera_view     -> camera_data.py (framing text)
    garment_details -> garment_details.py (sleeves, tuck, dupatta)
    background      -> BACKGROUND_DESCRIPTIONS in prompts.py
    style note      -> additional_style_note

CONSISTENCY RULES kept in this file (do not break them when editing):
    1. One instruction = one place. A pose, a pallu arrangement, a
       lighting rule or a background rule is stated once, and no other
       sentence may contradict it.
    2. Lighting: when the background of image 2 is kept, the face follows
       the lighting of image 2; only when a new background or a studio
       background is used, the face gets neutral white light.
    3. The pose text decides how the pallu hangs. The silhouette decides it
       only when the pose text does not say (customer's own pose_image).
    4. The silhouette gives the POSE only, never body build or age.
    5. MODESTY_FINAL is always the LAST sentence of every prompt, after the
       style note, so no note can override it.

IMPORTANT: keep prompts SHORT. Very long prompts make the model ignore
parts of them. Do not append long text to the tested prompts.

The background text is built HERE (not in prompts.py) so that the
lighting rule can protect the face, hair and skin tone from getting a
warm/dark colour cast from the background scene.
"""

import logging

from .prompts import (
    GARMENT_STYLE_OPTIONS,
    GARMENT_IMAGE_PROMPT,
    GARMENT_IMAGE_GUIDANCE,
    GARMENT_IMAGE_SEED,
    BACKGROUND_DESCRIPTIONS,
    get_prompt_config,
)
from .pose_data import (
    POSE_PHRASE_REPLACEMENTS,
    get_pose_sentence,
)
from .pose_images import POSE_TEXT_WITH_GUIDE
from .camera_data import get_framing
from .garment_details import apply_garment_details, MODE_EDIT, MODE_OWN

logger = logging.getLogger("fabricapp")

SCENARIO_PERSON_PHOTO = "person_photo"
SCENARIO_PERSON_POSE = "person_pose"
SCENARIO_FACE_PHOTO = "face_photo"
SCENARIO_GENERATED_PERSON = "generated_person"

# Scenarios that start from a blank canvas and build a brand-new photo.
OWN_MODEL_SCENARIOS = (
    SCENARIO_GENERATED_PERSON,
    SCENARIO_FACE_PHOTO,
    SCENARIO_PERSON_POSE,
)

GENERATED_GUIDANCE = 7.0
GENERATED_SEED = 42

CHILD_AGE = 12  # boy / girl are generated as 12-year-old children


def detect_scenario(has_person_image, face_choice, pose=None, camera_view=None):
    """Decides which scenario applies for this request."""
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
# boy, girl). The tested person_photo prompts already have their own
# no-bare-legs rule, so this is NOT added to them (MODESTY_FINAL is).
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

# Saree version: the generic rule above mentions trouser / churidar / pajama,
# which pushes the model toward a salwar suit instead of a saree. So the
# saree gets its own wording without any trouser words.
MODESTY_RULE_SAREE = (
    "The person is fully and modestly dressed in the saree and blouse: the "
    "saree covers the body from the shoulder to the ankles and the drape "
    "covers the waist, so nothing is bare except the face, hands and feet. "
    "The expression and posture are calm, natural and dignified, like a "
    "respectable catalog photograph. "
)


def _modesty_rule(garment_type):
    """Modesty wording that fits the garment (saree has its own)."""
    return MODESTY_RULE_SAREE if garment_type == "saree" else MODESTY_RULE


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
PERSON_REFERENCE_LINE = (
    "FINAL CHECK: the face, skin tone, hair colour and accessories must be "
    "identical to the person in image 2, with no warm, orange or dark "
    "colour cast — and the pose must be the NEW pose described at the "
    "start, not the pose shown in image 2. "
)

# Added to the person_pose subject sentence only. Stops extra limbs and
# stops a pallu/dupatta of image 2 from being copied.
PERSON_POSE_EXTRA = (
    "Image 2 shows the OLD pose only. No arm, hand, leg or cloth position "
    "from image 2 may appear in the output: draw every arm and hand fresh, "
    "exactly as described in the new pose above, so the person has exactly "
    "two arms, two hands and two legs — no extra, duplicated, merged or "
    "leftover limbs. Do not copy any pallu, dupatta, stole or loose cloth "
    "hanging over the shoulder, arm or hand in image 2: any such cloth must "
    "come only from the garment described below and must follow the new "
    "pose. "
)


# ----------------------------------------------------------------------
# Pose handling
# ----------------------------------------------------------------------

def _pose_guide_phrase(slot, garment_type=None):
    """
    Short phrase added after a written pose sentence when a silhouette is
    sent too. It does NOT talk about the pallu: for a named pose the pose
    text already says how the pallu hangs (rule 3 in the file docstring).
    garment_type is accepted only so older calls keep working.
    """
    return f"matching the body outline of the grey silhouette in image {slot}"


def _own_model_pose_text(
    pose, garment_type=None, garment_style=None, garment_details=None,
    camera_view=None, pose_slot=None,
):
    """
    Pose wording for the own-model prompts.
    No pose guide -> the text from pose_data.py (can differ per garment /
    style / detail, see pose_data.POSE_OVERRIDES); no pose requested -> the
    default pose of the camera view.
    Pose guide sent in slot `pose_slot` -> the same text (if the pose has
    one and POSE_TEXT_WITH_GUIDE is True) plus a phrase pointing at the
    silhouette; for a customer's own pose_image there is no text, so only
    the silhouette phrase is used (and then the silhouette also decides how
    the saree pallu hangs).
    """
    text = get_pose_sentence(pose, garment_type, garment_style, garment_details)
    if not pose_slot:
        return text or get_framing(camera_view)["pose_default"]

    if text and POSE_TEXT_WITH_GUIDE:
        return f"{text}, {_pose_guide_phrase(pose_slot, garment_type)}"
    return (
        f"posed exactly like the grey silhouette in image {pose_slot} — the "
        "same body direction, head direction and the same placement of both "
        "arms and both legs"
        + (", with the pallu following the hanging shape of that silhouette"
           if garment_type == "saree" else "")
    )


def _pose_guide_rule(slot, garment_type):
    """Short rule added after the subject sentence when a pose guide is sent."""
    rule = (
        f"POSE GUIDE: image {slot} is only a flat grey SILHOUETTE of the "
        "target pose on a white background. It is not a photo: it has no "
        "person, face, clothes, colours or background to copy. Draw the "
        "person so that the body fills this outline — the same body "
        "direction, the same head position, the same placement of both arms "
        "and both legs. Do not draw the grey colour, the white background "
        "or the silhouette itself. The person has exactly two arms, two "
        "hands and two legs. "
        "The silhouette gives only the pose: the body build, age and "
        "proportions come from the person described or shown, never from "
        "the grey outline. "
        "The framing of the output is the one described above. "
    )
    if garment_type == "saree":
        rule += (
            "If the pose description above does not say how the pallu "
            "hangs, any part of the grey shape hanging from the shoulder "
            "or falling toward the floor is the pallu: draw it with that "
            "outline, made only from the fabric of image 1. "
        )
    return rule


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
    """Who the model must generate. Children get a clear age and no body_type."""
    if _is_child(gender):
        return (
            f"a {CHILD_AGE}-year-old Indian {_gender_word(gender)} — clearly "
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
        f"{pose_text}, on a plain neutral studio "
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
        f"{pose_text}, on a plain neutral studio "
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
    """
    if keep_background:
        background_text = (
            "in the SAME place as image 2: keep the original background of "
            "image 2 — same location, objects, colours, lighting and depth "
            "of field — continued naturally to fill the new frame"
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
            "background is requested at the end of this prompt)"
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
        f"{pose_text}, {background_text}, "
        f"{framing['shown']}. "
        "THE PERSON MUST BE COPIED EXACTLY FROM IMAGE 2: same face, "
        "eyes, eyebrows, nose, lips, same skin tone and brightness, same "
        "hair colour, hair length and hairstyle (unless the pose above covers "
        "the hair with the pallu), same age, same body build "
        "and proportions, the same facial hair if any, and every "
        "accessory worn in image 2 (watch, bangles, rings, earrings, "
        "necklace, spectacles) in the same place. "
        f"{ignore_text} — the new pose "
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

# Saree: the blouse sleeves are set in the saree description, so the
# "full-length down to the wrist" sentence is left out (it made the model
# draw a full-sleeve top instead of a saree blouse).
CLOSING_SAREE = (
    "Generate realistic shading, folds, and shadows. The result must look "
    "like one real, unedited photograph. "
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

GARMENT_SPECS = {
    ("kurta", "plain"): {
        "fabric_target": "kurta",
        "border": True,
        "garment": (
            "a traditional Indian men's kurta — a straight-cut garment "
            "ending just above the knee (the hem a few inches above the "
            "kneecap, not mid-thigh, not below the knee), with a simple "
            "mandarin/band collar, a short front placket with two or three "
            "buttons near the neck, and straight side slits at the hem, "
            "loose-fitting. Below it, a matching plain straight-cut "
            "kurta-pajama reaching the ankles, in a plain solid color "
            "(white, off-white, or a solid shade from the kurta's palette), "
            "never patterned. "
        ),
    },
    ("kurta", "sherwani"): {
        "fabric_target": "sherwani",
        "border": False,
        "color_note": (
            "CRITICAL — sherwanis are commonly black, maroon, or gold, but "
            "ignore that assumption completely: the sherwani must be in the "
            "colors of image 1 only, even if unusual for a sherwani. "
        ),
        "garment": (
            "a formal sherwani — a long coat-like garment DRAMATICALLY "
            "LONGER than an ordinary kurta, extending well past the knee "
            "toward mid-calf (this length is the most important feature; a "
            "hem at or above the knee is wrong), with a stand-up "
            "mandarin/bandhgala collar, a full column of small decorative "
            "buttons from neck to hem, and a fitted, tailored torso with "
            "visible waist suppression. Below it, a matching churidar — "
            "fitted through the leg, gathering into soft folds above the "
            "ankle — in a plain solid color (white, off-white, or a solid "
            "shade from the sherwani's palette), never patterned. "
        ),
    },
    ("kurta", "pathani"): {
        "fabric_target": "kurta",
        "border": False,
        "color_note": (
            "CRITICAL — Pathani suits are commonly white or beige, but "
            "ignore that assumption: the kurta must be in the colors of "
            "image 1 only. "
        ),
        "garment": (
            "a Pathani-style kurta — loose, relaxed, straight-cut, to "
            "roughly mid-thigh or knee, with a classic SHIRT-style pointed "
            "collar (not a round or mandarin collar), two rectangular "
            "chest patch pockets with flaps, and a short button placket. "
            "Below it, a Pathani salwar — VERY LOOSE, voluminous and "
            "pleated, dramatically wider than a normal kurta-pajama, "
            "narrowing to a cuffed ankle — in a plain solid color that "
            "coordinates with the kurta, never patterned. "
        ),
    },
    ("kurta", "jodhpuri"): {
        "fabric_target": "jacket",
        "border": False,
        "color_note": (
            "CRITICAL — Jodhpuri suits are commonly cream or beige, but "
            "ignore that assumption: the jacket must be in the colors of "
            "image 1 only. This fabric rule applies to the JACKET only — "
            "the trouser stays plain and solid. "
        ),
        "garment": (
            "a Jodhpuri bandhgala jacket — structured, single-breasted, "
            "sharply tailored shoulders, stand-up mandarin/bandhgala "
            "collar (no lapel), a full column of small buttons, one small "
            "chest pocket and two flap hip pockets, hip-length hem, fitted "
            "closely, with a crisp, smooth, almost flat finish (creases "
            "only at the elbow bend). No extra kurta or tunic layer may "
            "show below the jacket hem — it goes straight into the "
            "trouser at the waist. Below it, a fitted straight-cut formal "
            "trouser in a PLAIN SOLID color matching the jacket's color "
            "tone, crisply pressed, with no pattern or texture. "
        ),
    },
    ("kurti_pant", "default"): {
        "fabric_target": "kurti",
        "border": True,
        "garment": (
            "a traditional Indian women's kurti — a modest straight or "
            "A-line cut ending at roughly mid-thigh or knee, with a plain "
            "round or V neckline (not deep), and elbow-length or "
            "full-length sleeves (never sleeveless), comfortably "
            "loose-fitting. The kurti is ALWAYS worn together with a "
            "matching straight-cut churidar/salwar-style pant that is "
            "clearly visible below the kurti hem and reaches the ankles, "
            "in a plain solid color (white, off-white, or a solid shade "
            "from the kurti's palette), never patterned — the legs must "
            "never be bare. No dupatta. "
        ),
    },
    ("shirt", "default"): {
        "fabric_target": "shirt",
        "border": False,
        "garment": (
            "a properly fitted, collared button-up shirt, not too loose "
            "and not too tight, worn with plain dark solid-color formal "
            "full-length trousers. "
        ),
    },
    ("pant", "default"): {
        "fabric_target": "pant",
        "border": False,
        "garment": (
            "a formal, full-length, straight-cut trouser reaching all the "
            "way to the ankles, clean and pressed (not skinny, not baggy, "
            "no cargo pockets), with naturally draped folds. Wear it with "
            "a plain white collared shirt — the shirt is NOT made from "
            "image 1's fabric, only the trouser is. "
        ),
    },
    ("saree", "default"): {
        "fabric_target": "saree",
        "border": False,
        "garment": (
            "an elegant Indian saree draped in the traditional Nivi style, "
            "with the pallu (end-piece) arranged exactly as described in the "
            "pose above, or, if the pose does not describe it, falling over "
            "the left shoulder; worn with a well-fitted, short, normal-length "
            "blouse with elbow-length sleeves (never long or tunic-like) in a "
            "solid color picked from "
            "image 1's palette, with a modest neckline and a fully covered "
            "back (a closed round back neck, never an open or deep back), "
            "and the waist covered neatly by the saree drape. The whole look "
            "must be graceful, dignified and modest — nothing revealing or "
            "suggestive. If image 1 has a special "
            "decorative artwork, place it on the pallu only; along the "
            "main body's bottom hem use only a plain, narrow, evenly "
            "repeating border in colors taken from image 1. "
        ),
    },
    ("blazer", "business"): {
        "fabric_target": "blazer",
        "border": False,
        "color_note": (
            "CRITICAL — business suits are commonly navy, charcoal, or "
            "black, but ignore that assumption: the blazer, including its "
            "lapel, must be in the colors of image 1 only. The shirt and "
            "tie are plain and unrelated to image 1. "
        ),
        "garment": (
            "a formal business blazer — structured, single-breasted, notch "
            "lapel, sharply tailored shoulders, hip length, buttoned "
            "closed — worn over a plain white collared shirt with a plain "
            "dark solid-color necktie, and matching plain dark "
            "full-length trousers. "
        ),
    },
    ("blazer", "wedding"): {
        "fabric_target": "jacket",
        "border": False,
        "color_note": (
            "CRITICAL — tuxedo jackets are commonly black, but ignore that "
            "assumption: the entire jacket, including the shawl lapel, "
            "must be in the colors of image 1 only. The shirt, bow tie, "
            "and pocket square are plain and unrelated to image 1. "
        ),
        "garment": (
            "a formal tuxedo-style dinner jacket — single-breasted with a "
            "smooth SHAWL lapel (one continuous rounded curve, no notch), "
            "sharply tailored shoulders, hip length, one button fastened "
            "— worn over a plain white collared shirt with a plain black "
            "bow tie and a plain white pocket square, and plain black "
            "full-length trousers. "
        ),
    },
    ("blazer", "casual"): {
        "fabric_target": "blazer",
        "border": False,
        "color_note": (
            "CRITICAL — casual blazers are commonly grey, beige, or navy, "
            "but ignore that assumption: the blazer, including its lapel, "
            "must be in the colors of image 1 only. The shirt is plain "
            "white and unrelated to image 1. "
        ),
        "garment": (
            "a casual unstructured blazer worn OPEN and unbuttoned, soft "
            "relaxed shoulders, notch lapel, relaxed fit, hip length — over "
            "a plain white collared shirt with the top button undone and "
            "no necktie, with plain dark full-length trousers. "
        ),
    },
}


def _get_garment_spec(garment_type, garment_style):
    """Looks up the spec entry for a garment (and style, if it has styles)."""
    style_key = garment_style if garment_type in GARMENT_STYLE_OPTIONS else "default"
    return GARMENT_SPECS.get((garment_type, style_key))


_GARMENT_NOUN = {
    "saree": "saree",
    "kurta": "kurta",
    "kurti_pant": "kurti with a matching pant",
    "shirt": "shirt",
    "pant": "pant",
    "blazer": "blazer",
}


def _task_line(scenario, garment_type, use_garment_image, pose_slot):
    """
    First sentence of every own-model prompt: says WHAT garment is wanted
    and WHAT each image is, so the garment is not buried after hundreds of
    words about the person and the pose, and image 1 (a fabric swatch) is
    never mistaken for a garment or a person.
    """
    if use_garment_image:
        what = "the garment shown in image 1"
        image_1 = "image 1 = the garment to copy"
    else:
        noun = _GARMENT_NOUN.get(garment_type, "garment")
        what = f"a {noun} made from the fabric in image 1"
        image_1 = (
            "image 1 = the FABRIC swatch (only its colors and pattern are "
            "used; it is not a garment shape)"
        )
    roles = ["image 0 = blank canvas (frame size only)", image_1]
    if scenario == SCENARIO_PERSON_POSE:
        roles.append("image 2 = photo of the person (identity only)")
    elif scenario == SCENARIO_FACE_PHOTO:
        roles.append("image 2 = face reference")
    if pose_slot:
        roles.append(f"image {pose_slot} = grey pose silhouette (pose only)")
    return (
        f"TASK: generate one realistic photograph of a person wearing {what}. "
        "IMAGES: " + "; ".join(roles) + ". "
    )


def _build_own_model_prompt(
    scenario, garment_type, garment_style, use_garment_image, gender,
    body_type, pose=None, camera_view=None, garment_details=None, background=None,
    pose_slot=None,
):
    """
    Builds the dedicated prompt used by generated_person, face_photo and
    person_pose.
    pose_slot: image slot number of the pose guide (silhouette), or None.
    """
    pose_text = _own_model_pose_text(
        pose, garment_type, garment_style, garment_details, camera_view,
        pose_slot=pose_slot,
    )
    framing = get_framing(camera_view)

    if scenario == SCENARIO_FACE_PHOTO:
        subject = _subject_block_with_face(gender, body_type, pose_text, framing)
    elif scenario == SCENARIO_PERSON_POSE:
        subject = _subject_block_with_person(
            pose_text, framing, keep_background=not background
        )
    else:
        subject = _subject_block(gender, body_type, pose_text, framing)

    # The garment and the role of every image come FIRST.
    subject = _task_line(scenario, garment_type, use_garment_image, pose_slot) + subject

    # The guide is a silhouette: it gives the pose only (never face / clothes / fabric).
    if pose_slot:
        subject += _pose_guide_rule(pose_slot, garment_type)

    if use_garment_image:
        prompt = subject + GENERATED_GARMENT_IMAGE_BODY
    else:
        spec = _get_garment_spec(garment_type, garment_style)
        if spec is None:
            return None

        target = spec["fabric_target"]
        prompt = subject + "Dress this person in " + spec["garment"]
        prompt += spec.get("color_note", "")
        prompt += FABRIC_RULES.format(target=target)
        if spec["border"]:
            prompt += BORDER_RULES.format(target=target)
        prompt += CLOSING_SAREE if garment_type == "saree" else CLOSING

    # person_pose has no gender field (the person comes from the photo).
    if _is_child(gender):
        prompt += CHILD_GARMENT_LINE
    return prompt


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------

def _build_base(
    scenario, garment_type, garment_style, use_garment_image, gender,
    body_type, pose=None, camera_view=None, garment_details=None, background=None,
    pose_slot=None,
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
            pose_slot=pose_slot,
        )
        if prompt is None:
            return None
        return {"prompt": prompt, "guidance": GENERATED_GUIDANCE, "seed": GENERATED_SEED}

    # person_photo: start from the prompts in prompts.py (never modified here).
    if use_garment_image:
        return {
            "prompt": GARMENT_IMAGE_PROMPT,
            "guidance": GARMENT_IMAGE_GUIDANCE,
            "seed": GARMENT_IMAGE_SEED,
        }

    base = get_prompt_config(garment_type, garment_style)
    if base is None:
        return None
    return dict(base)  # copy — never modify the stored data


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
    pose_slot=None,
):
    """
    Main function used by the engine. Returns
    {"prompt", "guidance", "seed"}, or None if no prompt exists for the
    given garment_type / garment_style.
    pose_slot: image slot number of the pose guide (silhouette), or None
    when no guide is sent (then only the pose text is used).
    """
    base = _build_base(
        scenario, garment_type, garment_style, use_garment_image, gender,
        body_type, pose, camera_view, garment_details, background,
        pose_slot=pose_slot,
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
        "Prompt built: scenario=%s pose=%s pose_slot=%s camera_view=%s details=%s "
        "pose_phrases_replaced=%s words=%s",
        scenario, pose, pose_slot, camera_view, garment_details, replaced,
        len(base["prompt"].split()),
    )
    logger.info("FINAL PROMPT: %s", base["prompt"])
    return base