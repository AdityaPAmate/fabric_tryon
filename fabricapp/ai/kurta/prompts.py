"""Scenario-organized prompt data extracted from the existing project.

Source wording is copied from prompts.py and prompt_builder.py. This module
separates garment-owned data by scenario; scenario composition still uses
the existing shared prompt builder until the later migration step.
"""

GARMENT_TYPE = 'kurta'
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
            "extending down to the knee (the hem ending level with the "
            "kneecap, fully covering both thighs, clearly below mid-thigh), "
            "with a simple mandarin/band collar, a short front placket with "
            "two or three buttons near the neck, straight side slits at the "
            "hem, and full-length long sleeves reaching down to the wrists "
            "covering both arms completely, loose-fitting. Below it, a "
            "matching plain straight-cut kurta-pajama reaching the ankles, "
            "in plain solid WHITE, never patterned and never made from "
            "image 1's fabric. "
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
            "collar (not a round or mandarin collar), two rectangular "
            "chest patch pockets with flaps, a short button placket, "
            "and full-length sleeves reaching down to the wrists covering "
            "both arms completely. Below it, a Pathani salwar — VERY LOOSE, "
            "voluminous and pleated, dramatically wider than a normal "
            "kurta-pajama, narrowing to a cuffed ankle — in a plain solid "
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
            "completely, hip-length hem, fitted closely, with a crisp, "
            "smooth, almost flat finish (creases only at the elbow bend). "
            "No extra kurta or tunic layer may show below the jacket hem "
            "— it goes straight into the trouser at the waist. Below it, "
            "a fitted straight-cut formal trouser in a PLAIN SOLID color "
            "matching the jacket's color "
            "tone, crisply pressed, with no pattern or texture. "
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
