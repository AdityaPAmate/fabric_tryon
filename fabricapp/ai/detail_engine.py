"""Load and apply garment details from each garment's own details module."""

from functools import lru_cache
from importlib import import_module


DETAIL_MODULES = {
    "blazer": "fabricapp.ai.blazer.details",
    "kurta": "fabricapp.ai.kurta.details",
    "kurti_pant": "fabricapp.ai.kurti_pant.details",
    "pant": "fabricapp.ai.pant.details",
    "saree": "fabricapp.ai.saree.details",
    "shirt": "fabricapp.ai.shirt.details",
}

MODE_EDIT = "edit"
MODE_OWN = "own"


@lru_cache(maxsize=None)
def _rules_for(garment_type):
    module_path = DETAIL_MODULES.get(garment_type)
    if module_path is None:
        return ()
    rules = getattr(import_module(module_path), "DETAIL_RULES", ())
    if not isinstance(rules, (list, tuple)):
        raise TypeError(f"{module_path}.DETAIL_RULES must be a list or tuple")
    return tuple(rules)


def validate_detail_keys(garment_type, garment_style, keys):
    """Return an error string for invalid options, otherwise None."""
    if not keys:
        return None
    slots = {}
    for rule in _rules_for(garment_type):
        if rule.get("styles") is None or garment_style in rule["styles"]:
            slots.setdefault(rule["slot"], set()).update(rule["options"])
    owner = {key: slot for slot, values in slots.items() for key in values}
    if not owner:
        return f"garment_details are not available for garment_type '{garment_type}'."
    chosen = {}
    for key in keys:
        if key not in owner:
            return f"'{key}' is not valid for '{garment_type}'. Valid values: {sorted(owner)}."
        slot = owner[key]
        if slot in chosen and chosen[slot] != key:
            return f"Choose only one option for '{slot}': got '{chosen[slot]}' and '{key}'."
        chosen[slot] = key
    return None


def apply_garment_details(prompt, garment_type, garment_style, keys, mode):
    """Apply selected/default detail rules using exact prompt anchors."""
    keys = keys or []
    for rule in _rules_for(garment_type):
        if rule.get("mode") != mode:
            continue
        styles = rule.get("styles")
        if styles is not None and garment_style not in styles:
            continue
        chosen = next((key for key in keys if key in rule["options"]), None)
        template = rule["options"][chosen] if chosen else rule.get("default")
        anchor = rule["anchor"]
        if template is None or anchor not in prompt:
            continue
        text = template.replace("{noun}", rule.get("noun", "garment"))
        text = text.replace("{anchor}", anchor)
        prompt = prompt.replace(anchor, text, 1)
    return prompt
