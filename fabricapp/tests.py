import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from .ai.main import generate_tryon_image
from .ai.shirt.builder import _fabric_colour_reference


class GarmentFallbackPromptTests(SimpleTestCase):
    """Check retry prompt routing without calling the image provider."""

    def test_fabric_routes_keep_selected_instructions_in_retry(self):
        from .ai.router import build_prompt_config

        styles = {
            "blazer": ("business", "wedding", "casual"),
            "kurta": ("plain", "sherwani", "pathani", "jodhpuri"),
            "kurti_pant": (None,),
            "pant": (None,),
        }
        for garment, garment_styles in styles.items():
            for style in garment_styles:
                for scenario in ("person_photo", "person_pose", "face_photo", "generated_person"):
                    with self.subTest(garment=garment, style=style, scenario=scenario):
                        config = build_prompt_config(
                            scenario=scenario, garment_type=garment, garment_style=style,
                            context={
                                "gender": "women" if garment == "kurti_pant" else "men",
                                "body_type": "plus", "pose": "pocket_walk",
                                "background": "white_marble_terrace",
                                "garment_details": ["half_sleeves", "with_dupatta"]
                                if garment == "kurti_pant" else [],
                                "additional_style_note": "Keep the footwear brown.",
                                "use_face_reference": scenario == "face_photo",
                            }, seed=19, guidance=4.5,
                        )
                        original = config["prompt"]
                        fallback = config["safety_fallback_prompt"]
                        # Blazer resolves the same attributes into a shorter
                        # prompt; other garments retain the full original.
                        if garment == "blazer":
                            self.assertLess(len(fallback.split()), len(original.split()))
                            self.assertIn("Keep the footwear brown.", fallback)
                            self.assertIn("blazer-structured-v3", config["prompt_version"])
                            self.assertIn("white marble terrace", fallback)
                            self.assertIn("plain solid", fallback)
                        else:
                            self.assertTrue(fallback.startswith(original.rstrip() + " "))
                            self.assertEqual(fallback.count("RETRY PRESENTATION:"), 1)
                        self.assertNotIn("RETRY PRESENTATION:", original)
                        self.assertIn("opaque", fallback)
                        if garment != "blazer" or scenario != "generated_person":
                            self.assertIn("apparent age", fallback)
                        self.assertEqual((config["seed"], config["guidance"]), (19, 4.5))

    def test_blazer_retry_keeps_child_build_without_inventing_a_reference(self):
        from .ai.router import build_prompt_config

        for scenario in ("generated_person", "face_photo"):
            config = build_prompt_config(
                scenario=scenario, garment_type="blazer", garment_style="wedding",
                context={"gender": "boy", "body_type": "plus", "camera_view": "close_up"},
            )
            fallback = config["safety_fallback_prompt"]
            self.assertIn("child-sized clothing", fallback)
            self.assertIn("plus-size", fallback)
            self.assertNotIn("fuller adult build", fallback)
            self.assertIn("shawl lapel", fallback.lower())
            self.assertIn("no necktie and no bow tie", fallback)
            if scenario == "generated_person":
                self.assertNotIn("image 2", fallback.lower())
            else:
                self.assertIn("Image 2 supplies facial identity", fallback)

    def test_saree_routes_do_not_gain_a_fallback(self):
        from .ai.router import build_prompt_config

        for scenario in ("person_photo", "person_pose", "face_photo", "generated_person", "pose_reference"):
            with self.subTest(scenario=scenario):
                config = build_prompt_config(
                    scenario=scenario, garment_type="saree",
                    context={"gender": "women", "pose": "pallu_on_head"},
                )
                self.assertNotIn("safety_fallback_prompt", config)

    def test_ready_made_garment_route_keeps_its_own_prompt(self):
        from .ai.router import build_prompt_config

        for garment in ("blazer", "kurta", "kurti_pant", "pant", "saree"):
            with self.subTest(garment=garment):
                config = build_prompt_config(
                    scenario="person_photo", garment_type=garment,
                    use_garment_image=True, context={},
                )
                # A ready-made garment supplies its own cut and length. Fabric
                # instructions must not silently replace that design.
                self.assertNotIn("safety_fallback_prompt", config)


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


class ProviderRetryHttpTests(SimpleTestCase):
    """Exercise the real multipart client against a local HTTP provider.

    Postman CLI cannot start on this machine (unreadable managed manifest).
    This local server replays the observed 400/3030 response, not a mocked
    requests response. No provider credentials or live generation are needed.
    """

    swatch = ShirtFabricColourTests.swatch

    def test_shirt_rejection_is_not_retried_but_other_garments_keep_policy(self):
        import base64
        import json
        import threading
        from email.parser import BytesParser
        from email.policy import default
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import requests
        from .ai.cloudflare_engine import CloudflareGenerationError

        captured = []
        reject_all = False
        buffer = io.BytesIO()
        Image.new("RGB", (1152, 1536), "white").save(buffer, "PNG")
        image = buffer.getvalue()
        error_message = "Your output has been flagged."
        error_code = 3030
        error_status = 400

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                nonlocal image
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                message = BytesParser(policy=default).parsebytes(
                    ("Content-Type: " + self.headers["Content-Type"] + "\r\n\r\n").encode() + raw
                )
                captured.append({
                    part.get_param("name", header="content-disposition"): part.get_payload(decode=True)
                    for part in message.iter_parts()
                })
                output = io.BytesIO()
                Image.new("RGB", (int(captured[-1]["width"]), int(captured[-1]["height"])), "white").save(output, "PNG")
                image = output.getvalue()
                # First request fails; a second would succeed if retried.
                first = reject_all or len(captured) == 1
                self.send_response(error_status if first else 200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"errors": [{"code": error_code, "message": error_message}]}
                    if first else {"result": {"image": base64.b64encode(image).decode()}}
                ).encode())

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        send = requests.Session.send

        def local_send(session, request, **kwargs):
            request.url = f"http://127.0.0.1:{server.server_port}/ai/run"
            kwargs["proxies"] = {}
            return send(session, request, **kwargs)

        try:
            with self.settings(CLOUDFLARE_ACCOUNT_ID="test", CLOUDFLARE_API_TOKEN="test",
                               SAVE_DEBUG_FILES=False), patch.object(requests.Session, "send", local_send):
                # Explicit internal diagnostic override; normal shirt requests
                # retain the existing alternate-attempt policy.
                with patch("fabricapp.ai.shirt.builder.get_generation_settings",
                           return_value={"seed": 42, "guidance": 7, "safety_retry_count": 0}):
                    with self.assertRaises(CloudflareGenerationError) as rejected:
                        generate_tryon_image(
                            fabric_image=self.swatch(), face_image=self.swatch(),
                            garment_type="shirt", gender="men", body_type="plus", seed=42,
                        )
                self.assertEqual(rejected.exception.provider_code, 3030)
                self.assertEqual(len(captured), 1)
                self.assertEqual(captured[0]["seed"], b"42")
                self.assertIn("PLUS-SIZE", captured[0]["prompt"].decode())
                self.assertIn("input_image_2", captured[0])

                captured.clear()
                result = generate_tryon_image(
                    fabric_image=self.swatch(), garment_type="kurta", garment_style="plain",
                    gender="men", seed=42,
                )
                self.assertEqual(len(captured), 2)
                self.assertEqual([item["seed"] for item in captured], [b"42", b"43"])
                self.assertTrue(captured[1]["prompt"].startswith(captured[0]["prompt"].rstrip()))
                self.assertIn(b"RETRY PRESENTATION:", captured[1]["prompt"])
                self.assertEqual(result.image_bytes, image)

                for source in ({"face_image": self.swatch()}, {"person_image": self.swatch()}):
                    captured.clear()
                    result = generate_tryon_image(
                        fabric_image=self.swatch(), garment_type="blazer", garment_style="business",
                        pose="low_hand_clasp_front", background="white_marble_terrace",
                        gender="men", seed=42, **source,
                    )
                    self.assertEqual([item["seed"] for item in captured], [b"42", b"43"])
                    self.assertNotEqual(captured[0]["prompt"], captured[1]["prompt"])
                    self.assertLess(len(captured[1]["prompt"]), len(captured[0]["prompt"]))
                    trace = result.diagnostics
                    self.assertEqual(trace["prompt_version"], "blazer-structured-v3")
                    self.assertEqual(trace["effective_seed"], 43)
                    self.assertEqual([a["fallback_prompt"] for a in trace["attempts"]], [False, True])
                    self.assertIn("input_image_2", captured[1])
                    self.assertEqual(captured[0]["input_image_2"], captured[1]["input_image_2"])

                # A persistent rejection still stops after the one permitted
                # alternate sample and carries evidence for the saved report.
                captured.clear()
                reject_all = True
                with self.assertRaises(CloudflareGenerationError) as rejected:
                    generate_tryon_image(
                        fabric_image=self.swatch(), garment_type="blazer", garment_style="casual",
                        gender="men", seed=42,
                    )
                self.assertEqual(len(captured), 2)
                self.assertEqual(rejected.exception.provider_code, 3030)
                self.assertEqual(len(rejected.exception.diagnostics["attempts"]), 2)
                for error_code, error_message, error_status, category in (
                    (3030, "Invalid input image", 400, "invalid_provider_input"),
                    (3030, "Input prompt contains NSFW content", 400, "input_rejected"),
                    (3030, "Undocumented failure", 400, "unknown_provider_error"),
                    (3036, "Daily allocation exhausted", 429, "allocation_exhausted"),
                ):
                    captured.clear()
                    with self.assertRaises(CloudflareGenerationError) as rejected:
                        generate_tryon_image(
                            fabric_image=self.swatch(), garment_type="pant", gender="men", seed=42,
                        )
                    self.assertEqual(len(captured), 1)
                    self.assertEqual(rejected.exception.failure_type, category)
                    self.assertEqual(rejected.exception.diagnostics["attempts"][0]["recovery_action"], "stop")

                captured.clear()
                reject_all = False
                error_code, error_message, error_status = 3040, "Capacity temporarily exceeded", 429
                with patch("fabricapp.ai.cloudflare_engine.time.sleep"):
                    result = generate_tryon_image(
                        fabric_image=self.swatch(), garment_type="pant", gender="men", seed=42,
                    )
                self.assertEqual([item["seed"] for item in captured], [b"42", b"42"])
                self.assertEqual(captured[0]["prompt"], captured[1]["prompt"])
                reject_all = True

                # Saree's unknown 3030 still follows the pre-existing seed retry.
                error_code, error_message, error_status = 3030, "Undocumented failure", 400
                captured.clear()
                with self.assertRaises(CloudflareGenerationError) as rejected:
                    generate_tryon_image(fabric_image=self.swatch(), garment_type="saree", gender="women", seed=42)
                self.assertEqual(len(captured), 2)
                self.assertIsNone(rejected.exception.failure_type)
                self.assertIsNone(rejected.exception.diagnostics)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
