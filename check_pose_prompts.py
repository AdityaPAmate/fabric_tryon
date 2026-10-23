"""Offline architecture smoke check for garment prompt routing.

Run from the project root: python check_pose_prompts.py
No API credentials, Django setup, or image generation are required.
"""

from importlib import import_module

from fabricapp.ai.pose_registry import get_pose_options, get_pose_sentence
from fabricapp.ai.router import (
    SCENARIO_FACE_PHOTO,
    SCENARIO_GENERATED_PERSON,
    SCENARIO_PERSON_PHOTO,
    SCENARIO_PERSON_POSE,
    build_prompt_config,
)

GARMENTS = {
    "blazer": "business",
    "kurta": "plain",
    "kurti_pant": None,
    "pant": None,
    "saree": None,
    "shirt": None,
}
SCENARIOS = (
    SCENARIO_PERSON_PHOTO,
    SCENARIO_PERSON_POSE,
    SCENARIO_FACE_PHOTO,
    SCENARIO_GENERATED_PERSON,
)

checked = 0
for garment, style in GARMENTS.items():
    settings = import_module(f"fabricapp.ai.{garment}.settings")
    for scenario in SCENARIOS:
        pose = "pocket_walk" if scenario == SCENARIO_PERSON_POSE else None
        context = {
            "gender": "women" if garment in {"kurti_pant", "saree"} else "men",
            "body_type": "slim",
            "pose": pose,
            "camera_view": None,
            "background": None,
            "garment_details": [],
        }
        result = build_prompt_config(
            scenario=scenario,
            garment_type=garment,
            garment_style=style,
            context=context,
        )
        assert result["prompt"].strip(), (garment, scenario, "empty prompt")
        assert result["seed"] == settings.DEFAULT_SEED, (garment, scenario, "seed")
        assert result["guidance"] == settings.DEFAULT_GUIDANCE, (garment, scenario, "guidance")
        if pose:
            assert get_pose_sentence(pose, garment), (garment, scenario, "pose missing")
        checked += 1

    overridden = build_prompt_config(
        scenario=SCENARIO_GENERATED_PERSON,
        garment_type=garment,
        garment_style=style,
        context={"gender": "women" if garment in {"kurti_pant", "saree"} else "men", "garment_details": []},
        seed=31,
        guidance=4.5,
    )
    assert overridden["seed"] == 31 and overridden["guidance"] == 4.5

print(f"PASS: {checked} garment/scenario routes and per-request setting overrides")
print(f"Registered pose keys: {len(get_pose_options())}")
