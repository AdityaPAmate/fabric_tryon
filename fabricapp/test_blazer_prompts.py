"""Blazer prompt contracts: preserve intent across routes and retry variants."""
from itertools import product
from django.test import SimpleTestCase
from .ai.blazer.builder import build_prompt
from .ai.blazer.poses import POSE_OPTIONS


class BlazerPromptTests(SimpleTestCase):
    def test_all_routes_keep_quality_and_valid_image_roles(self):
        for scenario, style, pose, camera in product(
            ("person_photo", "person_pose", "face_photo", "generated_person"),
            ("business", "wedding", "casual"), (None, *POSE_OPTIONS),
            (None, "front", "side", "close_up"),
        ):
            with self.subTest(scenario=scenario, style=style, pose=pose, camera=camera):
                config = build_prompt(scenario=scenario, garment_style=style, context={
                    "gender": "men", "pose": pose if scenario != "person_photo" else None,
                    "camera_view": camera if scenario != "person_photo" else None,
                }, seed=17, guidance=5)
                self.assertEqual((config["seed"], config["guidance"]), (17, 5))
                for key in ("prompt", "safety_fallback_prompt"):
                    prompt = config[key]
                    for rule in ("saturation", "motif spacing", "two hands", "two feet",
                                 "straight and unrolled", "natural fabric folds and shadows"):
                        self.assertIn(rule, prompt)
                    self.assertNotIn("saree", prompt)
                    self.assertNotIn("supplied pose reference", prompt)
                    self.assertNotIn("wrists of the hanging arms", prompt)
                    if scenario in ("person_photo", "generated_person"):
                        self.assertNotIn("image 2", prompt.lower())
                    else:
                        self.assertIn("image 2", prompt.lower())
                    if scenario in ("person_photo", "person_pose"):
                        self.assertIn("same body build", prompt)
                    if pose and scenario != "person_photo" and camera in ("front", "side"):
                        self.assertIn("FRAMING: full-body,", prompt)
                    if camera == "close_up" and scenario != "person_photo":
                        self.assertNotIn("both full legs and feet visible", prompt)
                    if style == "wedding":
                        self.assertIn("no necktie and no bow tie", prompt)
                    elif style == "casual":
                        self.assertIn("worn OPEN and unbuttoned", prompt)

    def test_reported_poses_have_one_hand_instruction_and_stable_hem(self):
        for pose in ("low_hand_clasp_front", "pocket_walk"):
            config = build_prompt(scenario="person_pose", garment_style="casual",
                                  context={"pose": pose})
            for key in ("prompt", "safety_fallback_prompt"):
                prompt = config[key]
                self.assertIn("base of the seat", prompt)
                self.assertNotIn("left hand resting over the right", prompt)
                self.assertNotIn("or lightly at the hip", prompt)
                if pose == "pocket_walk":
                    self.assertIn("left trouser pocket", prompt)

    def test_child_and_back_view_do_not_request_conflicting_output(self):
        for gender in ("boy", "girl"):
            config = build_prompt(scenario="face_photo", garment_style="wedding", context={
                "gender": gender, "pose": "back_turn_hair_touch", "body_type": "plus",
            })
            for key in ("prompt", "safety_fallback_prompt"):
                prompt = config[key]
                self.assertIn("child-sized", prompt)
                self.assertNotIn("same adult person", prompt)
                self.assertNotIn("clearly visible in the chest pocket", prompt)
                self.assertIn("hidden in this rear view", prompt)
                self.assertIn("out of view rather than drawn on its back", prompt)
