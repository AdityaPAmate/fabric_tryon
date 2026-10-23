"""Scenario-organized prompt data extracted from the existing project.

Source wording is copied from prompts.py and prompt_builder.py. This module
separates garment-owned data by scenario; scenario composition still uses
the existing shared prompt builder until the later migration step.
"""

GARMENT_TYPE = 'blazer'
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
    "ending at the base of the seat, about level with the wrists of the "
    "hanging arms (a short, fitted jacket length, never reaching the "
    "mid-thigh), with the trousers clearly visible below the hem"
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

# Exact common garment-image prompt and generation defaults from prompts.py.
GARMENT_IMAGE_PROMPT = GARMENT_IMAGE_PROMPT = (
    "Edit image 0. Keep the same person/subject, face, skin tone, hairstyle, "
    "expression, hands, arms, background, and body pose from image 0 "
    "completely unchanged — sharp, fully in focus, not altered in any way. "
    "Replace whatever garment the subject in image 0 is currently wearing "
    "with the exact garment shown in image 1 — same cut, style, color, "
    "pattern, and length as image 1, fitted naturally to the subject's body "
    "and pose in image 0. Do not invent or alter any design element not "
    "visible in image 1. Generate realistic new shading, folds, and shadows "
    "consistent with the lighting in image 0. Result must look like one "
    "real, unedited photograph."
)
GARMENT_IMAGE_GUIDANCE = GARMENT_IMAGE_GUIDANCE = 7.0
GENERATED_GARMENT_IMAGE_BODY = GENERATED_GARMENT_IMAGE_BODY = (
    "Dress this new person in the exact garment shown in image 1 — same "
    "cut, style, color, pattern, and length as image 1 — fitted naturally "
    "to the body and pose. Do not invent or alter any design element not "
    "visible in image 1. If the garment in image 1 covers only the upper or "
    "lower body, complete the outfit with a plain, modest, coordinating "
    "garment. Generate realistic shading, folds, and shadows. The result "
    "must look like one real, unedited photograph. "
)
GARMENT_IMAGE_SEED = GARMENT_IMAGE_SEED = 42

# Scenario routing/source map from the existing prompt_builder.py.
# person_pose and own-model outputs are assembled dynamically from shared
# text plus this garment's GARMENT_SPECS; their prompt wording is not one
# standalone string in the current project.
SCENARIO_PROMPTS = {
    "person_photo": {
        "prompt_data": GARMENT_PROMPTS[GARMENT_TYPE],
        "source": "prompts.py: GARMENT_PROMPTS",
    },
    "person_pose": {
        "builder": '_build_person_pose_spec_prompt',
        "garment_specs": GARMENT_SPECS,
        "source": "prompt_builder.py",
    },
    "face_photo": {
        "builder": '_build_own_model_spec_prompt',
        "garment_specs": GARMENT_SPECS,
        "source": "prompt_builder.py",
    },
    "generated_person": {
        "builder": '_build_own_model_spec_prompt',
        "garment_specs": GARMENT_SPECS,
        "source": "prompt_builder.py",
    },
    "pose_reference": None,  # Existing pose-reference route is saree-only.
    "garment_image": {
        "edit_prompt": GARMENT_IMAGE_PROMPT,
        "edit_guidance": GARMENT_IMAGE_GUIDANCE,
        "edit_seed": GARMENT_IMAGE_SEED,
        "generated_person_body": GENERATED_GARMENT_IMAGE_BODY,
    },
}
