"""
Stage: Prompt data for each garment type.
This file holds ONLY data (prompt text + generation settings) that has
already been tested and tuned. Do not edit the prompt wording here
unless you have re-tested it — small wording changes can change the
output quality significantly.

Structure:
    GARMENT_PROMPTS[garment_type][style_key] -> {"prompt", "guidance", "seed"}

Garment types with no real subtype (kurta, shirt, etc.) use a single
"default" style_key. Garment types with real subtypes (e.g. blazer)
list each subtype as its own key instead of "default". This keeps the
lookup logic in views.py identical for every garment_type, whether or
not it has subtypes.
"""

# Which garment types require a garment_style, and what values are
# valid for each. Garment types NOT listed here do not need/accept a
# garment_style value at all.
GARMENT_STYLE_OPTIONS = {
    "blazer": ["business", "wedding", "casual"],
}


def get_prompt_config(garment_type, garment_style=None):
    """
    Single-responsibility lookup used by views.py.

    Returns the {"prompt", "guidance", "seed"} dict for the given
    garment_type (+ garment_style, if that garment_type has subtypes),
    or None if garment_type / garment_style is not recognized.
    """
    garment_data = GARMENT_PROMPTS.get(garment_type)
    if garment_data is None:
        return None

    # Garment types without real subtypes always use "default".
    # Garment types with subtypes (see GARMENT_STYLE_OPTIONS) must be
    # looked up by the actual style key.
    style_key = garment_style if garment_type in GARMENT_STYLE_OPTIONS else "default"

    return garment_data.get(style_key)


GARMENT_PROMPTS = {
    "kurta": {
        "default": {
            # Men's kurta + pajama, tested and working (was kurta.py)
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing (shirt, t-shirt, "
                "kurta, or anything else), replace it entirely with a new, traditional Indian "
                "men's kurta — a straight-cut garment extending down to roughly mid-thigh or "
                "knee length, with a simple mandarin/band collar (or a plain round neckline, "
                "no wide shirt-style collar), a short front placket with only two or three "
                "buttons near the neck (not a full button-up front), and straight side slits "
                "at the hem. "

                "If any part of the person's legs below the kurta hem is visible in image 0 "
                "(whether originally covered by pants, jeans, a lungi, or anything else), do "
                "NOT leave that area as bare, exposed, or nude skin under any circumstance. "
                "Instead, generate a matching kurta-pajama (a simple, straight-cut traditional "
                "pajama trouser) covering the legs down to the ankles, in a plain solid color "
                "that coordinates naturally with the kurta — white, off-white, or a solid shade "
                "picked from the kurta's own color palette — with a simple realistic fabric "
                "drape and natural folds, never patterned or bright, and never the same "
                "check/stripe/print pattern as the kurta fabric itself. "

                "Use only the exact colors and pattern shown in "
                "image 1 for the kurta fabric — same type (check, stripe, print, weave, or plain), "
                "same scale and proportions — do not invent, add, brighten, darken, or alter any "
                "color or design element not visible in image 1. The motifs must repeat as densely "
                "and closely spaced as they appear in image 1, with the same small amount "
                "of empty space between them — do not spread them further apart or enlarge "
                "the gaps between motifs. "

                "First, examine image 1 carefully to see whether it contains a single "
                "uniform repeating pattern across its whole surface, or whether it has "
                "two visually distinct zones — a main body pattern plus a separate, "
                "denser decorative border or accent strip (often in different colors "
                "or motifs, usually running along one edge of the fabric). "
                "If image 1 has only one uniform pattern, apply that same single "
                "pattern evenly across the entire kurta, exactly as already described "
                "above, and ignore the rest of this paragraph. "
                "If image 1 does have a separate, more elaborate border design, you "
                "must reproduce BOTH zones on the kurta, not just one: apply the main "
                "body pattern across the bulk of the kurta (chest, back, upper "
                "sleeves), and apply the border design — using its own distinct "
                "colors and motifs exactly as shown in image 1, not blended or "
                "simplified into the main pattern — as a clearly visible accent band "
                "along the kurta's bottom hem and around the sleeve cuffs, matching "
                "how a real kurta made from this fabric would be tailored so the "
                "border falls at the finished edges of the garment. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new kurta structure from scratch: correct kurta collar, correct kurta "
                "length, and a fit that follows the person's actual body shape in this pose "
                "— straight and loose-fitting, not tailored tight like a shirt. "

                "The new kurta's sleeves must be full-length and fully extended down to "
                "the wrist in a natural, straight, unrolled state — never folded, cuffed, "
                "or rolled up at the forearm or elbow. "

                "Generate new, realistic shading, folds, and shadows appropriate for this "
                "new kurta and pajama on this body and pose — consistent with the lighting "
                "direction in the rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in "
                "the same pose and background, fully and modestly clothed, now wearing a "
                "properly fitted new kurta made exactly from image 1's fabric, paired with "
                "a plain matching pajama."
            ),
            "guidance": 7.0,
            "seed": 42,
        },
    },

    "kurti_pant": {
        "default": {
            # Women's kurti + matching pant, tested and working
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing (saree, salwar suit, "
                "western dress, top, or anything else), replace it entirely with a new, "
                "traditional Indian women's kurti paired with a matching straight-cut pant "
                "(churidar or straight salwar-pant style). "

                "The kurti must be a simple, modest, straight or A-line cut extending down to "
                "roughly mid-thigh or knee length, with a plain round or V-neck neckline (no "
                "deep or low-cut neckline), and sleeves that are either elbow-length or "
                "full-length (choose whichever drapes more naturally given the person's current "
                "arm position in image 0) — never sleeveless. "

                "If any part of the person's legs is visible below the kurti hem in image 0 "
                "(whether originally covered by a saree, jeans, a skirt, or anything else), do "
                "NOT leave that area as bare, exposed, or nude skin under any circumstance. "
                "Instead, generate a matching straight-cut pant (churidar/salwar style) covering "
                "the legs down to the ankles, in a plain solid color that coordinates naturally "
                "with the kurti — white, off-white, or a solid shade picked from the kurti's own "
                "color palette — with a simple realistic fabric drape and natural folds, never "
                "patterned or bright, and never the same check/stripe/print pattern as the "
                "kurti fabric itself. "

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
                "fitted new kurti made exactly from image 1's fabric, paired with a plain "
                "matching pant."
            ),
            "guidance": 7.0,
            "seed": 42,
        },
    },

    "shirt": {
        "default": {
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing (shirt, t-shirt, "
                "kurta, or anything else), replace it entirely with a new, properly fitted, "
                "collared button-up shirt."

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

                "Generate new, realistic shading, folds, and shadows appropriate for this "
                "new shirt on this body and pose — consistent with the lighting direction "
                "in the rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in "
                "the same pose and background, now wearing a properly fitted new shirt made "
                "exactly from image 1's fabric."
            ),
            "guidance": 7.0,
            "seed": 42,
        },
    },

    "pant": {
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
    },

    "saree": {
        "default": {
            "prompt": (
                "Edit image 0. Keep the same woman, face, hairstyle, pose, and background from "
                "image 0 unchanged. Render the face, eyes, hair strands, and skin texture sharp "
                "and in full focus, matching the clarity and detail level of image 0 — do not "
                "soften, smooth, or blur the face or any other part of the image. "
                "Replace her saree fabric with the fabric from image 1 — same pink base color, "
                "gold polka dots, and the parrot-and-floral artwork, rendered with sharp, crisp "
                "detail, not soft or blurred. "
                "Place the parrot-and-floral artwork only on the pallu end-piece, the part that "
                "falls over the shoulder — do not repeat it along the main body's bottom hem. "
                "Along the main body's bottom hem, use only a plain, narrow, evenly repeating gold "
                "border, matching the border style and proportions shown in image 2 — not large "
                "decorative artwork there. Do not generate a new person or new scene, and do not "
                "reduce overall image sharpness."
            ),
            "guidance": 7.0,
            "seed": 42,
        },
    },

    # ---- NEW: blazer, first garment_type to actually use garment_style ----
    "blazer": {
        "business": {
            # DRAFT — not yet tested against the real API. Wording may
            # need tuning after the first real output is seen.
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new formal business blazer — a structured, single-breasted, "
                "notch-lapel jacket with clean, sharply tailored shoulders, hitting at roughly "
                "hip length, worn open or with a single button closed at the waist, over a "
                "plain white or light-colored collared shirt visible at the neckline and cuffs. "

                "Use only the exact colors and pattern shown in image 1 for the blazer fabric — "
                "same type (solid, pinstripe, check, herringbone, or plain), same scale and "
                "proportions — do not invent, add, brighten, darken, or alter any color or "
                "design element not visible in image 1. The pattern must repeat as densely and "
                "closely spaced as it appears in image 1, with the same small amount of empty "
                "space between elements — do not spread it further apart or enlarge the gaps. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new business-blazer structure from scratch: correct notch lapel, correct "
                "structured shoulder line, correct hip-length hem, and a fit that follows the "
                "person's actual body shape in this pose — tailored and fitted, not loose or "
                "baggy. "

                "The new blazer's sleeves must be full-length and fully extended down to the "
                "wrist in a natural, straight, unrolled state — never folded, cuffed, or rolled "
                "up at the forearm or elbow. "

                "Generate new, realistic shading, folds, and shadows appropriate for this new "
                "blazer on this body and pose — consistent with the lighting direction in the "
                "rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in the "
                "same pose and background, now wearing a properly fitted new business blazer "
                "made exactly from image 1's fabric."
            ),
            "guidance": 7.0,
            "seed": 42,
        },

        "wedding": {
            # DRAFT — not yet tested. Modeled on an Indian-wedding-style
            # bandhgala/nehru-collar blazer look, since a plain Western
            # business blazer is not typically what "wedding blazer"
            # means in this context. Re-check wording with the user
            # before trusting the output.
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new formal wedding-style blazer (bandhgala-inspired) — a "
                "structured, single-breasted jacket with a stand-up mandarin/nehru collar "
                "(no lapel), a full row of small decorative buttons down the front placket, "
                "sharply tailored shoulders, and a hem reaching roughly mid-hip to upper-thigh "
                "length. "

                "Use only the exact colors and pattern shown in image 1 for the blazer fabric — "
                "same type (solid, brocade-style print, check, weave, or plain), same scale and "
                "proportions — do not invent, add, brighten, darken, or alter any color or "
                "design element not visible in image 1. The pattern must repeat as densely and "
                "closely spaced as it appears in image 1, with the same small amount of empty "
                "space between elements — do not spread it further apart or enlarge the gaps. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new wedding-blazer structure from scratch: correct mandarin collar, "
                "correct button placket, correct structured shoulder line, correct hem length, "
                "and a fit that follows the person's actual body shape in this pose — tailored "
                "and fitted, not loose or baggy. "

                "The new blazer's sleeves must be full-length and fully extended down to the "
                "wrist in a natural, straight, unrolled state — never folded, cuffed, or rolled "
                "up at the forearm or elbow. "

                "Generate new, realistic shading, folds, and shadows appropriate for this new "
                "blazer on this body and pose — consistent with the lighting direction in the "
                "rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in the "
                "same pose and background, now wearing a properly fitted new wedding blazer "
                "made exactly from image 1's fabric."
            ),
            "guidance": 7.0,
            "seed": 42,
        },

        "casual": {
            # DRAFT — not yet tested.
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new casual unstructured blazer — soft, relaxed shoulders "
                "(no sharp structured padding), a notch lapel, a relaxed fit that is not "
                "tightly tailored, and a hem reaching roughly hip length, worn open over a "
                "plain t-shirt or collared shirt visible at the neckline. "

                "Use only the exact colors and pattern shown in image 1 for the blazer fabric — "
                "same type (solid, check, textured weave, or plain), same scale and "
                "proportions — do not invent, add, brighten, darken, or alter any color or "
                "design element not visible in image 1. The pattern must repeat as densely and "
                "closely spaced as it appears in image 1, with the same small amount of empty "
                "space between elements — do not spread it further apart or enlarge the gaps. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new casual-blazer structure from scratch: correct relaxed notch lapel, "
                "correct soft shoulder line, correct hip-length hem, and a fit that follows the "
                "person's actual body shape in this pose — relaxed, not stiffly tailored, but "
                "not baggy either. "

                "The new blazer's sleeves must be full-length and fully extended down to the "
                "wrist in a natural, straight, unrolled state — never folded, cuffed, or rolled "
                "up at the forearm or elbow. "

                "Generate new, realistic shading, folds, and shadows appropriate for this new "
                "blazer on this body and pose — consistent with the lighting direction in the "
                "rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in the "
                "same pose and background, now wearing a properly fitted new casual blazer "
                "made exactly from image 1's fabric."
            ),
            "guidance": 7.0,
            "seed": 42,
        },
    },
}