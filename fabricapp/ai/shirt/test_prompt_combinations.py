"""Shirt prompt contracts; these tests do not spend provider credits."""
import logging
from itertools import product
from unittest.mock import patch

from django.test import SimpleTestCase

from ..backgrounds import BACKGROUND_OPTIONS
from ..main import generate_tryon_image
from .builder import build_prompt
from .details import SHIRT_TUCKED, SHIRT_UNTUCKED, SLEEVES_FOLDED, SLEEVES_FULL
from .poses import POSE_OPTIONS, requires_full_body_framing
from .prompts import BODY_BUILD


class ShirtPromptCombinationTests(SimpleTestCase):
    def test_all_body_pose_background_and_detail_combinations(self):
        logger = logging.getLogger("fabricapp")
        previous = logger.disabled
        logger.disabled = True
        try:
            for scenario, body, pose, background, details, camera in product(
                ("face_photo", "generated_person"), ("slim", "trim", "plus"),
                (None, *POSE_OPTIONS), (None, *BACKGROUND_OPTIONS),
                ([], ["tucked"], ["folded_sleeves"], ["tucked", "folded_sleeves"]),
                (None, "front", "side", "close_up"),
            ):
                if camera == "close_up" and requires_full_body_framing(pose):
                    continue  # The API rejects this incompatible framing.
                with self.subTest(scenario=scenario, body=body, pose=pose,
                                  background=background, details=details, camera=camera):
                    config = build_prompt(scenario=scenario, context={
                        "gender": "men", "body_type": body, "pose": pose,
                        "background": background, "garment_details": details,
                        "camera_view": camera,
                    }, seed=42, guidance=7)
                    prompt = config["prompt"]
                    self.assertEqual(prompt.count("BODY BUILD:"), 1)
                    self.assertIn(BODY_BUILD[body], prompt)
                    self.assertLess(prompt.index("BODY BUILD:"), prompt.index("POSE:"))
                    self.assertLess(prompt.index("HEM:"), prompt.index("BACKGROUND:"))
                    self.assertEqual(prompt.count("HEM:"), 1)
                    self.assertEqual(prompt.count("SLEEVES:"), 1)
                    self.assertIn(SHIRT_TUCKED if "tucked" in details else SHIRT_UNTUCKED, prompt)
                    self.assertNotIn(SHIRT_UNTUCKED if "tucked" in details else SHIRT_TUCKED, prompt)
                    expected = SLEEVES_FOLDED.format(noun="shirt") if "folded_sleeves" in details else SLEEVES_FULL
                    self.assertIn(expected, prompt)
                    self.assertNotIn("saree", prompt.lower())
                    self.assertNotIn("supplied pose reference", prompt)
                    if "folded_sleeves" in details:
                        self.assertNotIn("sleeve staying fully down", prompt)
                        self.assertNotIn(SLEEVES_FULL, prompt)
                        self.assertNotIn("holding the left sleeve near the wrist", prompt)
                    else:
                        self.assertNotIn(SLEEVES_FOLDED.format(noun="shirt"), prompt)
                    if scenario == "face_photo":
                        self.assertTrue(config["safety_fallback_prompt"].startswith(prompt))
                    else:
                        self.assertNotIn("image 2", prompt.lower())
                    self.assertEqual(config["seed"], 42)
                    self.assertEqual(config["guidance"], 7)
        finally:
            logger.disabled = previous

    @patch("fabricapp.ai.main._generate_with_engine")
    def test_public_entry_point_passes_selected_attributes_in_one_engine_call(self, engine):
        for body in ("slim", "trim", "plus"):
            for source in ({}, {"face_choice": "vihaan"}, {"face_image": object()}):
                engine.reset_mock()
                generate_tryon_image(
                    garment_type="shirt", gender="men", fabric_image=None,
                    body_type=body, pose="sleeve_adjust_stand", background="riverside_ghat",
                    garment_details=["tucked", "folded_sleeves"], seed=19, guidance=4.5,
                    **source,
                )
                engine.assert_called_once()
                config = engine.call_args.kwargs["prompt_config"]
                self.assertIn(BODY_BUILD[body], config["prompt"])
                self.assertIn(SHIRT_TUCKED, config["prompt"])
                self.assertIn("adjusting the folded left sleeve cuff just below the elbow", config["prompt"])
                self.assertEqual((config["seed"], config["guidance"]), (19, 4.5))

    def test_person_routes_preserve_source_build_and_apply_details(self):
        for scenario, details in product(
            ("person_photo", "person_pose"),
            ([], ["tucked"], ["folded_sleeves"], ["tucked", "folded_sleeves"]),
        ):
            prompt = build_prompt(scenario=scenario, context={
                "garment_details": details, "pose": "low_hand_clasp_front",
                "background": "riverside_ghat",
            })["prompt"]
            self.assertIn("body build", prompt)
            self.assertNotIn("BODY BUILD:", prompt)
            self.assertIn(SHIRT_TUCKED if "tucked" in details else SHIRT_UNTUCKED, prompt)
            self.assertEqual(prompt.count("SLEEVES:"), 1)

    def test_children_keep_age_and_body_selection(self):
        for gender, body in product(("boy", "girl"), ("slim", "trim", "plus")):
            config = build_prompt(scenario="face_photo", context={
                "gender": gender, "body_type": body,
            })
            self.assertIn("12-year-old child", config["prompt"])
            self.assertIn(BODY_BUILD[body], config["prompt"])
            self.assertNotIn("Generate an adult", config["prompt"])
