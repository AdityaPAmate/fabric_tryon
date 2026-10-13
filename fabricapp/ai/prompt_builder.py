"""
Stage: Prompt builder.
Single place that decides WHICH prompt is used for a request, based on
the situation (scenario). The engine only calls build_prompt() and
never needs to know how prompts are made.

Scenarios:
    person_photo      -> user uploaded a person photo and NO pose and NO
                         camera_view. The GARMENT_PROMPTS from prompts.py
                         are used, plus the movable parts (garment
                         details) and ONE short preserve line at the end.
    person_pose       -> user uploaded a person photo AND a pose and/or a
                         camera_view. image 0 = blank canvas, image 2 =
                         the person photo as a REFERENCE. Uses the
                         own-model prompt (built from GARMENT_SPECS).
                         (The plain edit-mode keeps the original pose and
                         framing, so it cannot be used for a new pose or
                         a new camera view.)
    face_photo        -> no person photo, but a predefined face was
                         chosen. image 0 = blank canvas, image 2 = face
                         reference. Uses the dedicated own-model prompt.
    generated_person  -> no person photo and no face. Dedicated
                         own-model prompt built from GARMENT_SPECS.
    pose_reference    -> no person photo, and the chosen pose has a
                         reference PHOTO (pose_reference.py, today only
                         saree + pallu_on_head). image 0 = that photo
                         (it is EDITED, the pose is not described in
                         words), image 1 = fabric, image 2 = face (only if
                         a face was chosen). A camera_view and a
                         background can be applied on top of the photo.
                         See the POSE REFERENCE PATH.

Movable parts (variables):
    pose            -> pose_data.py (can differ per garment / style / detail)
    camera_view     -> camera_data.py (framing text)
    garment_details -> garment_details.py (sleeves, tuck, dupatta)
    background      -> BACKGROUND_DESCRIPTIONS in prompts.py
    style note      -> additional_style_note

SAREE RESOLVER PATH (first round of the "one requirement, one owner"
architecture):
    garment_type == "saree", no garment_image, and scenario in
    (generated_person, face_photo) -> _build_saree_resolved().
    Python resolves every known condition (pose, pallu, background, face,
    style note) FIRST, then composes the prompt from the text variables in
    prompt_parts.py. The final prompt contains only the resolved
    instruction, never "unless" / "otherwise" / "if the pose ...".
    Every other garment and every other scenario (including saree with
    person_pose / person_photo / garment_image) still uses the OLD path
    below, which is unchanged.

POSE REFERENCE PATH:
    scenario == pose_reference -> _build_pose_reference_prompt().
    Same resolve-then-compose idea, but the prompt is an EDIT prompt: the
    reference photo is image 0 and only the fabric is replaced. Texts are
    the REF_* variables in prompt_parts.py. Nothing in the old paths or in
    the saree resolver path is changed by it.
    camera_view (NEW): when sent, a CAMERA line (the existing
    CAMERA_VIEW_INSTRUCTIONS text) is added, the framing is no longer
    "kept", and the ORIGINAL background of the photo is kept (continued
    behind the new angle), never replaced by a plain one.

PERSON POSE: DEDICATED SHORT PROMPTS (person photo + pose / camera_view):
    kurti_pant -> _build_person_pose_kurti_prompt
    shirt      -> _build_person_pose_shirt_prompt
    kurta, blazer (NEW) -> _build_person_pose_spec_prompt
    Reason: the shared long own-model prompt (about 1000 words) made the
    model ignore the new pose / camera view (test reports of 2026-10-09:
    kurta "pose not work", "camera view not work", blazer "poses not
    work"). The dedicated prompt is short and priority-ordered: pose first.
    The garment wording still comes from GARMENT_SPECS, and the movable
    parts (sleeves, dupatta) still use the same anchors from CLOSING.
    saree, pant and garment_image keep the old long prompt (unchanged).

KURTA / PLAIN: WHITE PANT (NEW):
    The pajama of the plain kurta is plain solid WHITE. GARMENT_SPECS says
    it for the own-model paths and the person_pose route, and
    KURTA_PANT_WHITE_LINE says it on the person_photo (edit) route.
    KURTA_WHITE_PANT_STYLES is the one place that lists which kurta styles
    get it.

KURTA / BLAZER FIXES OF THE 2026-10-10 TEST REPORTS (NEW, kurta + blazer ONLY):
    Every helper in the section "KURTA + BLAZER FIXES" returns its input
    unchanged for any other garment, so shirt / pant / kurti_pant / saree
    prompts stay exactly as they were. prompts.py is never edited; edit-route
    phrases are replaced in memory (a phrase not found is logged).
        plain kurta length + fabric patch on the hand + third hand (edit)
        sherwani / pathani trouser = plain solid main colour of image 1
        business blazer tie = plain solid main colour of image 1
        back view (back_turn_hair_touch): no buttons / placket / pockets
        face_choice + pose + background together: dedicated SHORT prompt
            _build_own_model_spec_prompt (OWN_MODEL_SPEC_SCENARIOS)
        body_type (plus / trim) with face_choice: explicit BODY BUILD line
        new background on kurta / blazer person_pose / face_photo: short
            background text, written in the middle of the prompt
        seated pose: "one person" rule (two bodies for two legs)

CONSISTENCY RULES kept in this file (do not break them when editing):
    1. One instruction = one place. A pose, a pallu arrangement, a
       lighting rule or a background rule is stated once, and no other
       sentence may contradict it.
    2. Lighting: when the background of image 2 is kept, the face follows
       the lighting of image 2; only when a new background or a studio
       background is used, the face gets neutral white light.
    3. The garment and the role of every image are named FIRST (TASK line).
       The role of image 2 in the TASK line must match what the subject
       block copies from image 2.
    4. MODESTY_FINAL is always the LAST sentence of every prompt, after the
       style note, so no note can override it.
    5. The saree has its own modesty wording, its own closing (no trouser
       words, no "sleeves down to the wrist") and its own border rule
       (special artwork on the pallu only).
    6. "The pose described above" is used (never "the NEW pose"), because
       when only camera_view is sent, the pose is the camera_view default.

    7. The pose has its own "POSE (...)" sentence right after the TASK line;
       the subject sentence only points to it ("the pose given in the POSE
       line above") and never repeats the pose wording.

IMPORTANT: keep prompts SHORT. Very long prompts make the model ignore
parts of them. Do not append long text to the prompts.

The background text is built HERE (not in prompts.py) so that the
lighting rule can protect the face, hair and skin tone from getting a
warm/dark colour cast from the background scene.
"""

import logging

from . import prompt_parts as P
from .prompts import (
    GARMENT_STYLE_OPTIONS,
    GARMENT_IMAGE_PROMPT,
    GARMENT_IMAGE_GUIDANCE,
    GARMENT_IMAGE_SEED,
    BACKGROUND_DESCRIPTIONS,
    get_prompt_config,
    get_camera_view_instruction,
)
from .pose_data import (
    POSE_PHRASE_REPLACEMENTS,
    get_pose_sentence,
    get_saree_pose_parts,
)
from .camera_data import get_framing
from .garment_details import apply_garment_details, MODE_EDIT, MODE_OWN

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

# Scenarios that use the NEW saree resolver (see _uses_saree_resolver).
SAREE_RESOLVER_SCENARIOS = (
    SCENARIO_GENERATED_PERSON,
    SCENARIO_FACE_PHOTO,
)

# NEW: garments whose person_pose request uses the dedicated short prompt
# built from GARMENT_SPECS (_build_person_pose_spec_prompt). kurti_pant and
# shirt have their own builders and are not listed here.
PERSON_POSE_SPEC_GARMENTS = ("kurta", "blazer")

# NEW (2026-10-10 reports 6, 7, 9, 10): own-model scenarios that use the
# short kurta / blazer prompt (_build_own_model_spec_prompt). Only the
# face_photo path failed in the reports (face + pose + background together,
# body_type ignored, three hands). Add SCENARIO_GENERATED_PERSON here later
# if the no-face path should use it too.
OWN_MODEL_SPEC_SCENARIOS = (SCENARIO_FACE_PHOTO,)

# NEW: kurta styles whose trouser / pajama must be plain solid white on the
# person_photo (edit) route. The own-model wording is in GARMENT_SPECS.
KURTA_WHITE_PANT_STYLES = ("plain",)

# NEW: exact phrase of the tested kurta/plain edit prompt (prompts.py) that
# leaves the pajama colour open, and the text that replaces it in memory.
KURTA_PANT_OLD_PHRASE = (
    "white, off-white, or a solid shade picked from the kurta's own "
    "color palette"
)
KURTA_PANT_NEW_PHRASE = "plain solid WHITE"

# NEW (blazer, from the reference image of the three blazer styles):
# 1. LENGTH: the generated jacket went far too low. The reference jacket
#    ends at the base of the seat, about level with the wrists of the
#    hanging arms. BLAZER_LENGTH_DETAIL is the one place for this wording.
BLAZER_LENGTH_DETAIL = (
    "ending at the base of the seat, about level with the wrists of the "
    "hanging arms (a short, fitted jacket length, never reaching the "
    "mid-thigh), with the trousers clearly visible below the hem"
)

# 2. TROUSERS: business and wedding trousers are a plain solid in the
#    main colour of the blazer fabric (colour only, never the pattern).
BLAZER_TROUSER_STYLES = ("business", "wedding")

BLAZER_TROUSER_LINE = (
    "TROUSERS (replace the trousers of image 0): plain, solid, "
    "straight-cut, full-length trousers down to the ankles, crisply "
    "pressed, in exactly the main colour of the blazer fabric from "
    "image 1, with no pattern, check, stripe or texture. Only the colour "
    "is taken from image 1, never its pattern. "
)

# 3. person_photo (edit) route: exact phrases of the tested blazer prompts
#    in prompts.py and their replacements. Applied in memory only
#    (prompts.py is never edited). A phrase that is not found is logged.
_WEDDING_INNER_OLD = (
    "worn OVER a plain white collared dress shirt, with a plain black bow "
    "tie visible at the collar, and a plain white pocket square in the "
    "chest pocket"
)
_WEDDING_INNER_NEW = (
    "worn OVER a plain mandarin band-collar shirt (a short stand-up band "
    "collar closed with a row of small buttons, no necktie and no bow tie) "
    "in a plain solid light tone, with a plain white pocket square folded "
    "into a small puff-flower shape clearly visible in the chest pocket"
)
_WEDDING_NEW_ELEMENTS_OLD = (
    "The white shirt, black bow tie, and white pocket square are NEW "
    "elements you are adding — plain white (shirt), plain black (bow tie), "
    "plain white (pocket square), completely unrelated to image 1's "
    "fabric; do not put image 1's pattern on the shirt, bow tie, or "
    "pocket square"
)
_WEDDING_NEW_ELEMENTS_NEW = (
    "The band-collar shirt and the pocket square are NEW elements you are "
    "adding — plain, solid and unpatterned, unrelated to image 1's "
    "pattern; do not put image 1's pattern on the shirt or the pocket "
    "square"
)
_WEDDING_RESULT_OLD = "over a white shirt with a black bow tie and pocket square"
_WEDDING_RESULT_NEW = "over a plain band-collar shirt with a pocket square"

# ----------------------------------------------------------------------
# KURTA + BLAZER FIXES (2026-10-10 test reports). Text + tiny helpers.
# Everything here works for garment_type "kurta" / "blazer" only and
# returns its input unchanged otherwise.
# ----------------------------------------------------------------------

KURTA_BLAZER = ("kurta", "blazer")


def _replace_phrases(prompt, pairs, label):
    """In-memory replace of exact phrases; a phrase not found is logged."""
    for old_text, new_text in pairs:
        if old_text in prompt:
            prompt = prompt.replace(old_text, new_text, 1)
        else:
            logger.warning("%s: phrase not found: %.70s", label, old_text)
    return prompt


# Report 1: plain kurta too short (edit route). The user wants the hem at
# the knee; the tested prompt said "a few inches above the kneecap".
KURTA_PLAIN_LENGTH_OLD = (
    "extending down to just above the knee (NOT mid-thigh, NOT below the "
    "knee — the hem must end a few inches above the kneecap)"
)
KURTA_PLAIN_LENGTH_NEW = (
    "extending down to the knee (the hem ends level with the middle of the "
    "kneecaps, clearly below mid-thigh)"
)
KURTA_PLAIN_LENGTH_LINE = (
    "KURTA LENGTH (replaces any earlier length instruction): the plain kurta "
    "is long, its hem ending level with the knees and fully covering both "
    "thighs, never short or mid-thigh. "
)

# Reports 1 + 2 (edit route): fabric patch on the hand, extra (third) hand.
KURTA_EDIT_LIMBS_LINE = (
    "ARMS AND HANDS: the person has exactly two arms and two hands in total — "
    "never a third hand or a leftover arm at the lower side of the frame. "
    "Hands, fingers and wrists keep their bare skin exactly as in image 0: "
    "image 1's fabric, its border or any patch of it appears only on the "
    "kurta body, collar and sleeves (a cuff band stops at the sleeve edge), "
    "never on the hands, skin or background. "
)

# Report 3: sherwani / pathani trouser = plain solid main colour of the
# fabric (it came out black, because the prompt left the colour open).
KURTA_COLOURED_PANT_STYLES = ("sherwani", "pathani")

KURTA_PANT_COLOUR_EDIT = {
    "sherwani": [(
        "(white, off-white, or a solid shade picked from the sherwani's own "
        "color palette), never patterned or bright",
        "(exactly the main colour of the sherwani fabric from image 1, as a "
        "plain solid), never patterned",
    )],
    "pathani": [(
        "(commonly the same tone as the kurta itself, or a solid shade "
        "picked from the kurta's own color palette), never patterned or "
        "bright",
        "(exactly the main colour of the kurta fabric from image 1, as a "
        "plain solid), never patterned",
    )],
}

KURTA_PANT_COLOUR_LINE = (
    "TROUSER COLOUR (replaces any earlier instruction about the trouser "
    "colour): the churidar / salwar below is a plain solid in exactly the "
    "main colour of image 1's fabric, with no pattern, print, check or "
    "border. It is never black, grey or any dark colour unless that is the "
    "main colour of image 1, and it does not keep the trouser colour of "
    "image 0. "
)

# Business blazer: the tie is a plain solid in the main colour of the
# fabric, no pattern (edit route = exact phrases of prompts.py).
BLAZER_TIE_EDIT_REPLACEMENTS = [
    (
        "with a plain dark solid-color necktie visible at the collar",
        "with a plain solid necktie visible at the collar, in exactly the "
        "main colour of image 1's fabric",
    ),
    (
        "plain white (shirt) and a plain dark solid color (tie), completely "
        "unrelated to image 1's fabric; do not put image 1's pattern on the "
        "shirt or tie",
        "plain white (shirt) and a plain solid tie in the main colour of "
        "image 1's fabric; the shirt is unrelated to image 1, and image 1's "
        "pattern must never appear on the shirt or on the tie",
    ),
    (
        "over a white shirt and dark tie",
        "over a white shirt and a plain tie in the blazer's main colour",
    ),
]

BLAZER_TIE_LINE = (
    "TIE (replaces any earlier instruction about the tie colour): the "
    "necktie is plain and solid, in exactly the main colour of the blazer "
    "fabric from image 1, with no pattern, stripe, check or texture. Only "
    "the colour is taken from image 1, never its pattern. "
)

# Report 8: sherwani buttons drawn on the BACK when the person is seen from
# behind. The button column, placket and pockets are front details.
BACK_VIEW_POSES = ("back_turn_hair_touch",)

BACK_VIEW_REPLACEMENTS = [
    ("a full column of small decorative buttons from neck to hem",
     "a plain, smooth, completely button-free back"),
    ("a full column of small buttons, one small chest pocket and two flap "
     "hip pockets",
     "a smooth plain back"),
    ("two rectangular chest patch pockets with flaps, and a short button "
     "placket",
     "a smooth plain back"),
    ("a short front placket with two or three buttons near the neck",
     "a plain smooth back"),
]

BACK_VIEW_NOTE = (
    "BACK VIEW: the camera sees only the BACK of the person, so the front of "
    "the garment is hidden: no buttons, button column, placket, chest "
    "pocket, hip pocket flaps or lapels are drawn anywhere. The back of the "
    "garment is one smooth, plain surface of image 1's fabric (a jacket may "
    "show a single centre vent). "
)

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


def _short_background(description):
    """
    Report 4 ("cinematic" image): short background text with plain catalog
    lighting. Used by the kurta / blazer short prompts only.
    """
    if not description:
        return ""
    return (
        "BACKGROUND: replace the whole area behind the person with this "
        "scene: " + description + ". The person is lit by plain, natural "
        "daylight with neutral white balance and no colour cast; it is an "
        "ordinary catalog photograph, not cinematic, with no dramatic "
        "lighting and no film look. "
    )


def _garment_text_for_pose(garment_text, garment_type, pose):
    """Garment wording for the pose (a back view hides every front detail)."""
    if garment_type not in KURTA_BLAZER or pose not in BACK_VIEW_POSES:
        return garment_text
    for old_text, new_text in BACK_VIEW_REPLACEMENTS:
        garment_text = garment_text.replace(old_text, new_text, 1)
    return garment_text + BACK_VIEW_NOTE


def _apply_kurta_edit_changes(prompt, garment_type, garment_style, use_garment_image):
    """person_photo (edit) route: kurta length and trouser colour phrases."""
    if use_garment_image or garment_type != "kurta":
        return prompt
    pairs = []
    if garment_style == "plain":
        pairs.append((KURTA_PLAIN_LENGTH_OLD, KURTA_PLAIN_LENGTH_NEW))
    pairs += KURTA_PANT_COLOUR_EDIT.get(garment_style, [])
    return _replace_phrases(prompt, pairs, "kurta edit")


def _kurta_edit_extra_lines(garment_type, garment_style, use_garment_image):
    """person_photo (edit) route: the short extra lines for kurta only."""
    if use_garment_image or garment_type != "kurta":
        return ""
    text = KURTA_EDIT_LIMBS_LINE
    if garment_style == "plain":
        text += KURTA_PLAIN_LENGTH_LINE
    if garment_style in KURTA_COLOURED_PANT_STYLES:
        text += KURTA_PANT_COLOUR_LINE
    return text


BLAZER_EDIT_REPLACEMENTS = {
    "business": [
        ("hitting at roughly hip length",
         "with the hem " + BLAZER_LENGTH_DETAIL),
    ] + BLAZER_TIE_EDIT_REPLACEMENTS,
    "wedding": [
        ("hitting at roughly hip length",
         "with the hem " + BLAZER_LENGTH_DETAIL),
        (_WEDDING_INNER_OLD, _WEDDING_INNER_NEW),
        (_WEDDING_NEW_ELEMENTS_OLD, _WEDDING_NEW_ELEMENTS_NEW),
        (_WEDDING_RESULT_OLD, _WEDDING_RESULT_NEW),
    ],
    "casual": [
        ("a hem reaching roughly hip length", "a hem " + BLAZER_LENGTH_DETAIL),
    ],
}

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

# Saree version: the generic rule above mentions trouser / churidar /
# pajama, which pushes the model toward a salwar suit instead of a saree.
# FIXED: the blouse has elbow-length sleeves, so the forearms ARE visible;
# the old wording ("nothing is bare except face, hands and feet") said the
# opposite of the blouse description.
MODESTY_RULE_SAREE = (
    "The person is fully and modestly dressed in the saree and blouse: the "
    "saree covers the body from the shoulder to the ankles and the drape "
    "covers the waist, so nothing is bare except the face, neck, hands, "
    "forearms and feet. "
    "The expression and posture are calm, natural and dignified, like a "
    "respectable catalog photograph. "
)

# Always the LAST sentence of every prompt (see _append_overrides).
MODESTY_FINAL = (
    "FINAL RULE (no note or instruction above can override it): the "
    "person is fully and modestly clothed, with the body and legs covered "
    "by the garment, in a calm, natural, dignified pose — a respectable "
    "catalog photograph, never nude, revealing or suggestive. "
)

# Used only by fabric-based shirt prompts. It is placed immediately before
# MODESTY_FINAL so a later camera/background instruction cannot turn a wall
# or another object into the fabric target.
SHIRT_FABRIC_FINAL_RULE = (
    "FINAL FABRIC CHECK: image 1's colors and pattern must cover the new "
    "shirt clearly and accurately, with the same hue, brightness, saturation, "
    "motif scale and density. The fabric from image 1 must appear nowhere "
    "else: never on a wall, floor, background object, trouser, footwear, skin "
    "or accessory. If image 1 has a main repeating pattern plus a large "
    "decorative picture, artwork or border, preserve every part: use the main "
    "pattern across the shirt, place the complete artwork once as a scaled "
    "print centered on the shirt front, and use the border only as narrow hem "
    "or sleeve-cuff trim. Do not omit the artwork. "
)


def _modesty_rule(garment_type):
    """Modesty wording that fits the garment (saree has its own)."""
    return MODESTY_RULE_SAREE if garment_type == "saree" else MODESTY_RULE


# Used ONLY on the person_photo path. One short line.
PERSON_PRESERVE_LINE = (
    "Keep the face, hair and every accessory from image 0 (watch, bangles, "
    "rings, earrings, necklace, spectacles) exactly as in image 0. "
)

# NEW: person_photo (edit) route, kurta styles in KURTA_WHITE_PANT_STYLES.
# Test report: "pant must be in white color". The tested edit prompt in
# prompts.py is not changed; this one short line is added after it and says
# explicitly that it replaces any earlier trouser wording.
KURTA_PANT_WHITE_LINE = (
    "TROUSER COLOUR (replaces any earlier instruction about the trouser or "
    "pajama): the pajama below the kurta is plain, solid WHITE, "
    "straight-cut and full-length down to the ankles, with no pattern, and "
    "it is not made from image 1's fabric. "
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

# Saree border rule. The generic BORDER_RULES above puts the border band on
# the hem and sleeve cuffs, which is wrong for a saree (special artwork goes
# on the pallu only). This is the ONLY place the saree border / artwork rule
# is stated; the saree description in GARMENT_SPECS no longer repeats it.
# (The saree resolver path has its own version in prompt_parts.py.)
SAREE_BORDER_RULES = (
    "First examine image 1: if it has one uniform pattern, apply it evenly "
    "over the whole saree, pallu included. If it has two distinct zones — "
    "a main body pattern plus a special decorative artwork or denser strip "
    "— put the main pattern on the body of the saree and put that artwork "
    "ONLY on the pallu, with its own colors and motifs exactly as in "
    "image 1; along the bottom hem use only a plain, narrow border that "
    "follows the border shown in image 1 (a plain hem if image 1 has no "
    "border), and do not repeat the large artwork there. "
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
        # CHANGED (test report: "pant must be in white color"): the
        # kurta-pajama is plain solid WHITE (it used to be "white,
        # off-white, or a solid shade from the kurta's palette").
        "garment": (
            "a traditional Indian men's kurta — a straight-cut garment "
            "ending just above the knee (the hem a few inches above the "
            "kneecap, not mid-thigh, not below the knee), with a simple "
            "mandarin/band collar, a short front placket with two or three "
            "buttons near the neck, and straight side slits at the hem, "
            "loose-fitting. Below it, a matching plain straight-cut "
            "kurta-pajama reaching the ankles, in plain solid WHITE, "
            "never patterned and never made from image 1's fabric. "
        ),
    },
    # CHANGED (report 3): the churidar is a plain solid in the main colour of
    # image 1 ("pant_colour_from_fabric"), no longer "white, off-white, or a
    # shade from the palette" (the model picked black).
    ("kurta", "sherwani"): {
        "fabric_target": "sherwani",
        "border": False,
        "pant_colour_from_fabric": True,
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
            "ankle — in a plain solid color that is exactly the main colour "
            "of the sherwani fabric from image 1 (never black, grey or "
            "white unless that is image 1's main colour), with no pattern. "
        ),
    },
    # CHANGED (report 3): same idea for the Pathani salwar.
    ("kurta", "pathani"): {
        "fabric_target": "kurta",
        "border": False,
        "pant_colour_from_fabric": True,
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
            "narrowing to a cuffed ankle — in a plain solid color that is "
            "exactly the main colour of the kurta fabric from image 1 "
            "(never black or grey unless that is image 1's main colour), "
            "never patterned. "
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
            "a traditional Indian women's kurti, modest and comfortably "
            "loose-fitting, with a simple round or modest V neckline and "
            "full-length sleeves reaching the wrists. Pair it with plain, "
            "solid white, straight-cut full-length pants visible below the "
            "kurti hem and reaching the ankles. The pants must be white and "
            "must not use image 1's fabric, print, or pattern. Apply image "
            "1's fabric only to the kurti. No dupatta. "
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
    # SAREE — OLD path only (person_pose etc.). The generated_person /
    # face_photo requests use the saree resolver (prompt_parts.py) and do
    # not read this entry. The border / artwork rule lives only in
    # SAREE_BORDER_RULES, and "border_rules" tells the builder to use it.
    # The pallu default below is used only when the pose sentence does not
    # describe the pallu.
    ("saree", "default"): {
        "fabric_target": "saree",
        "border": False,
        "border_rules": SAREE_BORDER_RULES,
        "garment": (
            "an elegant Indian saree draped in the traditional Nivi style, "
            "with the front pleats falling neatly to the ankles and the "
            "pallu (end-piece) arranged as described in the pose above, or, "
            "if the pose does not describe it, falling over the left "
            "shoulder in soft pleats to the knee or below; worn with a "
            "well-fitted, short, normal-length blouse with elbow-length "
            "sleeves (never long or tunic-like) in a solid color picked "
            "from image 1's palette, with a modest neckline and a fully "
            "covered back (a closed round back neck, never open or deep), "
            "and the waist covered neatly by the saree drape. The whole "
            "look must be graceful, dignified and modest — nothing "
            "revealing or suggestive. "
        ),
    },
    # BLAZER (updated from the reference image of the three styles):
    #   - jacket length is pinned (BLAZER_LENGTH_DETAIL),
    #   - business / wedding trousers are a plain solid in the main colour
    #     of the blazer fabric ("trouser_colour_from_fabric": True),
    #   - business tie (NEW): plain solid in the main colour of the blazer
    #     fabric ("tie_colour_from_fabric": True), never the pattern,
    #   - wedding: shawl lapel jacket over a mandarin band-collar shirt
    #     (no bow tie) with a puff-flower pocket square.
    ("blazer", "business"): {
        "fabric_target": "blazer",
        "border": False,
        "trouser_colour_from_fabric": True,
        "tie_colour_from_fabric": True,
        "color_note": (
            "CRITICAL — business suits are commonly navy, charcoal, or "
            "black, but ignore that assumption: the blazer, including its "
            "lapel, must be in the colors of image 1 only. The shirt is "
            "plain white and unrelated to image 1. The necktie and the "
            "trousers use only the main colour of the blazer fabric, each "
            "as a plain solid with no pattern. "
        ),
        "garment": (
            "a formal business blazer — structured, single-breasted, notch "
            "lapel, sharply tailored shoulders, the hem " + BLAZER_LENGTH_DETAIL
            + ", buttoned closed — worn over a plain white collared shirt "
            "with a plain solid necktie in exactly the main colour of the "
            "blazer fabric (no pattern), and matching plain, solid, "
            "full-length trousers in exactly the main colour of the "
            "blazer fabric, with no pattern. "
        ),
    },
    ("blazer", "wedding"): {
        "fabric_target": "jacket",
        "border": False,
        "trouser_colour_from_fabric": True,
        "color_note": (
            "CRITICAL — tuxedo jackets are commonly black, but ignore that "
            "assumption: the entire jacket, including the shawl lapel, "
            "must be in the colors of image 1 only. The band-collar shirt "
            "and pocket square are plain and unrelated to image 1's "
            "pattern. The trousers use only the main colour of the jacket "
            "fabric, as a plain solid. "
        ),
        "garment": (
            "a formal tuxedo-style dinner jacket — single-breasted with a "
            "smooth SHAWL lapel (one continuous rounded curve, no notch), "
            "sharply tailored shoulders, one button fastened, the hem "
            + BLAZER_LENGTH_DETAIL + " — worn over a plain mandarin "
            "band-collar shirt (a short stand-up band collar closed with a "
            "row of small buttons, no necktie and no bow tie) in a plain "
            "solid light tone, with a plain white pocket square folded "
            "into a small puff-flower shape clearly visible in the chest "
            "pocket, and plain, solid, full-length trousers in exactly the "
            "main colour of the jacket fabric, with no pattern. "
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
            "relaxed shoulders, notch lapel, relaxed fit, the hem "
            + BLAZER_LENGTH_DETAIL + " — over a plain white collared shirt "
            "with the top button undone and no necktie, with plain dark "
            "full-length trousers. "
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
    "kurti_pant": "kurti with plain white pants",
    "shirt": "shirt",
    "pant": "pant",
    "blazer": "blazer",
}


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
        if garment_type == "kurti_pant":
            what = (
                "a kurti made from the fabric in image 1, paired with "
                "plain white pants"
            )
        else:
            noun = _GARMENT_NOUN.get(garment_type, "garment")
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

    # NEW (kurta / blazer, report 7): the limbs rule is stated right after
    # the POSE line when a pose is requested.
    pose_part = _pose_line(pose_text)
    if garment_type in KURTA_BLAZER and pose:
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
        prompt += CLOSING_SAREE if garment_type == "saree" else CLOSING

    # person_pose has no gender field (the person comes from the photo).
    if _is_child(gender):
        prompt += CHILD_GARMENT_LINE
    return prompt


# ----------------------------------------------------------------------
# SAREE RESOLVER PATH
#
# Step 1 (resolve): Python decides every known condition and produces ONE
#                   final text for each requirement.
# Step 2 (compose): the resolved texts are joined in a fixed order.
# The final prompt has no "unless" / "otherwise" / "if the pose ...".
# All wording lives in prompt_parts.py (variables) and pose_data.py.
# ----------------------------------------------------------------------

def _uses_saree_resolver(scenario, garment_type, use_garment_image):
    """True only for saree + fabric swatch + generated_person / face_photo."""
    return (
        garment_type == "saree"
        and not use_garment_image
        and scenario in SAREE_RESOLVER_SCENARIOS
    )


def _resolve_saree_instructions(
    scenario, gender, body_type, pose, camera_view, background,
    additional_style_note,
):
    """
    Resolution step. Returns an ordered dict of final texts, one per
    requirement. A requirement that does not apply is an empty string.
    """
    is_face = scenario == SCENARIO_FACE_PHOTO
    framing = get_framing(camera_view)
    person = _person_description(gender, body_type)

    # POSE (+ PALLU): the pose module owns both.
    pose_text, pallu_text = get_saree_pose_parts(pose, framing["pose_default"])

    # CAMERA: the face reference also needs "do not copy the crop of image 2".
    camera = P.CAMERA.format(
        shot=framing["shot"], shown=framing["shown"], fill=framing["fill"]
    )
    if is_face:
        camera += " " + framing["output_rule_face"].strip()

    # BACKGROUND: ONE of two texts, chosen here.
    description = BACKGROUND_DESCRIPTIONS.get(background) if background else None
    if description:
        background_text = P.BACKGROUND_SCENE.format(description=description)
    else:
        background_text = P.BACKGROUND_DEFAULT

    # STYLE NOTE: only when the user sent one.
    note = (additional_style_note or "").strip().rstrip(".")
    style_text = P.STYLE_NOTE.format(note=note) if note else ""

    # GARMENT: saree text (no pallu placement); child line when needed.
    garment_text = P.SAREE_GARMENT
    if _is_child(gender):
        garment_text += " " + CHILD_GARMENT_LINE.strip()

    return {
        "task": P.TASK,
        "images": P.IMAGES_FACE if is_face else P.IMAGES_GENERATED,
        "pose": P.POSE.format(pose_text=pose_text),
        "pallu": P.PALLU.format(pallu_text=pallu_text) if pallu_text else "",
        "subject": (P.SUBJECT_FACE if is_face else P.SUBJECT_GENERATED).format(
            person=person
        ),
        "garment": garment_text,
        "fabric": P.SAREE_FABRIC_RULES,
        "border": P.SAREE_BORDER_RULES,
        "camera": camera,
        "background": background_text,
        "lighting": P.LIGHTING,
        "realism": P.REALISM,
        "style": style_text,
        "final": P.MODESTY_FINAL_SAREE,
    }


# Fixed order of the final prompt. The final modesty rule is always last.
SAREE_PROMPT_ORDER = (
    "task", "images", "pose", "pallu", "subject", "garment", "fabric",
    "border", "camera", "background", "lighting", "realism", "style",
    "final",
)


def _compose_saree_prompt(resolved):
    """Composition step: joins the resolved texts in SAREE_PROMPT_ORDER."""
    return " ".join(
        resolved[key].strip() for key in SAREE_PROMPT_ORDER if resolved[key]
    ) + " "


def _build_saree_resolved(
    scenario, gender, body_type, pose, camera_view, background,
    additional_style_note,
):
    """Returns {"prompt","guidance","seed"} for the saree resolver path."""
    resolved = _resolve_saree_instructions(
        scenario, gender, body_type, pose, camera_view, background,
        additional_style_note,
    )
    prompt = _compose_saree_prompt(resolved)

    logger.info(
        "Saree resolver prompt built: version=%s scenario=%s pose=%s "
        "camera_view=%s background=%s pallu_owner=%s words=%s",
        P.SAREE_PROMPT_VERSION, scenario, pose, camera_view, background,
        "pose_parts" if resolved["pallu"] else "pose_text",
        len(prompt.split()),
    )
    logger.info("FINAL PROMPT: %s", prompt)
    return {
        "prompt": prompt,
        "guidance": GENERATED_GUIDANCE,
        "seed": GENERATED_SEED,
    }


# ----------------------------------------------------------------------
# POSE REFERENCE PATH
#
# The reference photo is image 0 and is EDITED: only the fabric changes.
# The pose / drape / person / background are NOT described in words (they
# are in the photo). Python only resolves what to keep and which optional
# parts apply; the wording is in prompt_parts.py (REF_* variables).
#
#   nothing optional sent         -> keep person, face, pose, drape,
#                                    blouse, framing, background, lighting
#   camera_view                   -> CAMERA line added (the existing
#                                    CAMERA_VIEW_INSTRUCTIONS text); the
#                                    framing is not kept; the ORIGINAL
#                                    background is kept, continued behind
#                                    the new angle (not made plain)
#   face_choice                   -> FACE line added, face not kept
#   background                    -> BACKGROUND + LIGHTING lines added,
#                                    background / lighting not kept
# ----------------------------------------------------------------------

def _resolve_pose_reference_instructions(
    use_face_reference, background, additional_style_note, camera_view=None,
):
    """
    Resolution step. Returns an ordered dict of final texts, one per
    requirement. A requirement that does not apply is an empty string.
    """
    description = BACKGROUND_DESCRIPTIONS.get(background) if background else None
    camera_text = get_camera_view_instruction(camera_view)
    use_camera = bool(camera_text)

    # What stays exactly as in the photo. A piece that is replaced by the
    # FACE / BACKGROUND line is left out, so KEEP never contradicts them.
    # With a camera_view the framing is not kept and the original
    # background is continued behind the new angle.
    kept = [P.REF_KEPT_BASE_CAMERA if use_camera else P.REF_KEPT_BASE]
    if not use_face_reference:
        kept.append(P.REF_KEPT_FACE)
    if not description:
        kept.append(P.REF_KEPT_SCENE_CAMERA if use_camera else P.REF_KEPT_SCENE)

    note = (additional_style_note or "").strip().rstrip(".")

    return {
        "task": P.REF_TASK,
        "images": P.REF_IMAGES_FACE if use_face_reference else P.REF_IMAGES,
        "keep": P.REF_KEEP.format(kept=", ".join(kept)),
        "camera": (
            P.REF_CAMERA.format(instruction=camera_text) if use_camera else ""
        ),
        "change": P.REF_CHANGE,
        "fabric": P.SAREE_FABRIC_RULES,
        "border": P.REF_BORDER_RULES,
        "blouse": P.REF_BLOUSE,
        "right_side": P.REF_RIGHT_SIDE,
        "face": P.REF_FACE if use_face_reference else "",
        "background": (
            P.REF_BACKGROUND.format(description=description) if description else ""
        ),
        # Lighting is changed only when the background is changed.
        "lighting": P.LIGHTING if description else "",
        "realism": P.REALISM,
        "style": P.STYLE_NOTE.format(note=note) if note else "",
        "final": P.MODESTY_FINAL_SAREE,
    }


# Fixed order of the final prompt. The final modesty rule is always last.
POSE_REFERENCE_PROMPT_ORDER = (
    "task", "images", "keep", "camera", "change", "fabric", "border",
    "blouse", "right_side", "face", "background", "lighting", "realism",
    "style", "final",
)


def _compose_pose_reference_prompt(resolved):
    """Composition step: joins the resolved texts in order."""
    return " ".join(
        resolved[key].strip()
        for key in POSE_REFERENCE_PROMPT_ORDER
        if resolved[key]
    ) + " "


def _build_pose_reference_prompt(
    garment_type, use_face_reference, background, additional_style_note,
    camera_view=None,
):
    """
    Returns {"prompt","guidance","seed"} for the pose reference path, or
    None if the garment has no pose reference prompt (today: saree only).
    """
    if garment_type != "saree":
        return None

    resolved = _resolve_pose_reference_instructions(
        use_face_reference, background, additional_style_note, camera_view
    )
    prompt = _compose_pose_reference_prompt(resolved)

    logger.info(
        "Pose reference prompt built: version=%s face_reference=%s "
        "camera_view=%s background=%s words=%s",
        P.POSE_REFERENCE_PROMPT_VERSION, use_face_reference, camera_view,
        background, len(prompt.split()),
    )
    logger.info("FINAL PROMPT: %s", prompt)
    return {
        "prompt": prompt,
        "guidance": GENERATED_GUIDANCE,
        "seed": GENERATED_SEED,
    }


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------

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


def _build_person_pose_kurti_prompt(
    pose, camera_view=None, background=None,
):
    """Short, priority-ordered instructions for person-photo kurti edits."""
    pose_text = _own_model_pose_text(
        pose, garment_type="kurti_pant", camera_view=camera_view
    )
    framing = get_framing(camera_view)
    keep_background = not background
    prompt = _task_line(
        SCENARIO_PERSON_POSE, "kurti_pant", False, keep_background
    )
    prompt += _pose_line(pose_text)
    dupatta_rule = (
        "For this pose, include a plain white dupatta draped over the head; "
        "keep it solid white and do not apply image 1's fabric to it. "
        if pose == "pallu_on_head"
        else "No dupatta. "
    )
    # A chair pose changes the person's perspective more than the standing
    # poses. Keep this lock local to that pose so the proven prompt for the
    # other kurti-pant poses remains byte-for-byte the same.
    cross_leg_identity_lock = (
        "CROSS-CHAIR IDENTITY LOCK: Copy the exact facial structure from image 2 "
        "— same eyes, eyebrows, nose, lips and face shape — and preserve the "
        "same slim shoulder, waist and hip widths when seated. Keep the same "
        "arm and leg thickness; do not make her fuller or wider because she is "
        "sitting. The kurti and plain white pants are the only garments visible; "
        "do not retain any source clothing or loose cloth from image 2. "
        if pose == "cross_leg_chair_recline"
        else ""
    )
    prompt += (
        "POSE PRIORITY: Change the woman's posture to exactly the pose above. "
        "Do not retain her original posture. "
        "LIMBS: Do not copy the arms, hands, legs or feet from image 2. Draw "
        "exactly two arms, two hands, two legs and two feet in the pose above; "
        "never add, duplicate or leave an extra hand, arm, leg or foot. "
        "SUBJECT: Generate one realistic " + framing["shot"]
        + " photograph of the same woman in image 2, "
        + framing["shown"] + ". Preserve her recognizable "
        "face, hair, skin tone, age, accessories and natural body build. Keep "
        "her original shoulder, waist and hip widths, torso length, height-to-"
        "width ratio, and arm and leg thickness; do not slim or widen her. "
        "Replace the clothes in image 2 completely; do not copy their color, "
        "print or garment design. "
        + cross_leg_identity_lock +
        "OUTFIT: Dress her in a modest Indian kurti with full-length sleeves "
        "reaching the wrists, paired with plain, solid white, full-length "
        "pants visible below the kurti and reaching the ankles. The pants are "
        "white and have no print. " + dupatta_rule +
        "FABRIC: Use image 1 only as the kurti fabric reference. Apply its "
        "actual colors, print, motif size and density across the kurti. Do "
        "not use image 1's fabric or pattern on the white pants. If image 1 "
        "has a distinct border, use it only as a narrow kurti hem and sleeve "
        "cuff trim; do not invent a border when none is shown. "
    )
    if keep_background:
        prompt += (
            "BACKGROUND: Keep the original place, objects, colors and lighting "
            "from image 2; extend it naturally and add a simple chair or low "
            "ledge only when the selected pose requires it. "
        )
    prompt += "Make the result a natural, realistic photograph. "
    return prompt


def _build_person_pose_shirt_prompt(
    pose, camera_view=None, background=None,
):
    """Priority-ordered shirt instructions for a posed person photo."""
    pose_text = _own_model_pose_text(
        pose, garment_type="shirt", camera_view=camera_view
    )
    # pallu_on_head describes a saree veil. For a shirt, retain the usable
    # standing / hand position but remove the contradictory head-covering
    # instruction, which can otherwise change the identity into a woman.
    if pose == "pallu_on_head":
        pose_text = (
            "standing upright facing the camera with the head upright and "
            "looking forward, both hands softly clasped together in front of "
            "the lower waist, with exactly two arms and two hands in total, "
            "and no head covering"
        )
    framing = get_framing(camera_view)
    keep_background = not background
    prompt = _task_line(
        SCENARIO_PERSON_POSE, "shirt", False, keep_background
    )
    prompt += _pose_line(pose_text)
    prompt += (
        "POSE PRIORITY: Change the person's posture to exactly the pose above. "
        "Do not retain the posture in image 2. "
        "LIMBS: Do not copy arms, hands, legs or feet from image 2. Draw "
        "exactly two arms, two hands, two legs and two feet in the pose above; "
        "never add, duplicate or leave an extra limb. "
        "SUBJECT: Generate one realistic " + framing["shot"]
        + " photograph of the same person in image 2, "
        + framing["shown"] + ". IDENTITY: Copy the person in image 2 exactly: "
        "the same face shape, eyes, eyebrows, nose, lips, skin tone, hair, "
        "age category, apparent gender presentation, accessories and natural "
        "body build. Do not turn a man or boy into a woman or girl, or a woman "
        "or girl into a man or boy. Keep the original "
        "shoulder, waist and hip widths, torso length, height-to-width ratio, "
        "and arm and leg thickness; do not slim or widen the person. "
        "Replace every source garment completely, including shorts, trousers "
        "or jeans; do not copy their colour, print, cut or fabric. "
        "OUTFIT: Dress the person in a properly fitted, collared button-up "
        "shirt. Sleeves, where the garment has them, must be full-length down "
        "to the wrist, straight and unrolled, unless the garment description "
        "above says otherwise. The shirt is worn with "
        "plain dark solid-color formal full-length trousers. The trousers "
        "must reach the ankles, fit naturally, and be newly generated even "
        "when image 2 shows shorts or trousers. They must not use image 1's "
        "fabric, pattern or print. "
        "FABRIC: Use image 1 only as the shirt fabric reference. Apply its "
        "actual colours, print, motif size and density across the entire "
        "shirt. The fabric must be clearly visible on the shirt, with its "
        "original hue, brightness and saturation. Do not use image 1's fabric, "
        "pattern or colour on the trousers, footwear, accessories, skin or "
        "background. " + FABRIC_RULES.format(target="shirt")
    )
    if keep_background:
        prompt += (
            "BACKGROUND: Keep the original place, objects, colours and lighting "
            "from image 2; extend it naturally and add a simple chair or low "
            "ledge only when the selected pose requires it. "
        )
    prompt += "Make the result a natural, realistic photograph. "
    return prompt


# ----------------------------------------------------------------------
# PERSON POSE: dedicated short prompt for kurta and blazer (NEW)
#
# Same idea as the kurti and shirt builders above: a short prompt, pose
# first. The garment wording, colour note, fabric rules and border rules
# come from GARMENT_SPECS (one owner), so nothing is written twice.
# CLOSING is used at the end ON PURPOSE: it contains the two anchors that
# garment_details.py needs (the sleeves sentence and the "Generate
# realistic shading" sentence for the dupatta), so folded sleeves and the
# dupatta options keep working exactly as before.
# ----------------------------------------------------------------------

# Words used when a pose is requested for a man's garment.
# pallu_on_head describes a saree veil, so for kurta / blazer the usable
# hands position is kept and the head covering is removed (same idea as the
# shirt builder).
PERSON_POSE_NO_HEAD_COVER = (
    "standing upright facing the camera with the head upright and "
    "looking forward, both hands softly clasped together in front of "
    "the lower waist, with exactly two arms and two hands in total, "
    "and no head covering"
)

# Part of the sleeve_adjust_stand sentence in pose_data.py. It says the
# sleeve stays down, which contradicts the folded_sleeves detail.
POSE_SLEEVE_DOWN_PHRASE = ", the sleeve staying fully down"

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
    """Pose wording for the kurta / blazer person_pose prompt."""
    pose_text = _own_model_pose_text(
        pose, garment_type, garment_style, garment_details, camera_view
    )
    if pose == "pallu_on_head":
        pose_text = PERSON_POSE_NO_HEAD_COVER
    if pose == "sleeve_adjust_stand" and "folded_sleeves" in (garment_details or []):
        pose_text = pose_text.replace(POSE_SLEEVE_DOWN_PHRASE, "")
    return pose_text


def _build_person_pose_spec_prompt(
    garment_type, garment_style, pose, camera_view=None, background=None,
    garment_details=None,
):
    """
    Short, priority-ordered prompt for a posed person photo with a kurta
    or a blazer. Returns the prompt text, or None if the garment spec does
    not exist.
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

    # 4. The fabric. The dupatta (kurta only, when requested) is NOT listed
    #    among the places the fabric is forbidden: its own wording in
    #    garment_details.py says it is cut from the same fabric.
    prompt += (
        "FABRIC: Use image 1 only as the " + target + " fabric reference. "
        "Apply its actual colours, print, motif size and density across "
        "the entire " + target + ", with its original hue, brightness and "
        "saturation. " + _fabric_forbidden_text(spec)
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
        prompt += _short_background(BACKGROUND_DESCRIPTIONS.get(background))

    # 6. Closing. Holds the anchors used by garment_details.py.
    prompt += CLOSING
    return prompt


def _build_own_model_spec_prompt(
    scenario, garment_type, garment_style, gender, body_type, pose=None,
    camera_view=None, garment_details=None, background=None,
):
    """
    NEW (reports 6, 7, 9, 10): short prompt for kurta / blazer on the
    face_photo path (face + pose + background together). The old own-model
    prompt was about 1000 words, so the background (at its end) and part of
    the body_type / pose were lost. Order = importance: pose, limbs, one
    person, subject, body build, background, outfit, fabric, closing.
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
    else:
        prompt += (
            "SUBJECT: image 0 is only a blank canvas (frame size). Generate "
            f"a brand-new, realistic {framing['shot']} photograph of "
            f"{_person_description(gender, body_type)}, with a sharp, "
            f"natural face, {framing['shown']}{framing['fill']}. "
        )

    description = BACKGROUND_DESCRIPTIONS.get(background) if background else None
    if description:
        prompt += _short_background(description)
    else:
        prompt += "BACKGROUND: a plain neutral studio background. "

    prompt += "OUTFIT: Dress the person in " + _garment_text_for_pose(
        spec["garment"], garment_type, pose
    )
    prompt += spec.get("color_note", "")
    prompt += (
        "FABRIC: Use image 1 only as the " + target + " fabric reference, "
        "with its actual colours, print, motif size and density. "
        + _fabric_forbidden_text(spec) + FABRIC_RULES.format(target=target)
    )
    if spec["border"]:
        prompt += BORDER_RULES.format(target=target)

    prompt += CLOSING  # holds the anchors used by garment_details.py
    if _is_child(gender):
        prompt += CHILD_GARMENT_LINE
    return prompt


def _uses_kurta_white_pant(garment_type, garment_style, use_garment_image):
    """True for the kurta styles in KURTA_WHITE_PANT_STYLES (fabric swatch only)."""
    return (
        not use_garment_image
        and garment_type == "kurta"
        and garment_style in KURTA_WHITE_PANT_STYLES
    )


def _replace_kurta_pant_phrase(prompt, garment_type, garment_style, use_garment_image):
    """
    person_photo (edit) route only. The tested kurta/plain prompt in
    prompts.py lets the pajama be "white, off-white, or a solid shade
    picked from the kurta's own color palette". That exact phrase is
    replaced in memory (prompts.py is never edited), so the prompt does not
    contain two different instructions for the pajama colour.
    If the phrase is not found (prompts.py was edited), a warning is
    logged and the prompt is returned unchanged.
    """
    if not _uses_kurta_white_pant(garment_type, garment_style, use_garment_image):
        return prompt
    if KURTA_PANT_OLD_PHRASE not in prompt:
        logger.warning(
            "kurta white pant: old phrase not found in the edit prompt "
            "(garment=%s style=%s)", garment_type, garment_style,
        )
        return prompt
    return prompt.replace(KURTA_PANT_OLD_PHRASE, KURTA_PANT_NEW_PHRASE, 1)


def _kurta_white_pant_line(garment_type, garment_style, use_garment_image):
    """
    person_photo (edit) route only: the one-sentence white pajama rule for
    the kurta styles in KURTA_WHITE_PANT_STYLES. Empty string otherwise.
    """
    if _uses_kurta_white_pant(garment_type, garment_style, use_garment_image):
        return KURTA_PANT_WHITE_LINE
    return ""


def _fabric_forbidden_text(spec):
    """
    Where image 1's fabric must NOT appear (kurta / blazer short prompts).
    Business blazer: the tie and the trousers take only the main COLOUR of
    the fabric, as a plain solid, never its pattern. Wedding blazer: the
    trousers do. Sherwani / Pathani: the churidar / salwar does.
    """
    if spec.get("tie_colour_from_fabric"):
        return (
            "Do not use image 1's pattern on the shirt, pocket square, "
            "footwear, accessories, skin or background. The necktie and "
            "the trousers use only the main colour of image 1 as a plain "
            "solid, with no pattern. "
        )
    if spec.get("trouser_colour_from_fabric"):
        return (
            "Do not use image 1's pattern on the shirt, tie, pocket "
            "square, footwear, accessories, skin or background. The "
            "trousers use only the main colour of image 1 as a plain "
            "solid, with no pattern. "
        )
    if spec.get("pant_colour_from_fabric"):
        return (
            "Do not use image 1's pattern on the churidar, salwar or "
            "trousers, footwear, accessories, skin or background. The "
            "lower garment uses only the main colour of image 1 as a "
            "plain solid, with no pattern. "
        )
    return (
        "Do not use image 1's fabric, pattern or colour on the trousers "
        "or pajama, any shirt or tie, footwear, accessories, skin or "
        "background. "
    )


def _apply_blazer_edit_changes(prompt, garment_type, garment_style, use_garment_image):
    """
    person_photo (edit) route only, blazer fabric requests. Replaces the
    exact phrases listed in BLAZER_EDIT_REPLACEMENTS in memory (jacket
    length, the business tie colour, and the wedding shirt / bow tie /
    pocket square wording), then adds the TROUSERS line for business and
    wedding and the TIE line for business. Other garments and
    garment_image requests are returned unchanged.
    """
    if use_garment_image or garment_type != "blazer":
        return prompt
    for old_text, new_text in BLAZER_EDIT_REPLACEMENTS.get(garment_style, []):
        if old_text in prompt:
            prompt = prompt.replace(old_text, new_text, 1)
        else:
            logger.warning(
                "blazer edit: phrase not found in the edit prompt "
                "(style=%s): %.60s", garment_style, old_text,
            )
    if garment_style in BLAZER_TROUSER_STYLES:
        prompt = prompt.rstrip() + " " + BLAZER_TROUSER_LINE
    if garment_style == "business":
        prompt = prompt.rstrip() + " " + BLAZER_TIE_LINE
    return prompt


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


def _append_shirt_fabric_final_rule(prompt):
    """Place shirt-only fabric boundaries after all prompt overrides."""
    before, marker, after = prompt.rpartition(MODESTY_FINAL)
    if not marker:
        return prompt + " " + SHIRT_FABRIC_FINAL_RULE
    return before + SHIRT_FABRIC_FINAL_RULE + marker + after


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
):
    """
    Main function used by the engine. Returns
    {"prompt", "guidance", "seed"}, or None if no prompt exists for the
    given garment_type / garment_style.

    use_face_reference is used only by the pose_reference scenario: True
    when a face_choice was sent (image 2 = the face to put on the photo).
    """
    # Reference photo of the pose -> edit prompt (fabric only; optional
    # camera_view, face and background on top of the photo).
    if scenario == SCENARIO_POSE_REFERENCE:
        return _build_pose_reference_prompt(
            garment_type, use_face_reference, background, additional_style_note,
            camera_view,
        )

    # Saree + generated_person / face_photo -> resolver path.
    if _uses_saree_resolver(scenario, garment_type, use_garment_image):
        return _build_saree_resolved(
            scenario, gender, body_type, pose, camera_view, background,
            additional_style_note,
        )

    # FLUX.2 Klein inconsistently followed the longer shared prompt for
    # person-photo kurti pose edits (often retaining the source outfit or pose).
    # Keep these top-priority requirements in one short, dedicated prompt.
    if (
        scenario == SCENARIO_PERSON_POSE
        and garment_type == "kurti_pant"
        and not use_garment_image
    ):
        prompt = _build_person_pose_kurti_prompt(
            pose, camera_view=camera_view, background=background
        )
        prompt = apply_garment_details(
            prompt, garment_type, garment_style, garment_details, MODE_OWN
        )
        base = {
            "prompt": _append_overrides(
                prompt, background, additional_style_note
            ),
            "guidance": GENERATED_GUIDANCE,
            "seed": GENERATED_SEED,
        }
        logger.info(
            "Prompt built: scenario=%s pose=%s camera_view=%s details=%s "
            "words=%s",
            scenario, pose, camera_view, garment_details,
            len(base["prompt"].split()),
        )
        logger.info("FINAL PROMPT: %s", base["prompt"])
        return base

    # Shirt pose edits must replace the complete outfit even when the source
    # photo has shorts, rolled sleeves, or a tucked shirt.  This route is
    # intentionally shirt-only; all other garment prompt paths stay unchanged.
    if (
        scenario == SCENARIO_PERSON_POSE
        and garment_type == "shirt"
        and not use_garment_image
    ):
        prompt = _build_person_pose_shirt_prompt(
            pose, camera_view=camera_view, background=background
        )
        prompt = apply_garment_details(
            prompt, garment_type, garment_style, garment_details, MODE_OWN
        )
        base = {
            "prompt": _append_shirt_fabric_final_rule(_append_overrides(
                prompt, background, additional_style_note
            )),
            "guidance": GENERATED_GUIDANCE,
            "seed": GENERATED_SEED,
        }
        logger.info(
            "Prompt built: scenario=%s pose=%s camera_view=%s details=%s "
            "words=%s",
            scenario, pose, camera_view, garment_details,
            len(base["prompt"].split()),
        )
        logger.info("FINAL PROMPT: %s", base["prompt"])
        return base

    # NEW: kurta and blazer pose / camera_view edits. The shared long prompt
    # made the model ignore the new pose and camera view (test reports of
    # 2026-10-09), so these two garments get the same short dedicated route
    # as kurti_pant and shirt. Other garments are not affected.
    # CHANGED (report 4): the background is written inside the builder (short
    # text), so _append_overrides gets background=None here.
    if (
        scenario == SCENARIO_PERSON_POSE
        and garment_type in PERSON_POSE_SPEC_GARMENTS
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

    # NEW (reports 6, 7, 9, 10): kurta / blazer with a face reference
    # (face + pose + background together) use the short own-model prompt.
    if (
        scenario in OWN_MODEL_SPEC_SCENARIOS
        and garment_type in PERSON_POSE_SPEC_GARMENTS
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
        # NEW: kurta (plain) pajama must be white. Both steps do nothing
        # for every other garment, so their prompts stay exactly as before.
        prompt = _replace_kurta_pant_phrase(
            prompt, garment_type, garment_style, use_garment_image
        )
        # NEW: blazer length / trousers / business tie / wedding details
        # (edit route).
        prompt = _apply_blazer_edit_changes(
            prompt, garment_type, garment_style, use_garment_image
        )
        # NEW (2026-10-10 reports 1, 2, 3): kurta length, trouser colour of
        # sherwani / pathani, two arms only, no fabric patch on the hand.
        prompt = _apply_kurta_edit_changes(
            prompt, garment_type, garment_style, use_garment_image
        )
        prompt += _kurta_white_pant_line(
            garment_type, garment_style, use_garment_image
        )
        prompt += _kurta_edit_extra_lines(
            garment_type, garment_style, use_garment_image
        )
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
    if garment_type == "shirt" and not use_garment_image:
        base["prompt"] = _append_shirt_fabric_final_rule(base["prompt"])

    logger.info(
        "Prompt built: scenario=%s pose=%s camera_view=%s details=%s "
        "pose_phrases_replaced=%s words=%s",
        scenario, pose, camera_view, garment_details, replaced,
        len(base["prompt"].split()),
    )
    logger.info("FINAL PROMPT: %s", base["prompt"])
    return base