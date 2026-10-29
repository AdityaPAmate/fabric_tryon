"""Provider policy edge cases, without external generation or credentials."""

import io
from unittest import TestCase
from unittest.mock import Mock

from PIL import Image

from .ai.provider_errors import classify_response, uses_classified_recovery
from .ai.provider_output import validate_generated_image


class ProviderRecoveryTests(TestCase):
    def test_malformed_errors_do_not_authorize_generation(self):
        for payload in (None, [], {}, {"errors": []}, {"errors": [None]},
                        {"errors": {"code": 3030}}):
            response = Mock(status_code=400)
            response.json.return_value = payload
            self.assertEqual(classify_response(response).action, "stop")
        response.json.side_effect = ValueError("not json")
        self.assertEqual(classify_response(response).category, "unknown_provider_error")

    def test_input_rejection_takes_precedence_over_output_message(self):
        response = Mock(status_code=400)
        response.json.return_value = {"errors": [{"code": "3030", "message":
            "Your output has been flagged. Input prompt contains NSFW content secret-user-text"}]}
        result = classify_response(response)
        self.assertEqual(result.action, "stop")
        self.assertNotIn("secret-user-text", result.message)

    def test_capacity_and_allocation_have_different_policies(self):
        response = Mock(status_code=429)
        for code, action in ((3036, "stop"), (3040, "retry")):
            response.json.return_value = {"errors": [{"code": code}]}
            self.assertEqual(classify_response(response).action, action)

    def test_scope_excludes_saree(self):
        self.assertFalse(uses_classified_recovery("saree"))
        for garment in ("shirt", "blazer", "kurta", "kurti_pant", "pant"):
            self.assertTrue(uses_classified_recovery(garment))

    def test_image_integrity_and_dimensions(self):
        buffer = io.BytesIO()
        Image.new("RGB", (32, 48)).save(buffer, "PNG")
        validate_generated_image(buffer.getvalue(), (32, 48))
        with self.assertRaises(ValueError):
            validate_generated_image(buffer.getvalue(), (48, 32))
        with self.assertRaises(OSError):
            validate_generated_image(b"not an image", (32, 48))
