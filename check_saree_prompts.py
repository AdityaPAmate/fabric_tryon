"""
Offline check + preview for the SAREE prompt route (no API call, no cost).

Run from the project root (the folder that has manage.py):

    python check_saree_prompts.py
        -> builds every pose x scenario x camera_view x background
           combination and runs the sanity checks. Prints ALL OK or the
           list of problems.

    python check_saree_prompts.py --show POSE [SCENARIO] [CAMERA_VIEW] [BACKGROUND]
        -> prints the final prompt of ONE combination, so you can read
           exactly what the model receives. Example:
           python check_saree_prompts.py --show pallu_on_head generated_person
           python check_saree_prompts.py --show cross_leg_chair_recline person_pose front riverside_ghat

SCENARIO is one of: generated_person (default), face_photo, person_pose,
pose_reference.
"""

import logging
import sys

logging.disable(logging.CRITICAL)  # keep the output readable

from fabricapp.ai.pose_data import POSE_OPTIONS
from fabricapp.ai.prompts import BACKGROUND_OPTIONS, CAMERA_VIEW_OPTIONS
from fabricapp.ai.saree.builder import build_saree_prompt
from fabricapp.ai.saree.poses import SAREE_POSES

SCENARIOS = ("generated_person", "face_photo", "person_pose", "pose_reference")

# Wording that must never appear: the prompt must contain only resolved
# instructions.
FORBIDDEN_WORDS = (" unless ", "otherwise", "if the pose")
# Words that make the model draw a salwar suit / trousers instead of a saree.
TROUSER_WORDS = (" pant ", " pants ", " trouser", " churidar", " pajama")


def build(pose, scenario, camera_view=None, background=None):
    return build_saree_prompt(
        scenario,
        gender="women",
        body_type="slim",
        pose=pose,
        camera_view=camera_view,
        background=background,
        additional_style_note=None,
        use_face_reference=(scenario in ("face_photo", "pose_reference")),
    )


def check_one(label, config, scenario, problems):
    if config is None:
        problems.append(f"{label}: no prompt returned")
        return
    prompt = config["prompt"]
    low = " " + prompt.lower() + " "

    for word in FORBIDDEN_WORDS:
        if word in low:
            problems.append(f"{label}: contains '{word.strip()}'")
    for word in TROUSER_WORDS:
        if word in low:
            problems.append(f"{label}: contains trouser word '{word.strip()}'")
    if "{" in prompt or "}" in prompt:
        problems.append(f"{label}: unfilled placeholder")

    last = prompt.strip().split("FINAL RULE", 1)
    if len(last) != 2 or not prompt.strip().endswith("suggestive."):
        problems.append(f"{label}: FINAL RULE is not the last sentence")

    if scenario != "pose_reference":
        if prompt.count("POSE (") != 1:
            problems.append(f"{label}: POSE line count is not 1")
        if prompt.count("PALLU (") != 1:
            problems.append(f"{label}: PALLU line missing or repeated")
        if prompt.count("LIMBS:") != 1:
            problems.append(f"{label}: LIMBS line count is not 1")
        # Pose + pallu must come before the garment text.
        if prompt.find("POSE (") > prompt.find("GARMENT:"):
            problems.append(f"{label}: POSE is after GARMENT")


def run_all():
    problems = []
    count = 0

    missing = [p for p in POSE_OPTIONS if p not in SAREE_POSES]
    if missing:
        problems.append(
            f"poses in pose_data.POSE_OPTIONS without a saree entry in "
            f"saree/poses.py: {missing}"
        )

    for pose in [None] + list(POSE_OPTIONS):
        for scenario in SCENARIOS:
            for camera_view in [None] + list(CAMERA_VIEW_OPTIONS):
                for background in [None] + list(BACKGROUND_OPTIONS):
                    label = f"{pose}/{scenario}/{camera_view}/{background}"
                    config = build(pose, scenario, camera_view, background)
                    check_one(label, config, scenario, problems)
                    count += 1

    # Unsupported gender must be refused, not silently changed.
    if build_saree_prompt("generated_person", gender="men") is not None:
        problems.append("gender=men was accepted for saree")
    # person_photo (plain edit) is NOT handled by this route.
    if build_saree_prompt("person_photo") is not None:
        problems.append("person_photo must return None (old path)")

    print(f"Checked {count} combinations.")
    if problems:
        print(f"{len(problems)} problem(s):")
        for line in problems[:60]:
            print("  -", line)
        if len(problems) > 60:
            print(f"  ... and {len(problems) - 60} more")
        sys.exit(1)
    print("ALL OK")


def show(args):
    pose = args[0] if args and args[0] != "none" else None
    scenario = args[1] if len(args) > 1 else "generated_person"
    camera_view = args[2] if len(args) > 2 and args[2] != "none" else None
    background = args[3] if len(args) > 3 and args[3] != "none" else None
    config = build(pose, scenario, camera_view, background)
    if config is None:
        print("No prompt returned.")
        sys.exit(1)
    print(config["prompt"])
    print(f"\n[words: {len(config['prompt'].split())}  guidance: "
          f"{config['guidance']}  seed: {config['seed']}]")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--show":
        show(sys.argv[2:])
    else:
        run_all()