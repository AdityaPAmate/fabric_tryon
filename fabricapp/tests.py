import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from .ai.main import generate_tryon_image
from .ai.shirt.builder import _fabric_colour_reference


class ShirtFabricColourTests(SimpleTestCase):
    def swatch(self):
        image = Image.new("RGB", (80, 40), "#3e281b")
        image.paste("#1a6b44", (40, 0, 80, 40))
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        return SimpleUploadedFile("swatch.png", buffer.getvalue(), "image/png")

    def test_palette_retains_multiple_fabric_colours(self):
        reference = _fabric_colour_reference({"fabric_image": self.swatch()})
        self.assertIn("#3E281B", reference)
        self.assertIn("#1A6B44", reference)

    def test_palette_uses_same_crop_as_provider_input(self):
        reference = _fabric_colour_reference({
            "fabric_image": self.swatch(),
            "options": {"fabric_crop_box": [40, 0, 80, 40]},
        })
        self.assertIn("#1A6B44", reference)
        self.assertNotIn("#3E281B", reference)

    def test_palette_leaves_uploaded_file_unchanged(self):
        source = self.swatch()
        original = source.read()
        source.seek(13)
        _fabric_colour_reference({"fabric_image": source})
        self.assertEqual(source.tell(), 13)
        source.seek(0)
        self.assertEqual(source.read(), original)

    @patch("fabricapp.ai.main._generate_with_engine")
    def test_shirt_routes_pass_measured_colours_and_keep_requested_settings(self, engine):
        for route in ("generated", "face", "person", "person_pose"):
            with self.subTest(route=route):
                kwargs = {}
                if route == "face":
                    kwargs["face_choice"] = "vihaan"
                if route.startswith("person"):
                    kwargs["person_image"] = self.swatch()
                if route == "person_pose":
                    kwargs["pose"] = "low_hand_clasp_front"
                generate_tryon_image(
                    fabric_image=self.swatch(), garment_type="shirt",
                    gender="men", background="riverside_ghat",
                    seed=42, guidance=7, **kwargs,
                )
                config = engine.call_args.kwargs["prompt_config"]
                self.assertIn("#3E281B", config["prompt"])
                self.assertIn("#1A6B44", config["prompt"])
                self.assertEqual(config["seed"], 42)
                self.assertEqual(config["guidance"], 7)
                if config.get("safety_fallback_prompt"):
                    self.assertIn("#3E281B", config["safety_fallback_prompt"])

    @patch("fabricapp.ai.main._generate_with_engine")
    def test_other_garments_do_not_receive_shirt_colour_rules(self, engine):
        garments = {
            "kurta": ("plain", "men"),
            "kurti_pant": (None, "women"),
            "blazer": ("business", "men"),
            "pant": (None, "men"),
            "saree": (None, "women"),
        }
        for garment, (style, gender) in garments.items():
            with self.subTest(garment=garment):
                generate_tryon_image(
                    fabric_image=self.swatch(), garment_type=garment,
                    garment_style=style, gender=gender, seed=42, guidance=7,
                )
                config = engine.call_args.kwargs["prompt_config"]
                self.assertNotIn("SWATCH PALETTE:", config["prompt"])

    @patch("fabricapp.ai.main._generate_with_engine")
    def test_ready_made_garment_mode_does_not_use_fabric_palette(self, engine):
        generate_tryon_image(
            garment_image=self.swatch(), garment_type="shirt", gender="men",
            face_choice="vihaan", seed=31, guidance=4.5,
        )
        config = engine.call_args.kwargs["prompt_config"]
        self.assertNotIn("SWATCH PALETTE:", config["prompt"])
        self.assertEqual(config["seed"], 31)
        self.assertEqual(config["guidance"], 4.5)
