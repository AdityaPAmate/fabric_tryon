"""Shared background options and background prompt instructions."""

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
    """Return the override prompt for a known background, else None."""
    if not background:
        return None

    description = BACKGROUND_DESCRIPTIONS.get(background)
    if description is None:
        return None

    return (
        "BACKGROUND OVERRIDE: this instruction takes priority over any "
        "earlier instruction in this prompt to keep the background "
        "unchanged. Replace the entire area behind the person with the "
        "following scene: "
        + description
        + ". Keep the person, face, pose, and the newly generated garment "
        "exactly as already specified — only the background area changes. "
        "Subtly adjust the lighting and color tone on the person so it "
        "looks naturally lit by this new background environment, without "
        "changing the garment's actual fabric color or pattern."
    )