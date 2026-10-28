"""Scenario-organized prompt data extracted from the existing project.

Source wording is copied from prompts.py and prompt_builder.py. This module
separates garment-owned data by scenario; scenario composition still uses
the existing shared prompt builder until the later migration step.
"""

GARMENT_TYPE = 'kurta'
POSE_LIMBS_RULE = True
GARMENT_STYLE_OPTIONS = {'kurta': ['plain', 'sherwani', 'pathani', 'jodhpuri']}

# Exact existing edit-mode prompt(s), including seed and guidance.
GARMENT_PROMPTS = {
    GARMENT_TYPE: {
        "plain": {
            # CORRECTED — length was ambiguous ("mid-thigh or knee"),
            # which let the model drift too long. Now pinned to just
            # above the knee only.
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

                "The outfit has exactly TWO separate garments: one single kurta ending just "
                "above the kneecaps and one separate pair of straight-cut pajama trousers from the waist "
                "to the ankles. The pajama is plain solid WHITE. It is trousers, not a second "
                "tunic, inner kurta, dhoti, wrap, or loose white panel; no white cloth may hang "
                "from beneath the kurta hem. Only the separate trouser legs are visible below "
                "the kurta. Keep the kurta hem clean and unobstructed. Do not leave any leg "
                "skin below the kurta hem uncovered. The pajama must never use image 1's fabric, "
                "pattern, border, or color. "

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
            # CORRECTED — length made much more explicit (was drifting
            # too short/kurta-like). Length is the single biggest
            # defining feature vs. a plain kurta.
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
            # CORRECTED — collar was wrongly written as "round/band"
            # (that's a different kurta style); a real Pathani kurta
            # has a classic SHIRT collar. Pockets now specify flaps.
            # Salwar width made much more explicit.
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
                "circumstance. Instead, generate a distinct Pathani salwar — a VERY LOOSE, "
                "voluminous, deeply pleated trouser with a visibly wide silhouette from the "
                "waist through the seat and thighs, substantially wider than straight pajama "
                "trousers. Show generous folds and extra fabric volume at the waist, seat and "
                "thighs; only below the knees does it gradually narrow into soft folds and a "
                "cuffed ankle. It must read clearly as a baggy Pathani salwar, never as slim "
                "pants, churidar, or ordinary straight kurta-pajama trousers — in a "
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
            # CORRECTED, based on a real reference photo: (1) explicitly
            # forbids any extra kurta/tunic-like layer visible below the
            # jacket hem — jacket must transition directly to the trouser
            # at the waist; (2) trouser is now plain/solid, matching the
            # jacket's COLOR ONLY, no pattern or texture; (3) wrinkle
            # rule made per-garment and specific (elbow crease on jacket,
            # knee crease on trouser, crisp everywhere else on both).
            "prompt": (
                "Edit image 0. Keep the same person, face, skin tone, hairstyle, expression, "
                "hands, arms, background, and body pose from image 0 completely unchanged — "
                "sharp, fully in focus, not altered in any way. "

                "Regardless of what garment the person is currently wearing, replace it "
                "entirely with a new Jodhpuri-style bandhgala jacket — a structured, "
                "single-breasted coat with sharply tailored shoulders (like a blazer, not a "
                "loose kurta), a stand-up mandarin/bandhgala collar (no lapel, no notch), a "
                "full single column of small buttons down the front placket, one small welt "
                "or flap chest pocket, two flap pockets at the hip level, with the hem "
                "ending at the upper hip around the waistband and clearly above the crotch "
                "(never reaching mid-thigh or the knee; it must not look like a long kurta or "
                "sherwani), fitted closely to the body. "

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
                "kind — completely smooth and plain, in the same dominant base color as the "
                "jacket fabric in image 1 (ignore its motifs and border; use only the plain "
                "ground color). Do not substitute grey, beige, white, or another unrelated "
                "color unless that is the jacket fabric's actual dominant base color. The "
                "trouser fabric must look crisply "
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

# Exact existing garment specifications used by the shared own-model and
# person-pose builders. Values remain source expressions from prompt_builder.py.

GARMENT_SPECS = {
    ('kurta', 'plain'): {
        "fabric_target": "kurta",
        "border": True,
        # CHANGED (test report: "pant must be in white color"): the
        # kurta-pajama is plain solid WHITE (it used to be "white,
        # off-white, or a solid shade from the kurta's palette").
        "garment": (
            "a traditional Indian men's kurta — a straight-cut garment "
            "extending down to just above the knee (the hem ending a few "
            "inches above the kneecaps, fully covering both thighs), "
            "with a simple mandarin/band collar, a short front placket with "
            "two or three buttons near the neck, straight side slits at the "
            "hem, and full-length long sleeves reaching down to the wrists "
            "covering both arms completely, loose-fitting. Below it is exactly one separate "
            "pair of straight-cut white pajama trousers from the waist to the ankles, plain "
            "solid WHITE and never made from image 1's fabric. Do not add a second tunic, "
            "inner kurta, dhoti, wrap, or loose white panel; no white cloth hangs from under "
            "the kurta hem. Keep the hem clean, with only the separate pajama legs visible "
            "below it. "
        ),
    },
    ('kurta', 'sherwani'): {
        "fabric_target": "sherwani",
        "border": False,
        "pant_colour_from_fabric": True,
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
            "buttons from neck to hem, full-length structured sleeves "
            "reaching down to the wrists covering both arms completely, "
            "and a fitted, tailored torso with visible waist suppression. "
            "Below it, a matching churidar — fitted through the leg, "
            "gathering into soft folds above the ankle — in a plain solid "
            "color that is exactly the main colour of the sherwani fabric "
            "from image 1 (never black, grey or white unless that is "
            "image 1's main colour), with no pattern. "
        ),
    },
    ('kurta', 'pathani'): {
        "fabric_target": "kurta",
        "border": False,
        "pant_colour_from_fabric": True,
        "color_note": (
            "CRITICAL — Pathani suits are commonly white or beige, but "
            "ignore that assumption: the kurta must be in the colors of "
            "image 1 only. "
        ),
        "garment": (
            "a Pathani-style kurta — loose, relaxed, straight-cut, to "
            "roughly mid-thigh or knee, with a classic SHIRT-style pointed "
            "collar (not a round or mandarin collar), two clearly visible "
            "rectangular chest patch pockets, one on each side, each with a "
            "distinct flap, a short button placket, and full-length sleeves "
            "reaching down to the wrists covering both arms completely. This "
            "must read as a Pathani style, not a plain mandarin-collar kurta: "
            "the pointed collar and both flap pockets must be visible. Below "
            "it, a Pathani salwar — VERY LOOSE and deeply pleated, with a "
            "visibly wide silhouette from the waist through the seat and "
            "thighs, substantially wider than straight pajama trousers. Show "
            "generous folds and extra fabric volume at the waist, seat and "
            "thighs; only below the knees does it gradually narrow into soft "
            "folds and a cuffed ankle. Never slim pants, churidar or ordinary "
            "straight kurta-pajama trousers. In a plain solid "
            "color that is exactly the main colour of the kurta fabric "
            "from image 1 (never black or grey unless that is image 1's "
            "main colour), never patterned. "
        ),
    },
    ('kurta', 'jodhpuri'): {
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
            "chest pocket and two flap hip pockets, full-length tailored "
            "sleeves reaching down to the wrists covering both arms "
            "completely, hem ending at the upper hip around the waistband "
            "and clearly above the crotch (never reaching mid-thigh or the "
            "knee; it must not look like a long kurta or sherwani), fitted "
            "closely, with a crisp, "
            "smooth, almost flat finish (creases only at the elbow bend). "
            "No extra kurta or tunic layer may show below the jacket hem "
            "— it goes straight into the trouser at the waist. Below it, "
            "a fitted straight-cut formal trouser in a PLAIN SOLID color "
            "exactly matching the dominant base color of the jacket fabric "
            "in image 1, ignoring its motifs and border. It is one separate "
            "pair of full-length trouser legs to the ankles, crisply pressed, "
            "with no pattern or texture and no unrelated grey, beige or white color. "
        ),
    }
}
# Garment-image prompting is shared by fabricapp.ai.garment_image.


KURTA_WHITE_PANT_STYLES = ("plain",)

KURTA_PANT_OLD_PHRASE = (
    "white, off-white, or a solid shade picked from the kurta's own "
    "color palette"
)

KURTA_PANT_NEW_PHRASE = "plain solid WHITE"

KURTA_PLAIN_LENGTH_OLD = (
    "extending down to just above the knee (NOT mid-thigh, NOT below the "
    "knee — the hem must end a few inches above the kneecap)"
)

KURTA_PLAIN_LENGTH_NEW = (
    "extending down to the knee (the hem ends level with the middle of the "
    "kneecaps, clearly below mid-thigh)"
)

KURTA_PLAIN_LENGTH_LINE = (
    "KURTA LENGTH (replaces any earlier length instruction): the plain kurta "
    "is long, its hem ending level with the knees and fully covering both "
    "thighs, never short or mid-thigh. "
)

KURTA_EDIT_LIMBS_LINE = (
    "ARMS AND HANDS: the person has exactly two arms and two hands in total — "
    "never a third hand or a leftover arm at the lower side of the frame. "
    "Hands, fingers and wrists keep their bare skin exactly as in image 0: "
    "image 1's fabric, its border or any patch of it appears only on the "
    "kurta body, collar and sleeves (a cuff band stops at the sleeve edge), "
    "never on the hands, skin or background. "
)

KURTA_COLOURED_PANT_STYLES = ("sherwani", "pathani")

KURTA_PANT_COLOUR_EDIT = {
    "sherwani": [(
        "(white, off-white, or a solid shade picked from the sherwani's own "
        "color palette), never patterned or bright",
        "(exactly the main colour of the sherwani fabric from image 1, as a "
        "plain solid), never patterned",
    )],
    "pathani": [(
        "(commonly the same tone as the kurta itself, or a solid shade "
        "picked from the kurta's own color palette), never patterned or "
        "bright",
        "(exactly the main colour of the kurta fabric from image 1, as a "
        "plain solid), never patterned",
    )],
}

KURTA_PANT_COLOUR_LINE = (
    "TROUSER COLOUR (replaces any earlier instruction about the trouser "
    "colour): the churidar / salwar below is a plain solid in exactly the "
    "main colour of image 1's fabric, with no pattern, print, check or "
    "border. It is never black, grey or any dark colour unless that is the "
    "main colour of image 1, and it does not keep the trouser colour of "
    "image 0. "
)

KURTA_PANT_WHITE_LINE = (
    "TROUSER COLOUR (replaces any earlier instruction about the trouser or "
    "pajama): the pajama below the kurta is plain, solid WHITE, "
    "straight-cut and full-length down to the ankles, with no pattern, and "
    "it is not made from image 1's fabric; the person's legs must be fully "
    "covered down to the ankles, never bare legs or shorts. "
)



# Garment-specific back-view detail rules migrated from scenario_composer.py.
BACK_VIEW_POSES = ("back_turn_hair_touch",)

BACK_VIEW_REPLACEMENTS = [
    ("a full column of small decorative buttons from neck to hem",
     "a plain, smooth, completely button-free back"),
    ("a full column of small buttons, one small chest pocket and two flap "
     "hip pockets",
     "a smooth plain back"),
    ("two rectangular chest patch pockets with flaps, and a short button "
     "placket",
     "a smooth plain back"),
    ("a short front placket with two or three buttons near the neck",
     "a plain smooth back"),
]

BACK_VIEW_NOTE = (
    "BACK VIEW: the camera sees only the BACK of the person, so the front of "
    "the garment is hidden: no buttons, button column, placket, chest "
    "pocket, hip pocket flaps or lapels are drawn anywhere. The back of the "
    "garment is one smooth, plain surface of image 1's fabric (a jacket may "
    "show a single centre vent). "
)

def garment_text_for_pose(garment_text, pose):
    if pose not in BACK_VIEW_POSES:
        return garment_text
    for old_text, new_text in BACK_VIEW_REPLACEMENTS:
        garment_text = garment_text.replace(old_text, new_text, 1)
    return garment_text + BACK_VIEW_NOTE


def fabric_forbidden_text(spec):
    if spec.get("pant_colour_from_fabric"):
        return (
            "Do not use image 1's pattern, motifs or print on the churidar, "
            "salwar or trousers, footwear, accessories, skin or background. The "
            "lower garment (churidar, salwar or trousers) must be 100% PLAIN and "
            "SOLID with ZERO pattern, ZERO motifs, and ZERO print — taking ONLY "
            "the single plain matching solid colour from image 1, completely unpatterned. "
        )
    return (
        "Do not use image 1's fabric, pattern or colour on the trousers "
        "or pajama, any shirt or tie, footwear, accessories, skin or "
        "background. "
    )
