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

    }
}



# ==========================================================================
# NEW this session: camera_view (renamed from "pose") + background support.
# These are ADDITIVE — no existing GARMENT_PROMPTS wording is touched.
# The instructions below get appended to the already-tested base prompt at
# generation time (see cloudflare_engine.py), so tested wording stays intact.
# ==========================================================================

# If camera_view is not provided, no instruction is added — the original
# pose/framing already present in image 0 is kept, exactly like today.
CAMERA_VIEW_OPTIONS = ["front", "side", "close_up"]

CAMERA_VIEW_INSTRUCTIONS = {
    "front": (
        "CAMERA VIEW OVERRIDE: regardless of the camera angle or body "
        "orientation already present in image 0, render the final output as "
        "a front-facing, full-body shot — the person must be shown from "
        "head to feet, facing the camera directly (or nearly directly), "
        "with the entire body and the full length of the new garment "
        "clearly visible in frame."
    ),
    "side": (
        "CAMERA VIEW OVERRIDE: regardless of the camera angle or body "
        "orientation already present in image 0, render the final output "
        "as a side-profile, full-body shot — the person's body must be "
        "turned to show a clear side or three-quarter side angle relative "
        "to the camera, with the entire body and the full length of the "
        "new garment clearly visible in frame, including the side "
        "silhouette and drape of the garment."
    ),
    "close_up": (
        "CAMERA VIEW OVERRIDE: regardless of the camera angle or framing "
        "already present in image 0, render the final output as a tight "
        "close-up shot showing only the head, shoulders, and upper chest "
        "area down to roughly mid-chest. Crop the frame so that the waist, "
        "legs, and any lower-body garment (pant, salwar, churidar, "
        "trouser) are NOT visible at all in this shot — only the upper "
        "portion of the new garment (collar, upper chest, shoulders, "
        "visible upper sleeves) should be shown."
    ),
}


def get_camera_view_instruction(camera_view):
    """
    Returns the camera-view override instruction text to append to the
    base prompt, or None if camera_view is not provided / not recognized
    (in which case the original pose in image 0 is left as-is).
    """
    if not camera_view:
        return None
    return CAMERA_VIEW_INSTRUCTIONS.get(camera_view)


# If background is not provided, no instruction is added — the base
# prompt's own "keep background unchanged" line (already present in every
# GARMENT_PROMPTS entry) governs, exactly like today.
BACKGROUND_OPTIONS = [
    "white_marble_terrace",
    "festive_street",
    "royal_courtyard",
    "riverside_ghat",
]

BACKGROUND_DESCRIPTIONS = {
    "white_marble_terrace": (
        "a bright, sunlit white marble terrace overlooking a calm lake, "
        "with an ornately carved white marble balustrade railing in the "
        "foreground, hazy green hills in the distance, soft warm "
        "daylight, clear pale blue sky"
    ),
    "festive_street": (
        "a festively decorated Indian heritage street at dusk, with "
        "strings of orange and yellow marigold flower garlands hanging "
        "overhead between old carved-balcony buildings, warm glowing "
        "lanterns and string lights, a wet reflective stone-paved street "
        "lined with potted marigold plants, a lit decorated archway gate "
        "visible in the distance"
    ),
    "royal_courtyard": (
        "a grand palace courtyard at sunset, framed by an ornately carved "
        "scalloped stone archway in the foreground, a symmetrical "
        "colonnaded courtyard beyond it, a small domed pavilion and "
        "fountain at the center, tall palm trees, warm orange-pink sunset "
        "sky with soft clouds"
    ),
    "riverside_ghat": (
        "a calm riverside ghat at dawn or dusk, stone steps leading down "
        "to a still river, small floating oil lamps glowing on the "
        "water's surface, distant temple spires and silhouetted buildings "
        "across a misty river, soft pastel sky"
    ),
}


def get_background_instruction(background):
    """
    Returns the background-override instruction text to append to the
    base prompt, or None if background is not provided / not recognized
    (in which case the original background in image 0 is kept unchanged,
    exactly like today).

    NOT YET TESTED against the real API — the base prompts already say
    "keep background unchanged", so this override explicitly tells the
    model to prioritize the new instruction. May need wording iteration
    once real output is reviewed, same as every other prompt in this file.
    """
    if not background:
        return None
    description = BACKGROUND_DESCRIPTIONS.get(background)
    if description is None:
        return None
    return (
        "BACKGROUND OVERRIDE: this instruction takes priority over any "
        "earlier instruction in this prompt to keep the background "
        "unchanged. Replace the entire area behind the person with the "
        "following scene: " + description + ". Keep the person, face, "
        "pose, and the newly generated garment exactly as already "
        "specified — only the background area changes. Subtly adjust the "
        "lighting and color tone on the person so it looks naturally lit "
        "by this new background environment, without changing the "
        "garment's actual fabric color or pattern."
    )



