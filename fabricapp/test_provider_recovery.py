"""Provider policy edge cases, without external generation or credentials."""

import io
from unittest import TestCase
from unittest.mock import Mock

from PIL import Image

from .ai.provider_errors import classify_response, retry_delay, failure_message, uses_classified_recovery
from .ai.provider_output import validate_generated_image


class ProviderRecoveryTests(TestCase):
    def test_retry_after_and_worker_wait_budget(self):
        response = Mock(status_code=429, headers={})
        self.assertEqual(retry_delay(response, 1), 5)
        for value, expected in (("12", 12), ("120", None), ("invalid", 5), ("nan", 5), ("-3", 5)):
            response.headers = {"Retry-After": value}
            self.assertEqual(retry_delay(response, 1), expected)
        response.headers = {"Retry-After": "Fri, 30 Oct 2099 00:00:00 GMT"}
        self.assertIsNone(retry_delay(response, 1))

    def test_4006_is_not_assumed_to_mean_quota(self):
        response = Mock(status_code=429)
        response.json.return_value = {"errors": [{"code": 4006, "message": "Service temporarily at capacity"}]}
        self.assertEqual(classify_response(response).action, "retry")
        response.json.return_value["errors"][0]["message"] = "You have used up your daily free allocation"
        self.assertEqual(classify_response(response).action, "stop")
        self.assertIn("allocation", failure_message(classify_response(response).category))

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
