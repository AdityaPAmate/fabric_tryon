"""Shirt-specific garment detail rules copied from garment_details.py."""

GARMENT_TYPE = "shirt"
MODE_EDIT = "edit"
MODE_OWN = "own"

SLEEVES_FOLDED = (
    "The new {noun}'s sleeves must be neatly folded back: rolled up evenly "
    "to just below the elbow, with a clean folded cuff of the same fabric "
    "visible on each arm, both sleeves folded identically, and the "
    "forearms below the fold bare and natural. "
)
SHIRT_UNTUCKED = (
    "The new shirt must be worn untucked, with its straight hem hanging "
    "naturally outside the trousers over the hips, not tucked into the "
    "waistband. "
)
SHIRT_TUCKED = (
    "The new shirt must be tucked neatly into the trousers at the waist, "
    "with the shirt hem fully inside the waistband and a clean, smooth "
    "waistline. "
)

SLEEVES_OWN_ANCHOR = (
    "Sleeves, where the garment has them, must be full-length down to the "
    "wrist, straight and unrolled, unless the garment description above "
    "says otherwise. "
)
SHIRT_EDIT_ANCHOR = "collared button-up shirt."
SHIRT_OWN_ANCHOR = "worn with plain dark solid-color formal full-length trousers. "

DETAIL_RULES = [
    {
        "slot": "sleeves",
        "garment": GARMENT_TYPE,
        "mode": MODE_EDIT,
        "anchor": (
            "The new shirt's sleeves must be full-length and fully extended "
            "down to the wrist in a natural, straight, unrolled state — never "
            "folded, cuffed, or rolled up at the forearm or elbow. "
        ),
        "options": {"folded_sleeves": SLEEVES_FOLDED},
        "default": None,
        "styles": None,
        "noun": "shirt",
    },
    {
        "slot": "sleeves",
        "garment": GARMENT_TYPE,
        "mode": MODE_OWN,
        "anchor": SLEEVES_OWN_ANCHOR,
        "options": {"folded_sleeves": SLEEVES_FOLDED},
        "default": None,
        "styles": None,
        "noun": "shirt",
    },
    {
        "slot": "tuck",
        "garment": GARMENT_TYPE,
        "mode": MODE_EDIT,
        "anchor": SHIRT_EDIT_ANCHOR,
        "options": {"tucked": "{anchor} " + SHIRT_TUCKED},
        "default": "{anchor} " + SHIRT_UNTUCKED,
        "styles": None,
        "noun": "shirt",
    },
    {
        "slot": "tuck",
        "garment": GARMENT_TYPE,
        "mode": MODE_OWN,
        "anchor": SHIRT_OWN_ANCHOR,
        "options": {"tucked": "{anchor}" + SHIRT_TUCKED},
        "default": "{anchor}" + SHIRT_UNTUCKED,
        "styles": None,
        "noun": "shirt",
    },
]
