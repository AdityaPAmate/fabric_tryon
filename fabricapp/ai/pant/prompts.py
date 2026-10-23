"""Scenario-organized prompt data extracted from the existing project.

Source wording is copied from prompts.py and prompt_builder.py. This module
separates garment-owned data by scenario; scenario composition still uses
the existing shared prompt builder until the later migration step.
"""

GARMENT_TYPE = 'pant'
GARMENT_STYLE_OPTIONS = {}

# Exact existing edit-mode prompt(s), including seed and guidance.
GARMENT_PROMPTS = {
    GARMENT_TYPE: {
        "default": {
            "prompt": (
                "Edit image 0. Keep the person's face, skin tone, hairstyle, expression, "
                "hands, arms, body pose, and the entire background from image 0 completely "
                "unchanged — sharp, fully in focus, pixel-identical where possible. "

                "Do NOT touch, alter, redesign, recolor, or regenerate the person's shirt, "
                "top, kurta, or any upper-body garment in image 0 — keep it exactly as it "
                "already appears, with its original color, pattern, fit, folds, and shadows "
                "completely unchanged. "

                "Regardless of what type of lower-body garment the person is currently "
                "wearing in image 0 — half-pant, shorts, three-fourth pant, jeans, casual "
                "trousers, or a full-length formal pant already — convert it into a proper "
                "formal, full-length straight-cut trouser reaching all the way down to the "
                "ankles. If the original lower-wear is short (half-pant, shorts, "
                "three-fourth length) and leaves part of the legs bare below the hem, do "
                "NOT leave that area as exposed or bare skin under any circumstance — "
                "extend the new formal pant fully down to the ankles, following the "
                "person's actual leg shape and pose, with a clean, pressed, straight-leg "
                "formal cut (not skinny, not baggy, not cargo-style, no visible pockets "
                "flaps or drawstrings) — never keep the original short length. If the "
                "original lower-wear is already a full-length pant, keep its existing "
                "length and fit as-is and only formalize the cut if it currently looks "
                "casual (e.g. cargo, joggers, denim) into a plain straight-cut formal "
                "trouser shape. "

                "The ONLY visual element to change from image 0 is the pant's fabric "
                "color and pattern (and, per the paragraph above, its length/style if it "
                "was originally a short or casual lower-wear). Do not change where the "
                "pant sits on the waist, and do not alter anything about the upper-body "
                "garment, footwear, face, pose, or background. Replace the pant's fabric "
                "look with the exact fabric shown in image 1. "

                "Use only the exact colors and pattern shown in image 1 for the new pant "
                "fabric — same type (check, stripe, print, weave, or plain), same scale "
                "and proportions relative to the pant's size in image 0 — do not invent, "
                "add, brighten, darken, or alter any color or design element not visible "
                "in image 1. The motifs must repeat as densely and closely spaced as they "
                "appear in image 1, with the same small amount of empty space between "
                "them — do not spread them further apart or enlarge the gaps between "
                "motifs. "

                "The final pant color and pattern must match image 1 exactly, as-is — do "
                "not shift the hue, saturation, or brightness compared to image 1. "

                "Generate new, realistic folds, creases, and shadows for this new formal "
                "pant on the body in this exact pose, so the fabric looks naturally "
                "draped and worn — not flat or pasted on. Keep the same lighting "
                "direction already present in image 0. "

                "Do not change anything else in the image — not the shirt/top, not the "
                "footwear, not the face, not the pose, not the background, not the "
                "framing or crop of the photo. Result must look like one real, unedited "
                "photograph of the same person in the exact same pose, shirt, and "
                "background, now wearing a formal full-length pant made exactly from "
                "image 1's fabric."
            ),
            "guidance": 7.0,
            "seed": 42,
        },
    }
}

# Exact existing garment specifications used by the shared own-model and
# person-pose builders. Values remain source expressions from prompt_builder.py.

GARMENT_SPECS = {
    ('pant', 'default'): {
        "fabric_target": "pant",
        "border": False,
        "garment": (
            "a formal, full-length, straight-cut trouser reaching all the "
            "way to the ankles, clean and pressed (not skinny, not baggy, "
            "no cargo pockets), with naturally draped folds. Wear it with "
            "a plain white collared shirt — the shirt is NOT made from "
            "image 1's fabric, only the trouser is. "
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
        "builder": '_build_own_model_prompt',
        "garment_specs": GARMENT_SPECS,
        "source": "prompt_builder.py",
    },
    "face_photo": {
        "builder": '_build_own_model_prompt',
        "garment_specs": GARMENT_SPECS,
        "source": "prompt_builder.py",
    },
    "generated_person": {
        "builder": '_build_own_model_prompt',
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
