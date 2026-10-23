"""
Offline check for the garment-specific detail modules (does not call Cloudflare).

For every rule it builds the raw prompt (without any garment detail
applied) and checks that the rule's anchor phrase is really inside it.
If garment prompts.py wording or scenario_composer.py anchors are changed later and an anchor
stops matching, this script shows MISSING.

Run from the project folder (where manage.py is):

    python manage.py shell -c "from fabricapp.check_garment_details import run; run()"
"""

from importlib import import_module

from .ai.detail_engine import (
    DETAIL_MODULES,
    MODE_EDIT,
    MODE_OWN,
    apply_garment_details,
    validate_detail_keys,
)
GARMENT_STYLE_OPTIONS = {
    garment: getattr(import_module(f"fabricapp.ai.{garment}.prompts"), "GARMENT_STYLE_OPTIONS", {}).get(garment, [])
    for garment in DETAIL_MODULES
}
from .ai.scenario_composer import (
    SCENARIO_GENERATED_PERSON,
    SCENARIO_PERSON_PHOTO,
    _build_base,
)

OWN_MODEL_GENDER = {"shirt": "men", "kurta": "men", "kurti_pant": "women"}

DETAIL_RULES = [
    rule
    for module_path in DETAIL_MODULES.values()
    for rule in getattr(import_module(module_path), "DETAIL_RULES", [])
]


def _raw_prompt(garment, style, mode):
    scenario = SCENARIO_PERSON_PHOTO if mode == MODE_EDIT else SCENARIO_GENERATED_PERSON
    base = _build_base(
        scenario, garment, style, False, OWN_MODEL_GENDER.get(garment, "men"), "slim"
    )
    return base["prompt"] if base else ""


def run():
    problems = 0

    print("== 1. Anchors ==")
    for rule in DETAIL_RULES:
        styles = rule["styles"] or GARMENT_STYLE_OPTIONS.get(rule["garment"]) or [None]
        for style in styles:
            prompt = _raw_prompt(rule["garment"], style or "default", rule["mode"])
            found = rule["anchor"] in prompt
            status = "OK     " if found else "MISSING"
            if not found:
                problems += 1
            print(f"{status} {rule['garment']:<11} {str(style):<9} {rule['mode']:<4} {rule['slot']}")

    print("\n== 2. Every option changes the prompt ==")
    for rule in DETAIL_RULES:
        styles = rule["styles"] or GARMENT_STYLE_OPTIONS.get(rule["garment"]) or [None]
        for style in styles:
            raw = _raw_prompt(rule["garment"], style or "default", rule["mode"])
            for key in rule["options"]:
                changed = apply_garment_details(
                    raw, rule["garment"], style, [key], rule["mode"]
                ) != raw
                if not changed:
                    problems += 1
                print(f"{'CHANGES' if changed else 'SAME   '} {rule['garment']:<11} {str(style):<9} {rule['mode']:<4} {key}")

    print("\n== 3. Validation ==")
    print(validate_detail_keys("shirt", None, ["folded_sleeves", "tucked"]), "(expected: None)")
    print(validate_detail_keys("shirt", None, ["with_dupatta"]), "(expected: error)")
    print(validate_detail_keys("kurta", "sherwani", ["folded_sleeves"]), "(expected: error)")
    print(validate_detail_keys("kurta", "sherwani", ["with_dupatta"]), "(expected: None)")

    print("\nProblems found:", problems)
