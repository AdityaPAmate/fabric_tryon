"""
Stage: Garment details (movable parts of a garment prompt).

A "movable part" (sleeves, tuck, dupatta) is found inside an existing
prompt by an exact ANCHOR phrase copied from the prompt text. The
anchor is then replaced (or extended) with the wording of the option the
user chose. When nothing is chosen for a part, its DEFAULT is used:
    default = None  -> the prompt is left exactly as it is today
    default = text  -> the default wording below is applied

The API receives garment_details = a list of option keys, e.g.
["folded_sleeves", "tucked"]. Only ONE option per part is allowed, and
only options that belong to the selected garment_type (and garment_style)
are accepted.

Two kinds of prompts exist, so every rule has a mode:
    MODE_EDIT -> tested prompts in prompts.py (person photo edit)
    MODE_OWN  -> prompts built in prompt_builder.py (own-model paths)

Tokens inside a replacement text:
    {noun}   -> garment name used in the sentence (shirt, kurta ...)
    {anchor} -> the original anchor text (keeps it in place)

If an anchor is NOT found in a prompt (for example because the wording
in prompts.py / prompt_builder.py was edited), a warning is logged and
that rule is skipped. Run check_garment_details.py to verify all anchors.

NOTE: the wording of the NEW options (folded, tucked, half sleeves,
dupatta) is a first draft and untested.
"""

import logging

logger = logging.getLogger("fabricapp")

MODE_EDIT = "edit"
MODE_OWN = "own"

KURTA_ALL_STYLES = ["plain", "sherwani", "pathani", "jodhpuri"]
# Folded sleeves make no sense on a long coat (sherwani) or a jacket.
KURTA_FOLD_STYLES = ["plain", "pathani"]


# ----------------------------------------------------------------------
# Wording
# ----------------------------------------------------------------------

SLEEVES_FOLDED = (
    "The new {noun}'s sleeves must be neatly folded back: rolled up evenly "
    "to just below the elbow, with a clean folded cuff of the same fabric "
    "visible on each arm, both sleeves folded identically, and the "
    "forearms below the fold bare and natural. "
)

# Default for the shirt: not tucked.
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


# ----------------------------------------------------------------------
# Anchors (exact phrases copied from the prompts)
# ----------------------------------------------------------------------

def _full_sleeves_edit_anchor(noun):
    """The 'sleeves must be full-length' sentence of a tested prompt."""
    return (
        f"The new {noun}'s sleeves must be full-length and fully extended "
        "down to the wrist in a natural, straight, unrolled state — never "
        "folded, cuffed, or rolled up at the forearm or elbow. "
    )


# Sleeves sentence in CLOSING (prompt_builder.py), own-model prompts.
SLEEVES_OWN_ANCHOR = (
    "Sleeves, where the garment has them, must be full-length down to the "
    "wrist, straight and unrolled, unless the garment description above "
    "says otherwise. "
)

# Insert-before anchors (the text is added just before the anchor).
EDIT_CLOSING_ANCHOR = "Result must look like one real, unedited photograph"
OWN_CLOSING_ANCHOR = "Generate realistic shading, folds, and shadows."

SHIRT_EDIT_ANCHOR = "collared button-up shirt."
SHIRT_OWN_ANCHOR = "worn with plain dark solid-color formal full-length trousers. "

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


# ----------------------------------------------------------------------
# Rules
# ----------------------------------------------------------------------

def _rule(slot, garment, mode, anchor, options, default=None, styles=None, noun="garment"):
    return {
        "slot": slot,
        "garment": garment,
        "mode": mode,
        "anchor": anchor,
        "options": options,
        "default": default,
        "styles": styles,
        "noun": noun,
    }


DUPATTA_OPTIONS_BEFORE = {
    "with_dupatta": DUPATTA_ADD + "{anchor}",
    "no_dupatta": DUPATTA_REMOVE + "{anchor}",
}

DETAIL_RULES = [
    # ---------------- shirt ----------------
    _rule("sleeves", "shirt", MODE_EDIT, _full_sleeves_edit_anchor("shirt"),
          {"folded_sleeves": SLEEVES_FOLDED}, noun="shirt"),
    _rule("sleeves", "shirt", MODE_OWN, SLEEVES_OWN_ANCHOR,
          {"folded_sleeves": SLEEVES_FOLDED}, noun="shirt"),
    _rule("tuck", "shirt", MODE_EDIT, SHIRT_EDIT_ANCHOR,
          {"tucked": "{anchor} " + SHIRT_TUCKED},
          default="{anchor} " + SHIRT_UNTUCKED),
    _rule("tuck", "shirt", MODE_OWN, SHIRT_OWN_ANCHOR,
          {"tucked": "{anchor}" + SHIRT_TUCKED},
          default="{anchor}" + SHIRT_UNTUCKED),

    # ---------------- kurta (plain, sherwani, pathani, jodhpuri) ----------------
    _rule("sleeves", "kurta", MODE_EDIT, _full_sleeves_edit_anchor("kurta"),
          {"folded_sleeves": SLEEVES_FOLDED}, styles=KURTA_FOLD_STYLES, noun="kurta"),
    _rule("sleeves", "kurta", MODE_OWN, SLEEVES_OWN_ANCHOR,
          {"folded_sleeves": SLEEVES_FOLDED}, styles=KURTA_FOLD_STYLES, noun="kurta"),
    _rule("dupatta", "kurta", MODE_EDIT, EDIT_CLOSING_ANCHOR,
          DUPATTA_OPTIONS_BEFORE, styles=KURTA_ALL_STYLES),
    _rule("dupatta", "kurta", MODE_OWN, OWN_CLOSING_ANCHOR,
          DUPATTA_OPTIONS_BEFORE, styles=KURTA_ALL_STYLES),

    # ---------------- kurti_pant ----------------
    _rule("sleeves", "kurti_pant", MODE_EDIT, KURTI_SLEEVES_EDIT_ANCHOR,
          {"full_sleeves": KURTI_SLEEVES_FULL_EDIT, "half_sleeves": KURTI_SLEEVES_HALF_EDIT}),
    _rule("sleeves", "kurti_pant", MODE_OWN, KURTI_SLEEVES_OWN_ANCHOR,
          {"full_sleeves": KURTI_SLEEVES_FULL_OWN, "half_sleeves": KURTI_SLEEVES_HALF_OWN}),
    # Default: NO dupatta, and any dupatta/pallu in the source photo is removed.
    _rule("dupatta", "kurti_pant", MODE_EDIT, KURTI_DUPATTA_EDIT_ANCHOR,
          {"with_dupatta": DUPATTA_ADD, "no_dupatta": DUPATTA_REMOVE},
          default=DUPATTA_REMOVE),
    # Own-model prompts already say "No dupatta." (the default), so only
    # "with_dupatta" changes anything there.
    _rule("dupatta", "kurti_pant", MODE_OWN, KURTI_DUPATTA_OWN_ANCHOR,
          {"with_dupatta": DUPATTA_ADD}),
]


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------

def _allowed_options(garment_type, garment_style):
    """Returns {slot_name: set(option keys)} valid for this garment (+ style)."""
    slots = {}
    for rule in DETAIL_RULES:
        if rule["garment"] != garment_type:
            continue
        if rule["styles"] is not None and garment_style not in rule["styles"]:
            continue
        slots.setdefault(rule["slot"], set()).update(rule["options"])
    return slots


def validate_detail_keys(garment_type, garment_style, keys):
    """
    Returns an error message (string) if the selected keys are not valid
    for this garment_type / garment_style, or None if everything is fine.
    """
    if not keys:
        return None

    slots = _allowed_options(garment_type, garment_style)
    if not slots:
        return f"garment_details are not available for garment_type '{garment_type}'."

    owner = {}  # option key -> slot name
    for slot_name, option_keys in slots.items():
        for key in option_keys:
            owner[key] = slot_name

    chosen = {}  # slot name -> option key already chosen
    for key in keys:
        if key not in owner:
            return f"'{key}' is not valid for '{garment_type}'. Valid values: {sorted(owner)}."
        slot_name = owner[key]
        if slot_name in chosen and chosen[slot_name] != key:
            return f"Choose only one option for '{slot_name}': got '{chosen[slot_name]}' and '{key}'."
        chosen[slot_name] = key
    return None


# ----------------------------------------------------------------------
# Applying the rules to a prompt
# ----------------------------------------------------------------------

def apply_garment_details(prompt, garment_type, garment_style, keys, mode):
    """
    Applies every rule of this garment/mode to the prompt text (in
    memory only — prompts.py / prompt_builder.py are never edited).
    Parts with no selected option use their default.
    """
    keys = keys or []
    for rule in DETAIL_RULES:
        if rule["garment"] != garment_type or rule["mode"] != mode:
            continue
        if rule["styles"] is not None and garment_style not in rule["styles"]:
            continue

        chosen = next((k for k in keys if k in rule["options"]), None)
        template = rule["options"][chosen] if chosen else rule["default"]
        if template is None:
            continue  # nothing to change for this part

        anchor = rule["anchor"]
        if anchor not in prompt:
            logger.warning(
                "garment_details: anchor not found (garment=%s style=%s mode=%s slot=%s choice=%s)",
                garment_type, garment_style, mode, rule["slot"], chosen or "default",
            )
            continue

        text = template.replace("{noun}", rule["noun"]).replace("{anchor}", anchor)
        prompt = prompt.replace(anchor, text, 1)
    return prompt
