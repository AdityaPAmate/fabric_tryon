"""
Stage: Prompt builder.
Single place that decides WHICH prompt is used for a request, based on
the situation (scenario). The engine only calls build_prompt() and
never needs to know how prompts are made.

Scenarios:
    person_photo      -> user uploaded a person photo. The tested
                         GARMENT_PROMPTS are used exactly as they are.
    face_photo        -> no person photo, but a predefined face was
                         chosen. Face addendum + tested prompt.
    generated_person  -> no person photo and no face. A separate,
                         dedicated prompt is built from GARMENT_SPECS
                         below (model generates the whole person).

To support a new garment in generated_person: add one entry to
GARMENT_SPECS. To support a new situation: add a scenario + one
builder function. The engine does not change.
"""

from .prompts import (
    GARMENT_STYLE_OPTIONS,
    GARMENT_IMAGE_PROMPT,
    GARMENT_IMAGE_GUIDANCE,
    GARMENT_IMAGE_SEED,
    get_prompt_config,
    get_camera_view_instruction,
    get_background_instruction,
    get_own_model_instruction,
)

SCENARIO_PERSON_PHOTO = "person_photo"
SCENARIO_FACE_PHOTO = "face_photo"
SCENARIO_GENERATED_PERSON = "generated_person"

GENERATED_GUIDANCE = 7.0
GENERATED_SEED = 42


def detect_scenario(has_person_image, face_choice):
    """Decides which scenario applies for this request."""
    if has_person_image:
        return SCENARIO_PERSON_PHOTO
    if face_choice:
        return SCENARIO_FACE_PHOTO
    return SCENARIO_GENERATED_PERSON


# ----------------------------------------------------------------------
# Small helpers used only by the generated_person scenario
# ----------------------------------------------------------------------

def _gender_word(gender):
    return {"men": "man", "women": "woman", "boy": "boy", "girl": "girl"}.get(gender, "person")


def _build_word(body_type):
    return {"slim": "slim", "trim": "athletic, toned", "plus": "plus-size"}.get(body_type, "slim")


def _subject_block(gender, body_type):
    """Describes the new person the model must generate."""
    return (
        "SUBJECT SETUP: image 0 is only a blank, plain neutral canvas that "
        "sets the frame size — there is no person on it. Generate a "
        f"brand-new, realistic, full-body photograph of a young, "
        f"{_build_word(body_type)} Indian {_gender_word(gender)} with a "
        "natural, realistic face, standing in a natural, relaxed pose "
        "facing the camera, on a plain neutral studio background (unless a "
        "different background is requested at the end of this prompt), "
        "shown fully from head to feet and filling the frame. "
    )


# Shared fabric rules — same intent as the tested prompts.
FABRIC_RULES = (
    "Use only the exact colors and pattern shown in image 1 for the {target} "
    "fabric — same type (check, stripe, print, weave, or plain), same scale "
    "and proportions — do not invent, add, brighten, darken, or alter any "
    "color or design element not visible in image 1. The motifs must repeat "
    "as densely and closely spaced as they appear in image 1, with the same "
    "small amount of empty space between them — do not spread them further "
    "apart. "
)

# Only for garments where a border/accent band makes sense.
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
    "wrist, straight and unrolled — never folded or rolled up — unless the "
    "garment description above says otherwise. Generate realistic shading, "
    "folds, and shadows for the garment on this body and pose. The result "
    "must look like one real, unedited photograph of a fully and modestly "
    "clothed person."
)

GENERATED_GARMENT_IMAGE_BODY = (
    "Dress this new person in the exact garment shown in image 1 — same "
    "cut, style, color, pattern, and length as image 1 — fitted naturally "
    "to the body and pose. Do not invent or alter any design element not "
    "visible in image 1. If the garment in image 1 covers only the upper or "
    "lower body, complete the outfit with a plain, modest, coordinating "
    "garment so the person is fully and modestly clothed. Generate "
    "realistic shading, folds, and shadows. The result must look like one "
    "real, unedited photograph."
)


# ----------------------------------------------------------------------
# GARMENT_SPECS — one entry per garment (and style). Add new garments here.
# Keys: (garment_type, style_key) — style_key is "default" if the garment
# has no styles. Fields:
#   garment       : what the person wears (structure + lower garment)
#   fabric_target : name used in the fabric rules
#   border        : True if the border/accent-band rule applies
#   color_note    : optional "ignore the stereotype color" rule
# NOT YET TESTED against the real API — first version, to be tuned after
# reviewing real outputs (same way the tested prompts were tuned).
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
            "loose-fitting. Below it, a matching straight-cut churidar/"
            "salwar-style pant reaching the ankles in a plain solid color "
            "(white, off-white, or a solid shade from the kurti's "
            "palette), never patterned. No dupatta. "
        ),
    },
    ("shirt", "default"): {
        "fabric_target": "shirt",
        "border": False,
        "garment": (
            "a properly fitted, collared button-up shirt, not too loose "
            "and not too tight, worn with plain dark solid-color formal "
            "trousers. "
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
            "dark solid-color necktie, and matching plain dark trousers. "
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
            "trousers. "
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
            "no necktie, with plain dark trousers. "
        ),
    },
}


def _get_garment_spec(garment_type, garment_style):
    """Looks up the spec entry for a garment (and style, if it has styles)."""
    style_key = garment_style if garment_type in GARMENT_STYLE_OPTIONS else "default"
    return GARMENT_SPECS.get((garment_type, style_key))


def _build_generated_person_prompt(garment_type, garment_style, use_garment_image, gender, body_type):
    """Builds the dedicated prompt for the generated_person scenario."""
    subject = _subject_block(gender, body_type)

    if use_garment_image:
        return subject + GENERATED_GARMENT_IMAGE_BODY

    spec = _get_garment_spec(garment_type, garment_style)
    if spec is None:
        return None

    target = spec["fabric_target"]
    prompt = subject + "Dress this new person in " + spec["garment"]
    prompt += spec.get("color_note", "")
    prompt += FABRIC_RULES.format(target=target)
    if spec["border"]:
        prompt += BORDER_RULES.format(target=target)
    prompt += CLOSING
    return prompt


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------

def _build_base(scenario, garment_type, garment_style, use_garment_image, gender, body_type):
    """Returns {"prompt","guidance","seed"} for the scenario, or None."""
    if scenario == SCENARIO_GENERATED_PERSON:
        prompt = _build_generated_person_prompt(
            garment_type, garment_style, use_garment_image, gender, body_type
        )
        if prompt is None:
            return None
        return {"prompt": prompt, "guidance": GENERATED_GUIDANCE, "seed": GENERATED_SEED}

    # person_photo / face_photo both start from the tested prompts.
    if use_garment_image:
        base = {
            "prompt": GARMENT_IMAGE_PROMPT,
            "guidance": GARMENT_IMAGE_GUIDANCE,
            "seed": GARMENT_IMAGE_SEED,
        }
    else:
        base = get_prompt_config(garment_type, garment_style)
        if base is None:
            return None
        base = dict(base)  # copy — never modify the tested data

    if scenario == SCENARIO_FACE_PHOTO:
        base["prompt"] = get_own_model_instruction(gender, body_type) + " " + base["prompt"]
    return base


def _append_overrides(prompt, camera_view, background, additional_style_note):
    """Adds camera_view / background / style-note text at the end."""
    camera_text = get_camera_view_instruction(camera_view)
    if camera_text:
        prompt += " " + camera_text

    background_text = get_background_instruction(background)
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

    base["prompt"] = _append_overrides(
        base["prompt"], camera_view, background, additional_style_note
    )
    return base