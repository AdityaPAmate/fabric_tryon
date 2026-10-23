"""Kurta-specific garment detail rules copied from garment_details.py."""

GARMENT_TYPE = "kurta"
MODE_EDIT = "edit"
MODE_OWN = "own"

KURTA_ALL_STYLES = ["plain", "sherwani", "pathani", "jodhpuri"]
KURTA_FOLD_STYLES = ["plain", "pathani"]

SLEEVES_FOLDED = (
    "The new {noun}'s sleeves must be neatly folded back: rolled up evenly "
    "to just below the elbow, with a clean folded cuff of the same fabric "
    "visible on each arm, both sleeves folded identically, and the "
    "forearms below the fold bare and natural. "
)
KURTA_DUPATTA_ADD = (
    "Add a dupatta — a long, light, soft stole draped neatly over the "
    "shoulders and hanging down the front and back. DUPATTA FABRIC: the "
    "dupatta is cut from the same fabric as the kurta, so image 1's "
    "colors, pattern and motifs must be clearly visible all over the "
    "dupatta, at the same scale and density as on the kurta — never plain "
    "and never a single solid color — with a plain finished edge. The "
    "dupatta must follow the person's pose: it hangs naturally from the "
    "shoulders and never covers the face. "
)
DUPATTA_REMOVE = (
    "Do NOT add any dupatta, stole or scarf. If the person in the source "
    "photo has a dupatta, stole, pallu or any loose cloth over the "
    "shoulders, arms or hands, remove it completely (this applies only to "
    "that cloth: the person's face, arms and hands themselves stay the "
    "same) so the shoulders and arms are free of extra cloth. "
)
SLEEVES_OWN_ANCHOR = (
    "Sleeves, where the garment has them, must be full-length down to the "
    "wrist, straight and unrolled, unless the garment description above "
    "says otherwise. "
)
EDIT_CLOSING_ANCHOR = "Result must look like one real, unedited photograph"
OWN_CLOSING_ANCHOR = "Generate realistic shading, folds, and shadows."

DUPATTA_OPTIONS_BEFORE = {
    "with_dupatta": KURTA_DUPATTA_ADD + "{anchor}",
    "no_dupatta": DUPATTA_REMOVE + "{anchor}",
}

DETAIL_RULES = [
    {
        "slot": "sleeves", "garment": GARMENT_TYPE, "mode": MODE_EDIT,
        "anchor": (
            "The new kurta's sleeves must be full-length and fully extended "
            "down to the wrist in a natural, straight, unrolled state — never "
            "folded, cuffed, or rolled up at the forearm or elbow. "
        ),
        "options": {"folded_sleeves": SLEEVES_FOLDED}, "default": None,
        "styles": KURTA_FOLD_STYLES, "noun": "kurta",
    },
    {
        "slot": "sleeves", "garment": GARMENT_TYPE, "mode": MODE_OWN,
        "anchor": SLEEVES_OWN_ANCHOR,
        "options": {"folded_sleeves": SLEEVES_FOLDED}, "default": None,
        "styles": KURTA_FOLD_STYLES, "noun": "kurta",
    },
    {
        "slot": "dupatta", "garment": GARMENT_TYPE, "mode": MODE_EDIT,
        "anchor": EDIT_CLOSING_ANCHOR,
        "options": DUPATTA_OPTIONS_BEFORE, "default": None,
        "styles": KURTA_ALL_STYLES, "noun": "garment",
    },
    {
        "slot": "dupatta", "garment": GARMENT_TYPE, "mode": MODE_OWN,
        "anchor": OWN_CLOSING_ANCHOR,
        "options": DUPATTA_OPTIONS_BEFORE, "default": None,
        "styles": KURTA_ALL_STYLES, "noun": "garment",
    },
]
