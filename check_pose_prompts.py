"""
Offline check (no Cloudflare call, no cost).
Run from the project root:   python check_pose_prompts.py

Needs fabricapp/ai/prompt_builder_old.py = a copy of the prompt_builder.py
you had BEFORE adding the pose feature. Delete that file after the check.

Check 1: without pose, new prompts == old prompts (nothing else broke).
Check 2: person photo + pose is routed to the person_pose scenario, and
         its prompt contains the pose text and NOT "Edit image 0".
Check 3: own-model scenarios contain the pose text instead of the old
         default pose wording.
"""

import os
import sys
from itertools import product

sys.path.insert(0, os.getcwd())

from fabricapp.ai import prompt_builder as new
from fabricapp.ai.pose_data import (
    POSE_OPTIONS,
    DEFAULT_OWN_MODEL_POSE,
    get_pose_sentence,
    get_saree_pose_parts,
)
from fabricapp.ai.prompts import GARMENT_PROMPTS, GARMENT_STYLE_OPTIONS

try:
    from fabricapp.ai import prompt_builder_old as old
except ImportError:
    old = None
    print("NOTE: prompt_builder_old.py not found - Check 1 skipped.\n")

# All (garment_type, garment_style) pairs that exist.
GARMENTS = []
for garment_type, styles in GARMENT_PROMPTS.items():
    if garment_type in GARMENT_STYLE_OPTIONS:
        for style in styles:
            GARMENTS.append((garment_type, style))
    else:
        GARMENTS.append((garment_type, None))

CASES = [(g, s, False) for g, s in GARMENTS] + [(None, None, True)]

problems = 0

# ---------------------------------------------------------------
# Check 1: without pose, new prompts must equal the old prompts
# ---------------------------------------------------------------
if old is not None:
    SCENARIOS = [new.SCENARIO_PERSON_PHOTO, new.SCENARIO_FACE_PHOTO, new.SCENARIO_GENERATED_PERSON]
    GENDERS = ["men", "women", "boy", "girl"]
    BODY_TYPES = [None, "slim", "plus"]
    CAMERAS = [None, "front"]
    BACKGROUNDS = [None, "royal_courtyard"]
    NOTES = [None, "test note"]

    checked = 0
    diff = 0
    for scenario, gender, body, camera, bg, note in product(
        SCENARIOS, GENDERS, BODY_TYPES, CAMERAS, BACKGROUNDS, NOTES
    ):
        for garment_type, garment_style, use_garment_image in CASES:
            kwargs = dict(
                scenario=scenario, garment_type=garment_type,
                garment_style=garment_style, use_garment_image=use_garment_image,
                gender=gender, body_type=body, camera_view=camera,
                background=bg, additional_style_note=note,
            )
            a = old.build_prompt(**kwargs)
            b = new.build_prompt(**kwargs)
            checked += 1
            if a != b:
                diff += 1
                if diff <= 5:
                    print("DIFFERENT (no pose):", kwargs)
    print(f"Check 1: {checked} combinations compared with the old builder, differences = {diff}")
    problems += diff

# ---------------------------------------------------------------
# Check 2: person photo + pose  ->  person_pose scenario
# ---------------------------------------------------------------
c2 = 0
checked2 = 0
for pose in POSE_OPTIONS:
    scenario = new.detect_scenario(True, None, pose)
    if scenario != new.SCENARIO_PERSON_POSE:
        c2 += 1
        print(f"PROBLEM: detect_scenario(person, pose={pose}) gave {scenario}")
        continue
    for garment_type, garment_style, use_garment_image in CASES:
        sentence = get_pose_sentence(pose, garment_type, garment_style)
        result = new.build_prompt(
            scenario=scenario, garment_type=garment_type,
            garment_style=garment_style, use_garment_image=use_garment_image,
            pose=pose,
        )
        checked2 += 1
        prompt = result["prompt"]
        if sentence not in prompt or "image 2" not in prompt or prompt.startswith("Edit image 0"):
            c2 += 1
            print(f"PROBLEM person_pose pose={pose} garment={garment_type}/{garment_style}")

# person photo WITHOUT pose must still use the tested edit-mode path
if new.detect_scenario(True, None, None) != new.SCENARIO_PERSON_PHOTO:
    c2 += 1
    print("PROBLEM: person photo without pose is not person_photo")

print(f"Check 2: {checked2} person_pose prompts checked, problems = {c2}")
problems += c2

# ---------------------------------------------------------------
# Check 3: own-model scenarios carry the pose text
# ---------------------------------------------------------------
c3 = 0
checked3 = 0
for pose in POSE_OPTIONS:
    for scenario in (new.SCENARIO_GENERATED_PERSON, new.SCENARIO_FACE_PHOTO):
        for garment_type, garment_style, use_garment_image in CASES:
            if garment_type == "saree" and not use_garment_image:
                # Generated-person and face-photo sarees use the resolver,
                # whose pose text is owned by the saree pose-parts table.
                sentence, _ = get_saree_pose_parts(pose, DEFAULT_OWN_MODEL_POSE)
            else:
                sentence = get_pose_sentence(pose, garment_type, garment_style)
            result = new.build_prompt(
                scenario=scenario, garment_type=garment_type,
                garment_style=garment_style, use_garment_image=use_garment_image,
                gender="men", pose=pose,
            )
            checked3 += 1
            prompt = result["prompt"]
            if sentence not in prompt or DEFAULT_OWN_MODEL_POSE in prompt:
                c3 += 1
                print(f"PROBLEM own-model pose={pose} scenario={scenario} garment={garment_type}/{garment_style}")

print(f"Check 3: {checked3} own-model prompts checked, problems = {c3}")
problems += c3

# ---------------------------------------------------------------
# Check 4: kurti fabric must not be assigned to its white pants
# ---------------------------------------------------------------
c4 = 0
kurti_cases = [(new.SCENARIO_PERSON_PHOTO, None)] + [
    (new.SCENARIO_PERSON_POSE, pose) for pose in POSE_OPTIONS
]
for scenario, pose in kurti_cases:
    result = new.build_prompt(
        scenario=scenario,
        garment_type="kurti_pant",
        pose=pose,
    )
    prompt = result["prompt"]
    required = (
        "plain, solid white",
        "full-length sleeves",
    )
    if scenario == new.SCENARIO_PERSON_POSE:
        required += (
            "a kurti made from the fabric in image 1, paired with plain white pants",
            "Use image 1 only as the kurti fabric reference",
            "exactly two arms, two hands, two legs and two feet",
            get_pose_sentence(pose, "kurti_pant"),
        )
    else:
        required += ("image 1's fabric is for the kurti only",)
    if any(text not in prompt for text in required):
        c4 += 1
        print(f"PROBLEM kurti_pant white-pants rules missing in scenario={scenario}")
    if "white pants made from the fabric in image 1" in prompt:
        c4 += 1
        print(f"PROBLEM kurti_pant TASK assigns fabric to pants in scenario={scenario}")
    if scenario == new.SCENARIO_PERSON_POSE and len(prompt.split()) > 600:
        c4 += 1
        print(f"PROBLEM kurti_pant prompt is too long in scenario={scenario} pose={pose}")
    if pose == "pallu_on_head" and "No dupatta." in prompt:
        c4 += 1
        print("PROBLEM pallu_on_head conflicts with the kurti dupatta rule")
    if pose == "sleeve_adjust_stand" and "near the elbow" in prompt:
        c4 += 1
        print("PROBLEM sleeve_adjust_stand conflicts with full-length sleeves")
print(f"Check 4: {len(kurti_cases)} kurti_pant fabric/pants prompts checked, problems = {c4}")
problems += c4

print("\nRESULT:", "ALL OK" if problems == 0 else f"{problems} PROBLEM(S) - send me this output")
