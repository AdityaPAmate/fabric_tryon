"""Offline regression checks for the saree prompt package only.

Run from the project root with: python check_saree_regressions.py
These checks validate prompt construction, not Cloudflare image quality.
"""
from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Supply minimal dependency stubs so the prompt package can be checked
# without Django settings, API credentials, or the rest of the application.
# The project itself supplies these modules during real API execution.
pose_data = types.ModuleType("fabricapp.ai.pose_data")
pose_data.POSE_INSTRUCTIONS = {
    name: f"generic fallback pose for {name}"
    for name in (
        "back_turn_hair_touch", "cross_leg_chair_recline",
        "hands_on_hips_side_look", "low_hand_clasp_front", "pallu_on_head",
        "pocket_walk", "rail_wide_arm_side_look", "sleeve_adjust_stand",
        "three_quarter_hand_adjust",
    )
}

camera_data = types.ModuleType("fabricapp.ai.camera_data")
def get_framing(camera_view=None):
    if camera_view == "close_up":
        return {"shot": "close-up", "shown": "the upper body", "fill": "", "output_rule_face": "", "output_rule_person": ""}
    if camera_view == "side":
        return {"shot": "full-body", "shown": "the whole person", "fill": " from head to feet", "output_rule_face": "", "output_rule_person": ""}
    return {"shot": "full-body", "shown": "the whole person", "fill": " from head to feet", "output_rule_face": "", "output_rule_person": ""}
camera_data.get_framing = get_framing

prompts = types.ModuleType("fabricapp.ai.prompts")
prompts.BACKGROUND_DESCRIPTIONS = {
    "riverside_ghat": "a riverside ghat with stone steps",
    "white_marble_terrace": "a white marble terrace",
}
prompts.get_camera_view_instruction = lambda camera_view: (
    f"show a {camera_view} camera view" if camera_view else ""
)

sys.modules["fabricapp.ai.pose_data"] = pose_data
sys.modules["fabricapp.ai.camera_data"] = camera_data
sys.modules["fabricapp.ai.prompts"] = prompts

poses = importlib.import_module("fabricapp.ai.saree.poses")
builder = importlib.import_module("fabricapp.ai.saree.builder")

checks = []
def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    checks.append(message)

# Every known pose owns literal pallu text; none refers to style keys.
for name, entry in poses.SAREE_POSES.items():
    check(isinstance(entry.get("pallu"), str), f"{name}: direct pallu text exists")
    parts = poses.get_pose_parts(name)
    check(bool(parts["pose_text"]), f"{name}: pose resolves")
    check(bool(parts["pallu_text"]), f"{name}: pallu resolves")

# Reported pose failures: explicit pose geometry and supporting props.
check("upholstered armchair" in poses.SAREE_POSES["cross_leg_chair_recline"]["pose"], "chair pose explicitly retains armchair")
check("across the lap" in poses.SAREE_POSES["cross_leg_chair_recline"]["pallu"], "seated pallu is explicitly across lap")
check("back not arched" in poses.SAREE_POSES["back_turn_hair_touch"]["pose"], "back-turn pose remains non-suggestive")
check("both hands softly clasped together" in poses.SAREE_POSES["pallu_on_head"]["pose"], "head pallu pose keeps hands clasped low")
check("one single continuous pallu" in poses.SAREE_POSES["pallu_on_head"]["pallu"], "head pallu uses one continuous panel")
check("the left of the image" in poses.SAREE_POSES["pallu_on_head"]["pallu"], "head pallu direction is explicit")
check("single palm" in poses.SAREE_POSES["rail_wide_arm_side_look"]["pose"], "ledge pose explicitly avoids duplicate hand")
check("both hands are clearly separate and visible" in poses.SAREE_POSES["three_quarter_hand_adjust"]["pose"], "hand-adjust pose explicitly separates hands")
check("80 to 90 degrees" in poses.DEFAULT_POSES["side"], "side camera default is a clear side profile")

# Generated-person + chosen-face prompts and reported fabric/blouse issues.
result = builder.build_saree_prompt(
    "face_photo", gender="women", body_type="plus", pose="low_hand_clasp_front",
    background="white_marble_terrace", use_face_reference=True,
)
prompt = result["prompt"]
check("BODY BUILD: the body is clearly PLUS-SIZE" in prompt, "plus body type is present with selected face")
check("BACKGROUND: a white marble terrace" in prompt, "selected background is present with face choice")
check("same solid colour" not in prompt, "no stale blouse wording overrides solid-colour rule")
check("Do not copy image 2's crop, body, clothes, pose or background" in prompt, "face reference is identity-only")
check("no print, motifs, woven pattern or decorative border" in prompt, "blouse is solid and pattern-free")
check("Do not desaturate" in prompt, "fabric saturation is protected")
check("fully opaque" in prompt, "fabric opacity and stomach coverage are specified")
check(prompt.index("GARMENT:") < prompt.index("POSE (") < prompt.index("PALLU"), "garment then pose then pallu priority order is correct")
check(prompt.rstrip().endswith("Only the face, neck, hands, forearms and feet may remain uncovered."), "final modesty rule remains last")

# Reference-image route: border and blouse are controlled without redraping.
ref = builder.build_saree_prompt(
    "pose_reference", gender="women", body_type="slim", pose="pallu_on_head",
    background="white_marble_terrace", use_face_reference=False,
)
ref_prompt = ref["prompt"]
check("preserve the exact border shown in image 1" in ref_prompt.lower(), "reference route preserves source border")
check("no print, motifs, pattern or saree-border artwork" in ref_prompt, "reference blouse stays solid")
check("pallu hangs only on the left side of the frame" in ref_prompt, "head reference pallu side remains explicit")

# Other body parameters/backgrounds are resolved without conditional prose.
plus_generated = builder.build_saree_prompt(
    "generated_person", gender="women", body_type="plus", pose="low_hand_clasp_front",
    background="white_marble_terrace",
)
check("plus-size" in plus_generated["prompt"].lower(), "plus body type is present without face choice")
check("BACKGROUND: a white marble terrace" in plus_generated["prompt"], "background is present without face choice")

person_pose = builder.build_saree_prompt(
    "person_pose", gender="women", pose="three_quarter_hand_adjust",
    background="white_marble_terrace", use_face_reference=True,
)
check("Do not copy image 2 clothing, pose or background" in person_pose["prompt"], "person-photo identity reference excludes source pose")
check("right hand gently holds the left wrist" in person_pose["prompt"], "person pose route retains specific hand arrangement")

side = builder.build_saree_prompt("generated_person", gender="women", pose=None, camera_view="side")
check("clear side profile" in side["prompt"], "side camera instruction is used when no pose is supplied")
check("unless" not in side["prompt"].lower() and "otherwise" not in side["prompt"].lower(), "resolved prompt has no conditional branch wording")

print(f"PASS: {len(checks)} saree prompt regression checks")
for item in checks:
    print(f"  OK  {item}")
