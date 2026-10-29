"""Interpret provider failures without changing prompts or performing requests.

Only recognized messages authorize an alternate generation. Unknown 3030
responses remain unknown rather than being labelled as invalid user input.
Diagnostic messages are allowlisted summaries: provider bodies may echo inputs.
"""

from dataclasses import dataclass


def uses_classified_recovery(garment_type):
    return garment_type != "saree"


@dataclass(frozen=True)
class ProviderFailure:
    code: int | None
    category: str
    action: str
    message: str


def classify_response(response):
    code, messages = None, []
    try:
        payload = response.json()
        errors = payload.get("errors", []) if isinstance(payload, dict) else []
        for error in errors if isinstance(errors, list) else []:
            if not isinstance(error, dict):
                continue
            if code is None:
                try:
                    code = int(error.get("code"))
                except (ValueError, TypeError):
                    pass
            if isinstance(error.get("message"), str):
                messages.append(error["message"].lower())
    except (ValueError, TypeError):
        pass
    message = " ".join(messages)
    if code == 3036:
        return ProviderFailure(code, "allocation_exhausted", "stop", "Provider allocation exhausted.")
    if code == 3030:
        if any(term in message for term in ("input prompt contains nsfw", "request moderated", "policy violation", "input image contains nsfw")):
            return ProviderFailure(code, "input_rejected", "stop", "Provider rejected input content.")
        if any(term in message for term in ("invalid input", "invalid parameter", "missing required", "invalid image")):
            return ProviderFailure(code, "invalid_provider_input", "stop", "Provider reported invalid input.")
        if "output has been flagged" in message or "content moderated" in message:
            return ProviderFailure(code, "output_rejected", "alternate", "Provider flagged generated output.")
        return ProviderFailure(code, "unknown_provider_error", "stop", "Unrecognized provider error; inspect provider request ID.")
    if code == 3040 or response.status_code in (429, 500, 502, 503, 504):
        return ProviderFailure(code, "provider_unavailable", "retry", "Provider temporarily unavailable.")
    return ProviderFailure(code, "unknown_provider_error", "stop", "Unrecognized provider error; inspect provider request ID.")
