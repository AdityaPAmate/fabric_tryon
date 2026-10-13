"""
Offline Verification Script for Kurti-Pant Fixes (Zero Cost / No Cloudflare Calls).
Run from the project root:
    python verify_kurti_fixes.py
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tryon.settings")

import django
django.setup()

from fabricapp.ai.prompt_builder import detect_scenario, build_prompt
from fabricapp.ai.camera_data import get_framing
from fabricapp.ai.pose_data import get_pose_sentence

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
    print("TEST SUITE: Kurti-Pant 2026-10-09 Reports Verification")
    print("==================================================")

    # 1. Test Report 1: Side view leg separation
    print("\n1. Report 1 (Side view leg separation):")
    p1 = build_prompt(
        scenario=detect_scenario(True, None, None, camera_view="side"),
        garment_type="kurti_pant",
        camera_view="side"
    )["prompt"]
    assert_check(
        "Legs separated in side view",
        "both legs straight and naturally separated so both pant legs and feet remain distinct and visible" in p1
    )

    # 2. Test Report 2 & 5: pocket_walk + side view walking pace
    print("\n2. Report 2 & 5 (pocket_walk + side view running stride fix):")
    p2 = build_prompt(
        scenario=detect_scenario(True, None, pose="pocket_walk", camera_view="side"),
        garment_type="kurti_pant",
        pose="pocket_walk",
        camera_view="side"
    )["prompt"]
    assert_check(
        "Small natural step, feet close together",
        "taking a small natural step with feet close together (not a wide stride, not running)" in p2
    )
    assert_check(
        "Exactly two arms and two hands on side pocket walk",
        "exactly two arms and two hands in total" in p2
    )

    # 3. Test Report 3: rail_wide_arm_side_look leg bend
    print("\n3. Report 3 (rail_wide_arm_side_look leg bend fix):")
    p3 = build_prompt(
        scenario=detect_scenario(True, None, pose="rail_wide_arm_side_look"),
        garment_type="kurti_pant",
        pose="rail_wide_arm_side_look"
    )["prompt"]
    assert_check(
        "Legs nearly straight without extreme knee bend",
        "both legs nearly straight with one foot resting naturally slightly behind the other, gentle natural stance without extreme knee bend" in p3
    )

    # 4. Test Report 4: Young kid reference not aged up to woman
    print("\n4. Report 4 (Preserve child/girl age, no hardcoded 'woman'):")
    p4 = build_prompt(
        scenario=detect_scenario(True, None, pose="pocket_walk"),
        garment_type="kurti_pant",
        pose="pocket_walk"
    )["prompt"]
    assert_check(
        "No hardcoded 'Change the woman's posture'",
        "Change the woman's posture" not in p4
    )
    assert_check(
        "Exact age retention instruction present",
        "exact age (if image 2 is a child or girl, keep her clearly as a child/girl, do not age her into an adult)" in p4
    )

    # 5. Test Report 6: Facial structure preservation
    print("\n5. Report 6 (Facial feature locking):")
    p6 = build_prompt(
        scenario=detect_scenario(True, None, pose="low_hand_clasp_front"),
        garment_type="kurti_pant",
        pose="low_hand_clasp_front"
    )["prompt"]
    assert_check(
        "Facial structure lock present",
        "Copy the face accurately from image 2 — same eyes, eyebrows, nose, lips and face shape" in p6
    )

    # 6. Test Reports 7 & 8: gender="girl" + body_type="plus"
    print("\n6. Reports 7 & 8 (body_type='plus' for gender='girl'):")
    p78 = build_prompt(
        scenario=detect_scenario(False, None),
        garment_type="kurti_pant",
        gender="girl",
        body_type="plus"
    )["prompt"]
    assert_check(
        "Chubby plus-size build in child subject description",
        "noticeably chubby, plus-size build" in p78
    )
    assert_check(
        "Explicit BODY BUILD instructions for child",
        "BODY BUILD: the child has a noticeably chubby, plus-size build with fuller cheeks, a rounded belly and thicker arms and legs" in p78
    )

    # 7. Test Reports 9 & 10: Own-model 3 hands prevention
    print("\n7. Reports 9 & 10 (Own-model limb count rules):")
    p9 = build_prompt(
        scenario=detect_scenario(False, None, pose="three_quarter_hand_adjust"),
        garment_type="kurti_pant",
        gender="girl",
        body_type="plus",
        pose="three_quarter_hand_adjust"
    )["prompt"]
    assert_check(
        "three_quarter_hand_adjust has 'never a third hand'",
        "exactly two arms and two hands in total, never a third hand" in p9
    )
    assert_check(
        "p9 has OWN_MODEL_LIMBS_LINE",
        "LIMBS: exactly two arms, two hands, two legs and two feet in total in the pose above — never a third hand, an extra arm or a duplicate limb" in p9
    )

    p10 = build_prompt(
        scenario=detect_scenario(False, None, pose="sleeve_adjust_stand"),
        garment_type="kurti_pant",
        gender="girl",
        body_type="plus",
        pose="sleeve_adjust_stand"
    )["prompt"]
    assert_check(
        "sleeve_adjust_stand has 'never a third hand'",
        "exactly two arms and two hands in total, never a third hand" in p10
    )
    assert_check(
        "p10 has OWN_MODEL_LIMBS_LINE",
        "LIMBS: exactly two arms, two hands, two legs and two feet in total in the pose above — never a third hand, an extra arm or a duplicate limb" in p10
    )

    print("\n==================================================")
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("==================================================")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
