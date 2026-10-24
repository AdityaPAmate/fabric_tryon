"""Scenario-organized prompt data extracted from the existing project.

Source wording is copied from prompts.py and prompt_builder.py. This module
separates garment-owned data by scenario; scenario composition still uses
the existing shared prompt builder until the later migration step.
"""

GARMENT_TYPE = 'shirt'
GARMENT_STYLE_OPTIONS = {}

# Used by the shared scenario assembly so the first instruction identifies a
# button-up shirt rather than only the broad word "shirt".
TASK_PHRASE = (
    "a properly fitted collared button-up shirt made from the fabric in image 1"
)

# Shirt-only final constraint, applied by shirt/builder.py after the shared
# scenario composition so later style/background notes cannot override it.
SHIRT_FABRIC_FINAL_RULE = (
    "FINAL FABRIC RULE: Apply image 1 only to the shirt, preserving its "
    "colors, pattern, scale and density. Keep image 1 completely off the "
    "background, trousers, footwear, accessories and skin. Follow any "
    "shirt artwork or border placement instructions already given. "
)

# Face-reference generation starts from a blank canvas.  State the whole
# outfit explicitly so a sampled image cannot omit the lower half while the
# model is also trying to satisfy a full-body pose and a new background.
SHIRT_COVERAGE_RULE = (
    "OUTFIT COVERAGE: create a conventional adult menswear catalogue outfit: "
    "an opaque, buttoned, full-length-sleeve collared shirt closed from collar "
    "to hem; plain opaque formal trousers from the natural waist to the ankles; "
    "and ordinary closed footwear. Keep the stance and expression professional. "
)

# Cloudflare error 3030 is an output-safety rejection, which is known only
# after the provider samples an image.  The engine uses this deterministic
# shirt-only fallback on its one alternate-seed retry; it does not change a
# request that succeeds on the configured seed.
SHIRT_SAFETY_FALLBACK_RULE = (
    "RETRY PRESENTATION: render a conventional adult men's business catalogue "
    "photograph. The opaque button-up shirt is fully buttoned and covers the "
    "torso to the hips. Plain opaque formal trousers cover from waist to ankles, "
    "with closed footwear. Keep the pose calm, upright and professional. "
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
# Garment-image prompting is shared by fabricapp.ai.garment_image.
