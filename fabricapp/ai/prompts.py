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
    "kurta": ["plain", "sherwani", "pathani", "jodhpuri"],
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
        "plain": {
            # CORRECTED this session — length was ambiguous ("mid-thigh
            # or knee"), which let the model drift too long. Now pinned
            # to just above the knee only.
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing (shirt, t-shirt, "
                "kurta, or anything else), replace it entirely with a new, traditional Indian "
                "men's kurta — a straight-cut garment extending down to just above the knee "
                "(NOT mid-thigh, NOT below the knee — the hem must end a few inches above the "
                "kneecap), with a simple mandarin/band collar (or a plain round neckline, no "
                "wide shirt-style collar), a short front placket with only two or three "
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
                "length ending just above the knee, and a fit that follows the person's actual "
                "body shape in this pose — straight and loose-fitting, not tailored tight like "
                "a shirt. "

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

        "sherwani": {
            # CORRECTED this session — length made much more explicit
            # (was drifting too short/kurta-like). Length is the single
            # biggest defining feature vs. a plain kurta.
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new formal sherwani — a long, coat-like outer garment that "
                "is DRAMATICALLY LONGER than an ordinary kurta: it must extend well past the "
                "knee, down toward mid-calf, roughly two to three times the length from waist "
                "to a normal kurta's hem. This extreme length is the single most important, "
                "non-negotiable feature of a sherwani — if the hem ends at or above the knee, "
                "it is WRONG and must be redone longer. It has a stand-up mandarin/bandhgala "
                "collar (no lapel, no notch), a full single column of small decorative buttons "
                "running the entire length of the front placket from neck to hem, and a torso "
                "that is fitted and tailored with visible waist suppression (not loose like a "
                "casual kurta), with the coat flaring only slightly below the waist into its "
                "long skirt. "

                "If any part of the person's legs below the sherwani hem is visible in "
                "image 0, do NOT leave that area as bare, exposed, or nude skin under any "
                "circumstance. Instead, generate a matching churidar — a fitted trouser that "
                "is close to the leg through the thigh and calf and gathers into soft "
                "bunched folds just above the ankle — in a plain solid color that "
                "coordinates naturally with the sherwani (white, off-white, or a solid shade "
                "picked from the sherwani's own color palette), never patterned or bright, "
                "and never the same pattern as the sherwani fabric itself. "

                "CRITICAL — fabric color rule: sherwanis are commonly seen in black, maroon, "
                "or gold, but you must IGNORE that assumption completely. The sherwani must "
                "use ONLY the exact colors and pattern shown in image 1 — same type (solid, "
                "check, stripe, print, weave, or plain), same scale and proportions — even if "
                "that color is unusual for a sherwani (e.g. bright, light, or colorful). Do "
                "not shift the sherwani toward black, maroon, gold, or any other color unless "
                "that is literally the color already present in image 1. Do not invent, add, "
                "brighten, darken, or alter any color or design element not visible in image "
                "1. The pattern must repeat as densely and closely spaced as it appears in "
                "image 1, with the same small amount of empty space between elements — do "
                "not spread it further apart or enlarge the gaps. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new sherwani structure from scratch: correct mandarin/bandhgala "
                "collar, correct full-length button column, and above all the correct "
                "dramatically long coat length reaching well past the knee toward mid-calf, "
                "with a fit that follows the person's actual body shape in this pose — fitted "
                "through the torso, not loose or baggy. "

                "The new sherwani's sleeves must be full-length and fully extended down to "
                "the wrist in a natural, straight, unrolled state — never folded, cuffed, or "
                "rolled up at the forearm or elbow. "

                "Generate new, realistic shading, folds, and shadows appropriate for this new "
                "sherwani and churidar on this body and pose — consistent with the lighting "
                "direction in the rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in "
                "the same pose and background, fully and modestly clothed, now wearing a "
                "properly fitted new sherwani, extending well past the knee toward mid-calf, "
                "made exactly from image 1's fabric colors and pattern, paired with a plain "
                "matching churidar."
            ),
            "guidance": 7.0,
            "seed": 42,
        },

        "pathani": {
            # CORRECTED this session — collar was wrongly written as
            # "round/band" (that's a different kurta style); a real
            # Pathani kurta has a classic SHIRT collar. Pockets now
            # specify flaps. Salwar width made much more explicit.
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new Pathani-style kurta — a loose, relaxed, straight-cut "
                "garment (not fitted to the body) extending to roughly mid-thigh or knee "
                "length, with a classic SHIRT-style pointed collar (like a formal button-up "
                "shirt collar, NOT a round/mandarin/band collar), TWO rectangular patch "
                "pockets with a buttoned or plain flap covering the top of each pocket, "
                "positioned one on each side of the upper chest, and a front placket with a "
                "few buttons near the neck (not a full button-up front). "

                "If any part of the person's legs below the kurta hem is visible in image 0, "
                "do NOT leave that area as bare, exposed, or nude skin under any "
                "circumstance. Instead, generate a matching Pathani salwar — a VERY LOOSE, "
                "voluminous, pleated trouser that is dramatically wider than a normal kurta "
                "pajama through the thigh and seat (with visible extra fabric bunching at the "
                "waist), then narrows and gathers into soft folds toward a cuffed ankle — in a "
                "plain solid color that coordinates naturally with the kurta (commonly the "
                "same tone as the kurta itself, or a solid shade picked from the kurta's own "
                "color palette), never patterned or bright, and never the same pattern as the "
                "kurta fabric itself. This salwar must look noticeably baggier and wider than "
                "a regular straight kurta-pajama — that extra volume is the defining feature "
                "of a Pathani suit. "

                "CRITICAL — fabric color rule: Pathani suits are commonly seen in plain "
                "white or beige, but you must IGNORE that assumption completely. The kurta "
                "must use ONLY the exact colors and pattern shown in image 1 — same type "
                "(solid, check, stripe, print, weave, or plain), same scale and proportions "
                "— even if that color is unusual for a Pathani suit (e.g. bright, dark, or "
                "colorful). Do not shift the kurta toward white, beige, or any other color "
                "unless that is literally the color already present in image 1. Do not "
                "invent, add, brighten, darken, or alter any color or design element not "
                "visible in image 1. The pattern must repeat as densely and closely spaced "
                "as it appears in image 1, with the same small amount of empty space between "
                "elements — do not spread it further apart or enlarge the gaps. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new Pathani-kurta structure from scratch: correct shirt-style pointed "
                "collar, correct flapped chest patch pockets, correct loose relaxed cut, "
                "correct length, and a fit that follows the person's actual body shape in "
                "this pose — deliberately loose and relaxed, never tailored tight. "

                "The new kurta's sleeves must be full-length and fully extended down to the "
                "wrist in a natural, straight, unrolled state — never folded, cuffed, or "
                "rolled up at the forearm or elbow. "

                "Generate new, realistic shading, folds, and shadows appropriate for this new "
                "kurta and voluminous salwar on this body and pose — consistent with the "
                "lighting direction in the rest of the photo. "

                "Result must look like one real, unedited photograph of the same person in "
                "the same pose and background, fully and modestly clothed, now wearing a "
                "properly fitted new Pathani kurta with a shirt-style collar and flapped "
                "chest pockets, made exactly from image 1's fabric colors and pattern, "
                "paired with a noticeably wide, baggy, plain matching salwar."
            ),
            "guidance": 7.0,
            "seed": 42,
        },

        "jodhpuri": {
            # CORRECTED again this session, based on a real reference
            # photo: (1) explicitly forbids any extra kurta/tunic-like
            # layer visible below the jacket hem — jacket must transition
            # directly to the trouser at the waist; (2) trouser is now
            # plain/solid, matching the jacket's COLOR ONLY, no pattern
            # or texture; (3) wrinkle rule made per-garment and specific
            # (elbow crease on jacket, knee crease on trouser, crisp
            # everywhere else on both).
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new Jodhpuri-style bandhgala jacket — a structured, "
                "single-breasted coat with sharply tailored shoulders (like a blazer, not a "
                "loose kurta), a stand-up mandarin/bandhgala collar (no lapel, no notch), a "
                "full single column of small buttons down the front placket, one small welt "
                "or flap chest pocket, two flap pockets at the hip level, and a hem reaching "
                "roughly hip length (shorter than a sherwani, longer than a regular shirt), "
                "fitted closely to the body. "

                "CRITICAL — no extra layer rule: the jacket must sit directly against the "
                "body and end cleanly at its own hip-length hem, transitioning straight into "
                "the waistband of the trouser underneath. Do NOT generate any additional "
                "visible garment layer below or peeking out from under the jacket's hem — no "
                "long kurta, tunic, undershirt hem, or any extra fabric extending past the "
                "jacket's own hemline. Only the jacket above the waist and the trouser below "
                "the waist should be visible, exactly like a Western suit jacket worn over "
                "trousers, just with a bandhgala collar instead of a lapel. "

                "CRITICAL — fit and finish rule: a Jodhpuri jacket is famous for its crisp, "
                "razor-sharp, almost FLAT tailored finish, with the fabric lying smooth and "
                "taut against the body — it is NOT loosely draped and does NOT have heavy "
                "wrinkling or multiple soft folds across the chest, back, or torso. The only "
                "folds that should appear on the jacket are small, natural creases exactly at "
                "the elbow bend where the arm is angled — everywhere else on the jacket "
                "(chest, torso, back, shoulders) must remain smooth and essentially flat. "

                "If any part of the person's legs below the jacket hem is visible in image "
                "0, do NOT leave that area as bare, exposed, or nude skin under any "
                "circumstance. Instead, generate a matching fitted formal trouser — a "
                "straight-cut or slim-fit tailored trouser (not baggy, not a churidar, not a "
                "salwar) reaching down to the ankles. The trouser must be a PLAIN, SOLID "
                "color with NO pattern, print, check, stripe, or visible woven texture of any "
                "kind — completely smooth and plain, picking only the dominant solid color "
                "that matches or closely coordinates with the jacket's color (not image 1's "
                "pattern, only its overall color tone). The trouser fabric must look crisply "
                "pressed and ironed, lying flat and smooth against the leg, with the ONLY "
                "wrinkles or creases being small, natural ones exactly at the knee, where the "
                "leg bends in this pose — everywhere else on the trouser (thigh, shin, "
                "waist) must remain smooth, flat, and freshly pressed, never baggy or "
                "heavily creased. "

                "CRITICAL — fabric color rule: Jodhpuri suits are commonly seen in cream, "
                "beige, or off-white, but you must IGNORE that assumption completely. The "
                "jacket must use ONLY the exact colors and pattern shown in image 1 — same "
                "type (solid, check, stripe, print, weave, or plain), same scale and "
                "proportions — even if that color is unusual for a Jodhpuri suit (e.g. "
                "bright, dark, or colorful). Do not shift the jacket toward cream, beige, "
                "off-white, or any other color unless that is literally the color already "
                "present in image 1. Do not invent, add, brighten, darken, or alter any "
                "color or design element not visible in image 1. The pattern must repeat as "
                "densely and closely spaced as it appears in image 1, with the same small "
                "amount of empty space between elements — do not spread it further apart or "
                "enlarge the gaps. Do not add any embroidery, motifs, or decorative "
                "needlework beyond what is already present in image 1's fabric pattern "
                "itself. Remember: this fabric rule applies to the JACKET only — the trouser "
                "stays plain and solid-colored as described above, never patterned. "

                "Do not preserve the original garment's collar style, sleeve shape, length, "
                "drape, folds, wrinkles, or shadows — discard them completely and generate a "
                "brand-new Jodhpuri-jacket structure from scratch: correct mandarin/"
                "bandhgala collar, correct structured tailored shoulder line, correct "
                "hip-length hem with no extra layer beneath it, correct full button column, "
                "a smooth crisp flat finish with minimal wrinkling as described above, and a "
                "fit that follows the person's actual body shape in this pose — sharply "
                "tailored and fitted, not loose or baggy. "

                "The new jacket's sleeves must be full-length and fully extended down to the "
                "wrist in a natural, straight, unrolled state — never folded, cuffed, or "
                "rolled up at the forearm or elbow. "

                "Generate minimal, subtle shading only where the fabric naturally meets the "
                "body's contours (chest, shoulders, waist), consistent with the lighting "
                "direction in the rest of the photo — avoid generating heavy fold shadows "
                "that would suggest a wrinkled or loosely draped fabric, on either the "
                "jacket or the trouser. "

                "Result must look like one real, unedited photograph of the same person in "
                "the same pose and background, now wearing a properly fitted new Jodhpuri "
                "jacket with a crisp, smooth, minimally-wrinkled finish, made exactly from "
                "image 1's fabric colors and pattern, transitioning directly (with no extra "
                "layer beneath it) into a plain, solid-colored, crisply pressed matching "
                "trouser with no pattern or texture."
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

    # ---- blazer: fixed this session — fabric color/pattern was being
    # overridden by style-typical colors (e.g. tuxedo black). Each prompt
    # now explicitly forbids defaulting to a "typical" color for the style
    # and forces image 1's exact color/pattern onto the blazer regardless. ----
    "blazer": {
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
