"""Kurti-pant detail rules copied from garment_details.py."""

GARMENT_TYPE = "kurti_pant"
MODE_EDIT = "edit"
MODE_OWN = "own"

SLEEVES_FOLDED = (
    "The new {noun}'s sleeves must be neatly folded back: rolled up evenly "
    "to just below the elbow, with a clean folded cuff of the same fabric "
    "visible on each arm, both sleeves folded identically, and the "
    "forearms below the fold bare and natural. "
)
KURTI_SLEEVES_FULL_EDIT = "full-length sleeves reaching down to the wrist — never sleeveless"
KURTI_SLEEVES_HALF_EDIT = "half sleeves ending at the elbow — never sleeveless"
KURTI_SLEEVES_FULL_OWN = "full-length sleeves reaching down to the wrist (never sleeveless)"
KURTI_SLEEVES_HALF_OWN = "half sleeves ending at the elbow (never sleeveless)"
DUPATTA_ADD = (
    "Add a dupatta — a long, light, soft stole draped neatly over the "
    "shoulders and hanging down the front and back, made from exactly the "
    "same fabric as image 1 (the same colors, pattern and scale, with a "
    "plain finished edge). The dupatta must follow the person's pose: it "
    "hangs naturally from the shoulders and never covers the face. "
)
DUPATTA_REMOVE = (
    "Do NOT add any dupatta, stole or scarf. If the person in the source "
    "photo has a dupatta, stole, pallu or any loose cloth over the "
    "shoulders, arms or hands, remove it completely (this applies only to "
    "that cloth: the person's face, arms and hands themselves stay the "
    "same) so the shoulders and arms are free of extra cloth. "
)
KURTI_SLEEVES_EDIT_ANCHOR = (
    "full-length sleeves reaching down to the wrists — never sleeveless"
)
KURTI_SLEEVES_OWN_ANCHOR = "full-length sleeves reaching the wrists"
KURTI_DUPATTA_EDIT_ANCHOR = (
    "Do not add a dupatta, stole, or scarf unless one is already clearly "
    "present and unchanged from image 0 — if there is no dupatta in image "
    "0, do not invent one. "
)
KURTI_DUPATTA_OWN_ANCHOR = "No dupatta. "

DETAIL_RULES = [
    {
        "slot": "sleeves", "garment": GARMENT_TYPE, "mode": MODE_EDIT,
        "anchor": KURTI_SLEEVES_EDIT_ANCHOR,
        "options": {
            "full_sleeves": KURTI_SLEEVES_FULL_EDIT,
            "half_sleeves": KURTI_SLEEVES_HALF_EDIT,
        },
        "default": None, "styles": None, "noun": "garment",
    },
    {
        "slot": "sleeves", "garment": GARMENT_TYPE, "mode": MODE_OWN,
        "anchor": KURTI_SLEEVES_OWN_ANCHOR,
        "options": {
            "full_sleeves": KURTI_SLEEVES_FULL_OWN,
            "half_sleeves": KURTI_SLEEVES_HALF_OWN,
        },
        "default": None, "styles": None, "noun": "garment",
    },
    {
        "slot": "dupatta", "garment": GARMENT_TYPE, "mode": MODE_EDIT,
        "anchor": KURTI_DUPATTA_EDIT_ANCHOR,
        "options": {"with_dupatta": DUPATTA_ADD, "no_dupatta": DUPATTA_REMOVE},
        "default": DUPATTA_REMOVE, "styles": None, "noun": "garment",
    },
    {
        "slot": "dupatta", "garment": GARMENT_TYPE, "mode": MODE_OWN,
        "anchor": KURTI_DUPATTA_OWN_ANCHOR,
        "options": {"with_dupatta": DUPATTA_ADD},
        "default": None, "styles": None, "noun": "garment",
    },
]
