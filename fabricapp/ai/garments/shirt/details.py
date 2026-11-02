"""Shirt sleeve and hem choices, shared by all four fabric scenarios."""

GARMENT_TYPE = "shirt"

SLEEVES_FOLDED = (
    "SLEEVES: both {noun} sleeves are evenly rolled to just below the elbows, "
    "with visible folded fabric cuffs and exposed forearms below the folds. "
)
SLEEVES_FULL = (
    "SLEEVES: full-length, fully unrolled shirt sleeves reaching both wrists, "
    "with buttoned wrist cuffs and continuous fabric covering both forearms. "
)
SHIRT_UNTUCKED = (
    "HEM: the shirt is completely untucked, worn outside the trousers. "
    "Its continuous bottom edge hangs over the upper hips below and "
    "covering the trouser waistband, overlapping the top of the trousers. "
)
SHIRT_TUCKED = (
    "HEM: fully tucked-in styling. The shirt fabric enters the trousers at "
    "the natural waist. The trouser waistband and a plain belt are clearly "
    "visible around the waist. The shirt's bottom edge and any lower fabric "
    "border are concealed inside the trousers. "
)


def get_shirt_detail_prompt(detail_keys=None):
    """Select one sleeve treatment and one hem placement, including defaults."""
    keys = set(detail_keys or [])
    sleeves = SLEEVES_FOLDED if "folded_sleeves" in keys else SLEEVES_FULL
    hem = SHIRT_TUCKED if "tucked" in keys else SHIRT_UNTUCKED
    return sleeves.format(noun="shirt") + hem


# The shared serializer reads these slots and option keys for validation.
# Prompt text is selected directly by get_shirt_detail_prompt; these entries
# deliberately have no edit/own mode or sentence-replacement anchors.
DETAIL_RULES = [
    {"slot": "sleeves", "options": {"folded_sleeves": SLEEVES_FOLDED}, "styles": None},
    {"slot": "tuck", "options": {"tucked": SHIRT_TUCKED}, "styles": None},
]
