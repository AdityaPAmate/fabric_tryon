"""Scenario-organized prompt data extracted from the existing project.

Source wording is copied from prompts.py and prompt_builder.py. This module
separates garment-owned data by scenario; scenario composition still uses
the existing shared prompt builder until the later migration step.
"""

GARMENT_TYPE = 'shirt'
GARMENT_STYLE_OPTIONS = {}

# Shirt-only final constraint, applied by shirt/builder.py after the shared
# scenario composition so later style/background notes cannot override it.
SHIRT_FABRIC_FINAL_RULE = (
    "FINAL FABRIC RULE: Apply image 1 only to the shirt, preserving its "
    "colors, pattern, scale and density. Keep image 1 completely off the "
    "background, trousers, footwear, accessories and skin. Follow any "
    "shirt artwork or border placement instructions already given. "
)


def fabric_forbidden_text(spec):
    """Keep image 1 off non-shirt regions without contradicting its target."""
    return (
        "Do not use image 1's fabric, pattern or colours on the trousers "
        "or pajama, footwear, accessories, skin or background. The shirt "
        "is the only fabric target. "
    )

SHIRT_FACE_BODY_LINES = {
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

# Exact existing edit-mode prompt(s), including seed and guidance.
GARMENT_PROMPTS = {
    GARMENT_TYPE: {
        "default": {
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing (shirt, t-shirt, "
                "kurta, or anything else), replace it entirely with a new, properly fitted, "
                "collared button-up shirt. "

                "Use only the exact colors and pattern shown in "
                "image 1 — same type (check, stripe, print, weave, or plain), same scale and "
                "proportions — do not invent, add, brighten, darken, or alter any color or "
                "design element not visible in image 1. The motifs must repeat as densely "
                "and closely spaced as they appear in image 1, with the same small amount "
                "of empty space between them — do not spread them further apart or enlarge "
                "the gaps between motifs. "

                "Do not preserve the original garment's collar style, sleeve shape, drape, "
                "folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new shirt structure from scratch: proper collar, natural sleeve "
                "length, and a fit that follows the person's actual body shape in this pose "
                "— not too loose, not too tight. "

                "The new shirt's sleeves must be full-length and fully extended down to "
                "the wrist in a natural, straight, unrolled state — never folded, cuffed, "
                "or rolled up at the forearm or elbow. "

                "Replace any shorts, trousers, jeans, or other lower-body clothing in image "
                "0 with newly generated, plain dark solid-color formal full-length trousers "
                "that reach the ankles and fit naturally. The trousers must be created even "
                "when image 0 already shows full-length trousers. Do not use image 1's "
                "fabric, print, pattern, or colours on the trousers. "

                "Generate new, realistic shading, folds, and shadows appropriate for this "
                "new shirt and trousers on this body and pose — consistent with the lighting "
                "direction in the rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in "
                "the same pose and background, now wearing a properly fitted new shirt made "
                "exactly from image 1's fabric."
            ),
            "guidance": 7.0,
            "seed": 42,
        },
    }
}

# Exact existing garment specifications used by the shared own-model and
# person-pose builders. Values remain source expressions from prompt_builder.py.

GARMENT_SPECS = {
    ('shirt', 'default'): {
        "fabric_target": "shirt",
        "border": False,
        "garment": (
            "a properly fitted, collared button-up shirt, not too loose "
            "and not too tight, worn with plain dark solid-color formal "
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
        "builder": '_build_person_pose_shirt_prompt',
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
