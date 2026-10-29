"""Scenario-organized prompt data extracted from the existing project.

Source wording is copied from prompts.py and prompt_builder.py. This module
separates garment-owned data by scenario; scenario composition still uses
the existing shared prompt builder until the later migration step.
"""

GARMENT_TYPE = 'blazer'

POSE_LIMBS_RULE = True
GARMENT_STYLE_OPTIONS = {'blazer': ['business', 'wedding', 'casual']}

# Exact existing edit-mode prompt(s), including seed and guidance.
GARMENT_PROMPTS = {
    GARMENT_TYPE: {
        "business": {
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new formal business suit blazer worn OVER a plain white "
                "collared dress shirt, with a plain dark solid-color necktie visible at the "
                "collar. The blazer is a structured, single-breasted jacket with a notch "
                "lapel, sharply tailored shoulders, and buttoned closed with its single "
                "front button fastened (not left open), hitting at roughly hip length. "
                "The shirt collar points and a small triangle of shirt/tie must be visible "
                "at the neckline exactly as in a buttoned suit jacket. "

                "The white shirt and the necktie are NEW elements you are adding — they are "
                "plain white (shirt) and a plain dark solid color (tie), completely unrelated "
                "to image 1's fabric; do not put image 1's pattern on the shirt or tie. "

                "CRITICAL — fabric color rule: business suits are commonly navy, charcoal, or "
                "black, but you must IGNORE that assumption completely. The blazer (including "
                "its lapel) must use ONLY the exact colors and pattern shown in image 1 — same "
                "type (solid, pinstripe, check, herringbone, or plain), same scale and "
                "proportions — even if that color is unusual for a business suit (e.g. bright, "
                "light, or colorful). Do not shift the blazer toward navy, charcoal, grey, or "
                "black unless that is literally the color already present in image 1. Do not "
                "invent, add, brighten, darken, or alter any color or design element not "
                "visible in image 1. The pattern must repeat as densely and closely spaced as "
                "it appears in image 1, with the same small amount of empty space between "
                "elements — do not spread it further apart or enlarge the gaps. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new business-blazer structure from scratch: correct notch lapel, "
                "correct structured shoulder line, correct hip-length hem, buttoned closed, "
                "and a fit that follows the person's actual body shape in this pose — "
                "tailored and fitted, not loose or baggy. "

                "The new blazer's sleeves must be full-length and fully extended down to the "
                "wrist in a natural, straight, unrolled state — never folded, cuffed, or "
                "rolled up at the forearm or elbow. "

                "Generate new, realistic shading, folds, and shadows appropriate for this new "
                "blazer, shirt, and tie on this body and pose — consistent with the lighting "
                "direction in the rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in "
                "the same pose and background, now wearing a properly fitted new business "
                "suit — blazer made exactly from image 1's fabric colors and pattern, "
                "buttoned closed, over a white shirt and dark tie."
            ),
            "guidance": 7.0,
            "seed": 42,
        },

        "wedding": {
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new formal tuxedo-style dinner jacket worn OVER a plain "
                "white collared dress shirt, with a plain black bow tie visible at the "
                "collar, and a plain white pocket square in the chest pocket. The jacket's "
                "STRUCTURE (not color) is: single-breasted, with a smooth SHAWL lapel — a "
                "single continuous rounded curve from the collar down to the button, with no "
                "notch cut into it, and no separate collar piece — sharply tailored "
                "shoulders, a single front button fastened (not left open), hitting at "
                "roughly hip length. This is a Western-style tuxedo shawl lapel shape, NOT a "
                "stand-up mandarin/nehru collar and NOT a bandhgala-style buttoned placket. "

                "The white shirt, black bow tie, and white pocket square are NEW elements "
                "you are adding — plain white (shirt), plain black (bow tie), plain white "
                "(pocket square), completely unrelated to image 1's fabric; do not put "
                "image 1's pattern on the shirt, bow tie, or pocket square. "

                "CRITICAL — fabric color rule: tuxedo jackets are commonly plain black, but "
                "you must IGNORE that assumption completely. The ENTIRE jacket, including "
                "the shawl lapel itself, must use ONLY the exact colors and pattern shown in "
                "image 1 — same type (solid, subtle weave, check, or plain), same scale and "
                "proportions — even if that color is not black (e.g. it may be a light color, "
                "a bright color, or a patterned fabric). Do NOT render the jacket or lapel in "
                "plain black, navy, or any other color unless that is literally the color "
                "already present in image 1 — do not treat 'tuxedo' as meaning 'must be "
                "black'. Do not invent, add, brighten, darken, or alter any color or design "
                "element not visible in image 1. The pattern must repeat as densely and "
                "closely spaced as it appears in image 1, with the same small amount of empty "
                "space between elements — do not spread it further apart or enlarge the gaps. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new tuxedo structure from scratch: correct shawl lapel shape, correct "
                "structured shoulder line, correct hip-length hem, single button fastened, "
                "and a fit that follows the person's actual body shape in this pose — "
                "tailored and fitted, not loose or baggy. "

                "The new jacket's sleeves must be full-length and fully extended down to the "
                "wrist in a natural, straight, unrolled state — never folded, cuffed, or "
                "rolled up at the forearm or elbow. "

                "Generate new, realistic shading, folds, and shadows appropriate for this new "
                "jacket, shirt, bow tie, and pocket square on this body and pose — consistent "
                "with the lighting direction in the rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in "
                "the same pose and background, now wearing a properly fitted new tuxedo-style "
                "jacket with a shawl lapel, made exactly from image 1's fabric colors and "
                "pattern, buttoned closed, over a white shirt with a black bow tie and pocket "
                "square."
            ),
            "guidance": 7.0,
            "seed": 42,
        },

        "casual": {
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new casual unstructured blazer worn OPEN and UNBUTTONED "
                "(not fastened), over a plain white collared shirt with the top button "
                "undone and no necktie. The blazer has soft, relaxed shoulders (no sharp "
                "structured padding), a notch lapel, a relaxed comfortable fit that is not "
                "tightly tailored, and a hem reaching roughly hip length. Because it is worn "
                "open, both edges of the blazer hang naturally apart, clearly showing the "
                "plain white shirt underneath the full length of the torso. "

                "The white shirt underneath is a NEW element you are adding — plain white, "
                "completely unrelated to image 1's fabric; do not put image 1's pattern on "
                "the shirt. Do not add any necktie or bow tie. "

                "CRITICAL — fabric color rule: casual blazers are commonly grey, beige, or "
                "navy, but you must IGNORE that assumption completely. The blazer (including "
                "its lapel) must use ONLY the exact colors and pattern shown in image 1 — "
                "same type (solid, check, textured weave, or plain), same scale and "
                "proportions — even if that color is unusual for a casual blazer (e.g. "
                "bright, light, or colorful). Do not shift the blazer toward grey, beige, "
                "navy, or any other color unless that is literally the color already present "
                "in image 1. Do not invent, add, brighten, darken, or alter any color or "
                "design element not visible in image 1. The pattern must repeat as densely "
                "and closely spaced as it appears in image 1, with the same small amount of "
                "empty space between elements — do not spread it further apart or enlarge "
                "the gaps. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new casual-blazer structure from scratch: correct relaxed notch "
                "lapel, correct soft shoulder line, correct hip-length hem, worn open and "
                "unbuttoned, and a fit that follows the person's actual body shape in this "
                "pose — relaxed, not stiffly tailored, but not baggy either. "

                "The new blazer's sleeves must be full-length and fully extended down to the "
                "wrist in a natural, straight, unrolled state — never folded, cuffed, or "
                "rolled up at the forearm or elbow. "

                "Generate new, realistic shading, folds, and shadows appropriate for this new "
                "open blazer and shirt on this body and pose — consistent with the lighting "
                "direction in the rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in "
                "the same pose and background, now wearing a properly fitted new casual "
                "blazer made exactly from image 1's fabric colors and pattern, worn open "
                "over a plain white shirt with no tie."
            ),
            "guidance": 7.0,
            "seed": 42,
        },
    }
}

# Exact existing garment specifications used by the shared own-model and
# person-pose builders. Values remain source expressions from prompt_builder.py.
BLAZER_LENGTH_DETAIL = (
    "ending at the base of the seat, above mid-thigh, with a fitted jacket length"
)
GARMENT_SPECS = {
    ('blazer', 'business'): {
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
    ('blazer', 'wedding'): {
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
    ('blazer', 'casual'): {
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
    }
}
# Garment-image prompting is shared by fabricapp.ai.garment_image.




BLAZER_TROUSER_STYLES = ("business", "wedding")

BLAZER_TROUSER_LINE = (
    "TROUSERS (replace the trousers of image 0): plain, solid, "
    "straight-cut, full-length trousers down to the ankles, crisply "
    "pressed, in exactly the main colour of the blazer fabric from "
    "image 1, with no pattern, check, stripe or texture. Only the colour "
    "is taken from image 1, never its pattern. "
)

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



# Garment-specific back-view detail rules migrated from scenario_composer.py.
BACK_VIEW_POSES = ("back_turn_hair_touch", "back_showing_pallu")

def garment_text_for_pose(garment_text, pose):
    if pose not in BACK_VIEW_POSES:
        return garment_text
    # Describe hidden front construction without requiring it to be visible.
    garment_text = garment_text.replace(
        "clearly visible in the chest pocket", "in the front chest pocket, hidden in this rear view"
    )
    return garment_text + (
        "VIEW: show the jacket's back with its fabric pattern and natural seams. "
        "The front lapels, shirt front, buttons, tie and pocket square remain "
        "on the front of the outfit, out of view rather than drawn on its back. "
    )


def fabric_forbidden_text(spec):
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
    return (
        "Do not use image 1's fabric, pattern or colour on the trousers "
        "or pajama, any shirt or tie, footwear, accessories, skin or "
        "background. "
    )
