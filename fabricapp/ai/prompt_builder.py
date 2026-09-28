"""
Stage: Prompt builder.
Single place that decides WHICH prompt is used for a request, based on
the situation (scenario). The engine only calls build_prompt() and
never needs to know how prompts are made.

Scenarios:
    person_photo      -> user uploaded a person photo. The tested
                         GARMENT_PROMPTS are used exactly as they are
                         (they already contain the no-bare-legs rule),
                         plus ONE short preserve line at the end.
    face_photo        -> no person photo, but a predefined face was
                         chosen. image 0 = blank canvas, image 2 = face
                         reference. Uses the dedicated own-model prompt.
    generated_person  -> no person photo and no face. Dedicated
                         own-model prompt built from GARMENT_SPECS.

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
    get_camera_view_instruction,
)

logger = logging.getLogger("fabricapp")

SCENARIO_PERSON_PHOTO = "person_photo"
SCENARIO_FACE_PHOTO = "face_photo"
SCENARIO_GENERATED_PERSON = "generated_person"

GENERATED_GUIDANCE = 7.0
GENERATED_SEED = 42

CHILD_AGE = 12  # boy / girl are generated as 12-year-old children


def detect_scenario(has_person_image, face_choice):
    """Decides which scenario applies for this request."""
    if has_person_image:
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
# no-bare-legs rule, so this is NOT added to them.
MODESTY_RULE = (
    "The person must be fully and modestly clothed: never show bare legs "
    "or thighs. An upper-body garment (kurti, kurta, shirt, blazer) must "
    "always be worn with a full-length plain trouser, pant, churidar or "
    "pajama reaching the ankles. "
)

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
        "BACKGROUND OVERRIDE: this takes priority over any earlier "
        "instruction to keep the background unchanged. Replace the entire "
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


def _subject_block(gender, body_type):
    """Describes the new person the model must generate (no face reference)."""
    return (
        "SUBJECT SETUP: image 0 is only a blank, plain neutral canvas that "
        "sets the frame size — there is no person on it. Generate a "
        "brand-new, realistic, full-body photograph of "
        f"{_person_description(gender, body_type)}, with a natural, "
        "realistic, sharp face with clearly visible eyes, standing in a "
        "natural, relaxed pose facing the camera, on a plain neutral studio "
        "background (unless a different background is requested at the end "
        "of this prompt), shown fully from head to feet and filling the "
        "frame. "
    )


def _subject_block_with_face(gender, body_type):
    """Same as _subject_block, but image 2 is a reference photo of the face."""
    return (
        "SUBJECT SETUP: image 0 is only a blank, plain neutral canvas that "
        "sets the frame size — there is no person on it. Image 2 is a "
        "reference photo of a real person's face. Generate a brand-new, "
        "realistic, FULL-BODY photograph of this SAME person, "
        f"{_person_description(gender, body_type)}, standing in a natural, "
        "relaxed pose facing the camera, on a plain neutral studio "
        "background (unless a different background is requested at the end "
        "of this prompt), shown fully from head to feet. "
        "FACE AND HAIR MUST BE COPIED EXACTLY FROM IMAGE 2: same facial "
        "structure, eyes, eyebrows, nose, lips, same skin tone and "
        "brightness, same hair colour, hair length and hairstyle, and the "
        "same facial hair if any (if image 2 has jet-black hair, the "
        "output must have jet-black hair, not brown). The face must be "
        "evenly lit with soft, neutral white light — no warm or orange "
        "cast, no dark shadow — sharp, with clearly visible eyes. Do NOT "
        "output only a face or a close-up, and do not copy the crop of "
        "image 2: the output must be a complete head-to-feet photograph. "
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
            "with the pallu (end-piece) falling over the shoulder, worn "
            "with a well-fitted short-sleeved blouse in a solid color "
            "picked from image 1's palette. If image 1 has a special "
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


def _build_own_model_prompt(
    garment_type, garment_style, use_garment_image, gender, body_type, has_face_reference
):
    """
    Builds the dedicated prompt used by generated_person and face_photo.
    has_face_reference=True means image 2 is a face photo (face_photo).
    """
    if has_face_reference:
        subject = _subject_block_with_face(gender, body_type)
    else:
        subject = _subject_block(gender, body_type)

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
        prompt += CLOSING

    if _is_child(gender):
        prompt += CHILD_GARMENT_LINE
    return prompt


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------

def _build_base(scenario, garment_type, garment_style, use_garment_image, gender, body_type):
    """Returns {"prompt","guidance","seed"} for the scenario, or None."""
    if scenario in (SCENARIO_GENERATED_PERSON, SCENARIO_FACE_PHOTO):
        prompt = _build_own_model_prompt(
            garment_type,
            garment_style,
            use_garment_image,
            gender,
            body_type,
            has_face_reference=(scenario == SCENARIO_FACE_PHOTO),
        )
        if prompt is None:
            return None
        return {"prompt": prompt, "guidance": GENERATED_GUIDANCE, "seed": GENERATED_SEED}

    # person_photo: start from the tested prompts (never modified).
    if use_garment_image:
        return {
            "prompt": GARMENT_IMAGE_PROMPT,
            "guidance": GARMENT_IMAGE_GUIDANCE,
            "seed": GARMENT_IMAGE_SEED,
        }

    base = get_prompt_config(garment_type, garment_style)
    if base is None:
        return None
    return dict(base)  # copy — never modify the tested data


def _append_overrides(prompt, camera_view, background, additional_style_note):
    """Adds camera_view / background / style-note text at the very end."""
    camera_text = get_camera_view_instruction(camera_view)
    if camera_text:
        prompt += " " + camera_text

    background_text = _background_instruction(background)
    if background_text:
        prompt += " " + background_text

    if additional_style_note:
        prompt += (
            " ADDITIONAL USER INSTRUCTION (apply only if it does not "
            "contradict the rules above): " + additional_style_note
        )
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
):
    """
    Main function used by the engine. Returns
    {"prompt", "guidance", "seed"}, or None if no prompt exists for the
    given garment_type / garment_style.
    """
    base = _build_base(
        scenario, garment_type, garment_style, use_garment_image, gender, body_type
    )
    if base is None:
        return None

    prompt = base["prompt"].rstrip() + " "

    if scenario == SCENARIO_PERSON_PHOTO:
        # Tested prompts already forbid bare legs. Only one short line added.
        prompt += PERSON_PRESERVE_LINE
        if use_garment_image:
            # GARMENT_IMAGE_PROMPT has no leg rule, so add the short one.
            prompt += MODESTY_RULE
    else:
        # Own-model scenarios: short modesty rule for every gender.
        prompt += MODESTY_RULE
        if scenario == SCENARIO_FACE_PHOTO:
            prompt += FACE_KEEP_LINE

    base["prompt"] = _append_overrides(
        prompt, camera_view, background, additional_style_note
    )

    logger.info(
        "Prompt built: scenario=%s words=%s",
        scenario, len(base["prompt"].split()),
    )
    return base