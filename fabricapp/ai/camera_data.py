"""
Stage: Camera framing data (data + one tiny lookup, no prompt logic).

camera_view decides HOW MUCH of the person is shown. prompt_builder.py
puts these pieces into the subject sentence of the own-model prompts, so
the framing never contradicts the rest of the prompt.

Keys of every framing dict:
    shot              -> name of the shot ("full-body", ...)
    shown             -> how much of the person is visible
    fill              -> extra words used only in the generated-person prompt
    output_rule_face  -> closing rule when image 2 is a face reference
    output_rule_person-> closing rule when image 2 is the person's own photo
    pose_default      -> pose used when no pose is requested

camera_view None (not sent) gives exactly the old full-body wording.

NOTE: "front" and "close_up" follow the requirement. "side" is a first
draft and still to be checked against real output.
"""

from .pose_data import DEFAULT_OWN_MODEL_POSE

_FULL_RULE_FACE = (
    "Do NOT output only a face or a close-up, and do not copy the crop of "
    "image 2: the output must be a complete head-to-feet photograph. "
)
_FULL_RULE_PERSON = (
    "Do NOT output only a face or a close-up: the output must be a "
    "complete head-to-feet photograph. "
)

_FULL_BODY = {
    "shot": "full-body",
    "shown": "shown fully from head to feet",
    "fill": " and filling the frame",
    "output_rule_face": _FULL_RULE_FACE,
    "output_rule_person": _FULL_RULE_PERSON,
    "pose_default": DEFAULT_OWN_MODEL_POSE,
}

CAMERA_FRAMING = {
    "front": {
        "shot": "front-facing full-body",
        "shown": (
            "shown fully from head to feet, facing the camera directly, with "
            "the entire body and the full length of the garment clearly "
            "visible in the frame"
        ),
        "fill": " and filling the frame",
        "output_rule_face": _FULL_RULE_FACE,
        "output_rule_person": _FULL_RULE_PERSON,
        "pose_default": "standing in a natural, relaxed pose facing the camera directly",
    },
    "side": {
        "shot": "side-view full-body",
        "shown": (
            "shown fully from head to feet, with the body turned to a clear "
            "side or three-quarter side angle to the camera so the side "
            "silhouette and drape of the garment are visible, and the full "
            "length of the garment in the frame"
        ),
        "fill": " and filling the frame",
        "output_rule_face": _FULL_RULE_FACE,
        "output_rule_person": _FULL_RULE_PERSON,
        "pose_default": (
            "standing in a natural, relaxed pose with the body turned to a "
            "clear side or three-quarter side view"
        ),
    },
    "close_up": {
        "shot": "close-up, head-and-upper-body",
        "shown": (
            "framed as a close-up: showing the head, shoulders, chest and "
            "torso down to about the hip line, so the whole upper part of "
            "the garment is clearly visible, with only a small part of the "
            "trouser or pant just below the waist visible at the bottom "
            "edge of the frame; the knees, legs and feet are NOT visible"
        ),
        "fill": "",
        "output_rule_face": (
            "Do NOT show the full body, and do not copy the crop of image 2: "
            "the output must be a close-up from the head down to the hip "
            "line, as described above. "
        ),
        "output_rule_person": (
            "Do NOT show the full body: the output must be a close-up from "
            "the head down to the hip line, as described above. "
        ),
        "pose_default": "standing in a natural, relaxed pose facing the camera",
    },
}


def get_framing(camera_view):
    """Framing dict for the camera_view; full-body if None / unknown."""
    return CAMERA_FRAMING.get(camera_view, _FULL_BODY)