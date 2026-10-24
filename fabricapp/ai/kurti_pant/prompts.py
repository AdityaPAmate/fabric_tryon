"""Scenario-organized prompt data extracted from the existing project.

Source wording is copied from prompts.py and prompt_builder.py. This module
separates garment-owned data by scenario; scenario composition still uses
the existing shared prompt builder until the later migration step.
"""

GARMENT_TYPE = 'kurti_pant'
POSE_LIMBS_RULE = True
TASK_PHRASE = (
    "a kurti made from the fabric in image 1, paired with plain white pants"
)
GARMENT_STYLE_OPTIONS = {}

# Exact existing edit-mode prompt(s), including seed and guidance.
GARMENT_PROMPTS = {
    GARMENT_TYPE: {
        "default": {
            # Women's kurti + plain white pant.
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing (saree, salwar suit, "
                "western dress, top, or anything else), replace it entirely with a new, "
                "traditional Indian women's kurti paired with plain, solid white, straight-cut pants "
                "(churidar or straight salwar-pant style). "

                "The kurti must be a simple, modest, straight or A-line cut extending down to "
                "roughly mid-thigh or knee length, with a plain round or V-neck neckline (no "
                "deep or low-cut neckline), and full-length sleeves reaching down to the wrists "
                "— never sleeveless. "

                "If any part of the person's legs is visible below the kurti hem in image 0 "
                "(whether originally covered by a saree, jeans, a skirt, or anything else), do "
                "NOT leave that area as bare, exposed, or nude skin under any circumstance. "
                "Instead, generate plain, solid white, straight-cut pants covering the legs down "
                "to the ankles, with natural folds. The pants must remain white and must not use "
                "image 1's fabric, colors, print or pattern; image 1's fabric is for the kurti only. "

                "Do not add a dupatta, stole, or scarf unless one is already clearly present and "
                "unchanged from image 0 — if there is no dupatta in image 0, do not invent one. "

                "Use only the exact colors and pattern shown in image 1 for the kurti fabric — "
                "same type (check, stripe, print, weave, or plain), same scale and proportions — "
                "do not invent, add, brighten, darken, or alter any color or design element not "
                "visible in image 1. The motifs must repeat as densely and closely spaced as "
                "they appear in image 1, with the same small amount of empty space between "
                "them — do not spread them further apart or enlarge the gaps between motifs. "

                "First, examine image 1 carefully to see whether it contains a single uniform "
                "repeating pattern across its whole surface, or whether it has two visually "
                "distinct zones — a main body pattern plus a separate, denser decorative "
                "border or accent strip (often in different colors or motifs, usually running "
                "along one edge of the fabric). "
                "If image 1 has only one uniform pattern, apply that same single pattern "
                "evenly across the entire kurti, exactly as already described above, and "
                "ignore the rest of this paragraph. "
                "If image 1 does have a separate, more elaborate border design, you must "
                "reproduce BOTH zones on the kurti, not just one: apply the main body pattern "
                "across the bulk of the kurti (front, back, upper sleeves), and apply the "
                "border design — using its own distinct colors and motifs exactly as shown in "
                "image 1, not blended or simplified into the main pattern — as a clearly "
                "visible accent band along the kurti's bottom hem, sleeve cuffs, and neckline "
                "trim, matching how a real kurti made from this fabric would be tailored so "
                "the border falls at the finished edges of the garment. "

                "Do not preserve the original garment's neckline style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new kurti structure from scratch: correct kurti neckline, correct kurti "
                "length, and a fit that follows the person's actual body shape in this pose — "
                "straight or A-line and comfortably loose-fitting, not tailored tight like a "
                "western top. "

                "Generate new, realistic shading, folds, and shadows appropriate for this new "
                "kurti and pant on this body and pose — consistent with the lighting direction "
                "in the rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in the "
                "same pose and background, fully and modestly clothed, now wearing a properly "
                "fitted new kurti made exactly from image 1's fabric, paired with plain, solid "
                "white pants."
            ),
            "guidance": 7.0,
            "seed": 42,
        },
    }
}

# Exact existing garment specifications used by the shared own-model and
# person-pose builders. Values remain source expressions from prompt_builder.py.

GARMENT_SPECS = {
    ('kurti_pant', 'default'): {
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
    }
}
# Garment-image prompting is shared by fabricapp.ai.garment_image.
