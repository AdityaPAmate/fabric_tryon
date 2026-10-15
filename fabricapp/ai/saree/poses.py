"""Saree-specific body poses and their exact pallu placement instructions.

Each pose owns its own pallu geometry. Do not route pose-specific draping
through a generic style name: that can silently apply the wrong drape.
Directions below are stated from the VIEWER / IMAGE perspective.
"""

import logging

from ..pose_data import POSE_INSTRUCTIONS

logger = logging.getLogger("fabricapp")

FALL_FULL = " to the knee"
FALL_CLOSE = ""

# Only the no-pose/default-camera path uses this generic drape.
DEFAULT_PALLU_STYLE = (
    "the loose end of the saree rests over the shoulder on the right of "
    "the image and hangs down that same side in soft pleats{fall}; the "
    "left side of the image shows the blouse sleeve, arm and saree wrap"
)

PROP_CHAIR = (
    "An upholstered armchair is present in the scene and the person is "
    "seated in it, never on the bare ground or floor."
)
PROP_LEDGE = (
    "A low wall or ledge at hip height is present in the scene for the "
    "hand to rest on."
)

# "prop"       : sentence added to the BACKGROUND line (a chair / ledge the
#                pose needs must survive a background change).
# "one_person" : adds the one-person rule (seated poses made two bodies).
SAREE_POSES = {
    "back_turn_hair_touch": {
        "pose": (
            "standing upright with her back mostly toward the camera and "
            "the torso turned only slightly toward the right of the image, "
            "head turned over the right shoulder for a natural three-quarter "
            "profile, the left arm raised with elbow bent and fingers gently "
            "touching the hair at the back of the head, the right arm relaxed "
            "straight beside the hip, legs close together with one foot "
            "slightly behind the other; shoulders level, hips neutral and "
            "back not arched"
        ),
        "pallu": (
            "the pallu starts at the shoulder on the left of the image and "
            "falls down the back as one continuous panel in soft pleats{fall}; "
            "the back and waist remain fully covered, with no loose panel "
            "crossing onto the front of the body"
        ),
    },
    # Display name suggestion: Chair Pallu Spread.
    # Keep the API key unchanged so non-saree pose selection is unaffected.
    "cross_leg_chair_recline": {
        "pose": (
            "seated gracefully in one upholstered armchair with the back "
            "supported by the backrest, torso upright and facing mostly "
            "toward the camera, head facing forward with a gentle relaxed "
            "expression, both forearms resting naturally on the lap and "
            "both hands resting together near the center of the lap, legs "
            "positioned neatly together and angled slightly toward the "
            "left of the image"
        ),
        "pallu": (
            "the loose end of the saree drapes naturally from the shoulder "
            "on the right of the image, passes diagonally across the front "
            "of the lap, then opens into a broad, continuous fan-shaped "
            "spread across the floor toward the lower-right corner of the "
            "image. The full length and outer edge of the spread fabric "
            "remain visible, with the trailing end lying flat on the floor "
            "and not disappearing behind the chair"
        ),
        "prop": PROP_CHAIR,
        "one_person": True,
    },
    "hands_on_hips_side_look": {
        "pose": (
            "standing upright with the body facing the camera and the head "
            "turned in profile toward the left of the image, the eyes "
            "looking in the same direction, both hands placed on the hips "
            "over the saree wrap with the elbows pointing outward, the legs "
            "straight with the feet slightly apart"
        ),
        "pallu": (
            "the pallu rests on the shoulder on the right of the image and "
            "hangs down that same side in soft, continuous pleats{fall}; "
            "the left side of the image shows only the blouse sleeve, arm "
            "and saree wrap"
        ),
    },
    "low_hand_clasp_front": {
        "pose": (
            "standing straight facing the camera with the head upright and "
            "the eyes looking straight into the camera with a soft, gentle "
            "smile, both elbows slightly bent with the hands clasped low in "
            "front of the waist, the hand on the left of the image loosely "
            "cupping the fingers of the other hand, the legs nearly "
            "straight with the feet slightly apart"
        ),
        "pallu": (
            "the pallu rests on the shoulder on the right of the image and "
            "hangs down that same side in soft, continuous pleats{fall}; "
            "the left side of the image shows only the blouse sleeve, arm "
            "and saree wrap"
        ),
    },
    "pallu_on_head": {
        "pose": (
            "standing upright and straight, facing the camera directly, "
            "head upright with the eyes looking forward and a soft smile, "
            "both elbows gently bent and both hands softly clasped together "
            "low in front of the waist, the hand on the left of the image "
            "resting loosely over the fingers of the other hand"
        ),
        "pallu": (
            "one single continuous pallu rises from behind the shoulder on "
            "the left of the image, passes over the top of the head and hair, "
            "frames the face, then descends only over the shoulder on the left "
            "of the image and hangs beside that arm{fall}; "
            "the right side of the image shows the blouse sleeve, arm and saree "
            "wrap only; both hands remain softly clasped low in front of the "
            "waist and do not hold the pallu; the pallu is opaque and remains "
            "one continuous piece, not a two-sided veil or a separate dupatta"
        ),
    },
    "pocket_walk": {
        "pose": (
            "walking toward the camera in a relaxed mid-stride with the "
            "body facing forward and the head upright, the eyes looking "
            "into the camera with a soft smile, both arms hanging relaxed "
            "at the sides with the hands slightly open, one foot stepping "
            "forward ahead of the other with the saree hem swaying gently"
        ),
        "pallu": (
            "the pallu rests on the shoulder on the right of the image and "
            "hangs down that same side in soft, continuous pleats{fall}; "
            "the left side of the image shows only the blouse sleeve, arm "
            "and saree wrap"
        ),
    },
    "rail_wide_arm_side_look": {
        "pose": (
            "standing with the torso at a slight three-quarter angle to the "
            "camera and the head turned toward the left of the image, eyes "
            "looking left; the left arm extends down and outward, with its "
            "single palm resting flat on the top of a low ledge at hip height; "
            "the right arm hangs naturally beside the body with its hand "
            "visible near the thigh; one leg straight and the other slightly bent"
        ),
        "pallu": (
            "the pallu rests on the shoulder on the right of the image and "
            "hangs down that same side in soft, continuous pleats{fall}; "
            "the left side of the image shows only the blouse sleeve, arm "
            "and saree wrap"
        ),
        "prop": PROP_LEDGE,
    },
    "sleeve_adjust_stand": {
        "pose": (
            "standing in a three-quarter stance with the body turned "
            "slightly toward the left of the image and the head turned with "
            "the eyes looking toward the left of the image, the arm on the "
            "left of the image bent across the body with its hand lightly "
            "holding the upper arm on the right of the image near the "
            "blouse sleeve as if adjusting it, the arm on the right of the "
            "image hanging down with the hand relaxed beside the thigh, the "
            "legs nearly straight with the feet slightly apart"
        ),
        "pallu": (
            "the pallu rests on the shoulder on the right of the image and "
            "hangs down that same side in soft, continuous pleats{fall}; "
            "the left side of the image shows only the blouse sleeve, arm "
            "and saree wrap"
        ),
    },
    "three_quarter_hand_adjust": {
        "pose": (
            "standing in a clear three-quarter front stance, torso turned "
            "slightly toward the left of the image, head tilted slightly down "
            "to look at the raised hand; the left arm is bent with its hand "
            "held in front of the upper chest, fingers relaxed; the right arm "
            "is bent across the abdomen and the right hand gently holds the "
            "left wrist; both hands are clearly separate and visible, legs "
            "straight with feet slightly apart and the left foot slightly forward"
        ),
        "pallu": (
            "the pallu rests on the shoulder on the right of the image and "
            "hangs down that same side in soft, continuous pleats{fall}; "
            "the left side of the image shows only the blouse sleeve, arm "
            "and saree wrap"
        ),
    },
}

# Pose used when no pose is requested, by camera_view (None = not sent).
# Written for a saree: the generic texts in camera_data.py talk about
# "pant legs", which is wrong here.
DEFAULT_POSES = {
    None: "standing straight in a natural, relaxed pose facing the camera directly",
    "front": "standing straight in a natural, relaxed pose facing the camera directly",
    "side": (
        "standing upright in a clear side profile, torso and hips turned "
        "approximately 80 to 90 degrees away from the camera, head facing "
        "the same direction as the body, arms relaxed naturally, both feet "
        "visible below the saree hem"
    ),
    "close_up": "standing in a natural, relaxed pose facing the camera",
}

def get_pose_parts(pose, camera_view=None):
    """Resolve body pose and its pallu text for one request."""
    fall = FALL_CLOSE if camera_view == "close_up" else FALL_FULL

    if pose and pose in SAREE_POSES:
        entry = SAREE_POSES[pose]
        pose_text = entry["pose"]
        pallu_value = entry["pallu"]
        # Each known pose owns literal pallu placement text.
        pallu_text = pallu_value.format(fall=fall)
        prop = entry.get("prop", "")
        one_person = entry.get("one_person", False)
    elif pose:
        logger.error(
            "Unknown saree pose '%s'; using generic pose text. Check POSE_OPTIONS "
            "and add an explicit SAREE_POSES entry.", pose,
        )
        pose_text = POSE_INSTRUCTIONS.get(pose, DEFAULT_POSES[None])
        pallu_text = DEFAULT_PALLU_STYLE.format(fall=fall)
        prop = ""
        one_person = False
    else:
        pose_text = DEFAULT_POSES.get(camera_view, DEFAULT_POSES[None])
        pallu_text = DEFAULT_PALLU_STYLE.format(fall=fall)
        prop = ""
        one_person = False

    return {
        "pose_text": pose_text,
        "pallu_text": pallu_text,
        "prop": prop,
        "one_person": one_person,
    }
