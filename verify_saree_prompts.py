"""
Offline Verification Script for Saree Prompts.
Run from the project root:
    SECRET_KEY=dummy python verify_saree_prompts.py
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tryon.settings")

import django
django.setup()

from fabricapp.ai.prompt_builder import detect_scenario, build_prompt

def run_tests():
    passed = 0
    failed = 0

    def assert_check(name, condition, error_msg=""):
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}: {error_msg}")
            failed += 1

    print("==================================================")
    print("TEST SUITE: Saree Prompt Verification")
    print("==================================================")

    # 1. Test person_pose with cross_leg_chair_recline and riverside_ghat background
    print("\n1. Saree person_pose with cross_leg_chair_recline & background:")
    scenario = detect_scenario(has_person_image=True, face_choice=None, pose="cross_leg_chair_recline")
    res = build_prompt(
        scenario=scenario,
        garment_type="saree",
        pose="cross_leg_chair_recline",
        background="riverside_ghat"
    )
    p1 = res["prompt"]
    assert_check("No duplicate MODESTY_FINAL", p1.count("FINAL RULE") == 1, f"Found {p1.count('FINAL RULE')} occurrences")
    assert_check("Armchair note present for cross_leg pose", "armchair" in p1.lower())
    assert_check("No duplicate background instruction", p1.count("BACKGROUND:") == 1)

    # 2. Test generated_person (own-model) with cross_leg_chair_recline and background
    print("\n2. Saree generated_person with cross_leg_chair_recline & background:")
    scenario = detect_scenario(has_person_image=False, face_choice=None, pose="cross_leg_chair_recline")
    res = build_prompt(
        scenario=scenario,
        garment_type="saree",
        gender="woman",
        body_type="medium",
        pose="cross_leg_chair_recline",
        background="riverside_ghat"
    )
    p2 = res["prompt"]
    assert_check("No duplicate MODESTY_FINAL", p2.count("FINAL RULE") == 1, f"Found {p2.count('FINAL RULE')} occurrences")
    assert_check("Subject comes before background", p2.find("SUBJECT:") < p2.find("BACKGROUND:") if "SUBJECT:" in p2 and "BACKGROUND:" in p2 else True)
    assert_check("Blouse solid requirement present", "100% plain, solid" in p2 or "solid matching color" in p2)

    # 3. Test face_photo with saree & background
    print("\n3. Saree face_photo with pose & background:")
    scenario = detect_scenario(has_person_image=False, face_choice="anaya", pose="cross_leg_chair_recline")
    res = build_prompt(
        scenario=scenario,
        garment_type="saree",
        gender="woman",
        body_type="medium",
        pose="cross_leg_chair_recline",
        use_face_reference=True,
        background="riverside_ghat"
    )
    p3 = res["prompt"]
    assert_check("No duplicate MODESTY_FINAL", p3.count("FINAL RULE") == 1, f"Found {p3.count('FINAL RULE')} occurrences")
    assert_check("Opaque drape/midriff instruction present", "opaque drape" in p3.lower() or "midriff" in p3.lower())

    # 4. Test person_photo (default saree edit, no pose)
    print("\n4. Saree person_photo (default edit):")
    scenario = detect_scenario(has_person_image=True, face_choice=None, pose=None)
    res = build_prompt(
        scenario=scenario,
        garment_type="saree"
    )
    p4 = res["prompt"]
    assert_check("No duplicate MODESTY_FINAL", p4.count("FINAL RULE") == 1, f"Found {p4.count('FINAL RULE')} occurrences")

    print("\n==================================================")
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("==================================================")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
