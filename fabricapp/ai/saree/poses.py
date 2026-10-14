"""
Saree route: POSE and PALLU data (data only, no prompt logic).

THIS IS THE ONLY FILE YOU EDIT TO CONTROL A SAREE POSE OR PALLU.

Two separate things:
    SAREE_POSES   pose name -> body pose text + which pallu style it uses
    PALLU_STYLES  pallu style name -> the pallu placement text

To change where the pallu goes for ONE pose: change its "pallu" value to
another style name.
To change how a pallu style looks for EVERY pose that uses it: edit the
text in PALLU_STYLES.

Writing rules (FLUX.2 Klein follows these better):
    1. ONE direction language only: positions IN THE IMAGE
       ("the arm on the left of the image"), never "model's left".
    2. Positive wording: say what IS visible on a side, not what must
       not be there.
    3. Do NOT write "exactly two arms and two hands" in a pose text:
       the LIMBS line in the prompt says it once.
    4. Do not write pleats-to-the-ankle or blouse words here: they belong
       to the garment text (texts.py).
    {fall} in a pallu text is filled by Python: " to the knee" on a
    full-body shot, empty on a close-up (the knee is out of frame).

POSE NAMES must exist in pose_data.POSE_OPTIONS (the serializer uses that
list). A name that is not in SAREE_POSES falls back to the generic pose
text and a warning is logged.
"""

import logging

from ..pose_data import POSE_INSTRUCTIONS

logger = logging.getLogger("fabricapp")

FALL_FULL = " to the knee"
FALL_CLOSE = ""

# Used when a pose does not name a pallu style.
DEFAULT_PALLU_STYLE = "nivi_shoulder"

PALLU_STYLES = {
    # Pallu over the shoulder on the RIGHT of the image (the wearer's left
    # shoulder when she faces the camera): the normal Nivi drape.
    "nivi_shoulder": (
        "the pallu, the loose end of the saree, rests on the shoulder on "
        "the right of the image and hangs down that side of the body in "
        "soft, even pleats{fall}. The left of the image shows only the "
        "blouse sleeve, the arm and the saree wrap."
    ),
    # Gujarati seedha pallu: the pallu comes from the back, over the
    # shoulder on the LEFT of the image, to the front.
    "seedha_front": (
        "the saree is draped in the Gujarati seedha pallu style: the "
        "pallu comes from behind the back over the shoulder on the left "
        "of the image and falls to the front, hanging down that side of "
        "the body in soft pleats{fall}. The right of the image shows only "
        "the blouse sleeve, the arm and the saree wrap."
    ),
    # Pallu drawn over the head like a soft veil (tested wording).
    "veil_head": (
        "the saree is draped in the Gujarati seedha pallu style: the loose "
        "end of the saree comes from behind the back, rises over the top "
        "of the head and hair like a soft hood framing the face, then "
        "falls over the shoulder on the left of the image and hangs down "
        "that side of the body over the outside of the bent arm, ending at "
        "mid-thigh, with the hand of the bent arm gently touching the "
        "pallu at waist height. The right of the image shows only the "
        "straight arm, the blouse sleeve and the saree wrap."
    ),
    # Seated: the pallu rests across the lap.
    "lap_drape": (
        "the pallu rests on the shoulder on the right of the image and its "
        "soft pleats fall across the lap and over the knees, with the "
        "saree pleats falling over the crossed legs to the ankles."
    ),
    # Seen from behind.
    "back_fall": (
        "seen from behind, the pallu falls from the shoulder on the left "
        "of the image down the back in soft pleats{fall}, and the saree is "
        "wrapped neatly around the hips and falls to the ankles."
    ),
}

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
            "standing with her back to the camera, the body turned slightly "
            "toward the right of the image, the head turned over the "
            "shoulder on the right of the image so that her face is seen in "
            "a soft three-quarter profile with the eyes looking toward the "
            "right of the image, the arm on the left of the image raised "
            "with the elbow bent and the hand gently touching the hair at "
            "the back of the head, the arm on the right of the image "
            "hanging down with the hand resting near the hip, one leg "
            "straight and the other crossed slightly behind it, resting "
            "lightly on the toe"
        ),
        "pallu": "back_fall",
    },
    "cross_leg_chair_recline": {
        "pose": (
            "seated in one low upholstered armchair in a relaxed, upright "
            "recline with the back against the chair and the body angled "
            "slightly toward the left of the image, the head turned "
            "slightly toward the left of the image with the eyes looking in "
            "the same direction and a soft smile, both forearms resting "
            "over the lap with the hands loosely overlapped, the legs "
            "crossed at the knee with the top foot pointing out toward the "
            "left of the image, the whole chair and both full legs and feet "
            "visible"
        ),
        "pallu": "lap_drape",
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
        "pallu": "nivi_shoulder",
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
        "pallu": "nivi_shoulder",
    },
    "pallu_on_head": {
        "pose": (
            "standing upright and straight, facing the camera directly, "
            "head upright with the eyes looking forward and a soft smile, "
            "the arm on the right of the image hanging straight down with "
            "the elbow straight and the hand relaxed beside the thigh, the "
            "arm on the left of the image gently bent at the elbow with the "
            "hand held lightly at waist height"
        ),
        "pallu": "veil_head",
    },
    "pocket_walk": {
        "pose": (
            "walking toward the camera in a relaxed mid-stride with the "
            "body facing forward and the head upright, the eyes looking "
            "into the camera with a soft smile, both arms hanging relaxed "
            "at the sides with the hands slightly open, one foot stepping "
            "forward ahead of the other with the saree hem swaying gently"
        ),
        "pallu": "nivi_shoulder",
    },
    "rail_wide_arm_side_look": {
        "pose": (
            "standing upright with the body facing the camera at a slight "
            "angle and the head turned in profile to look toward the left "
            "of the image, the eyes looking in the same direction, the arm "
            "on the left of the image extended down and out to the side "
            "with the palm resting flat on the top edge of a low wall or "
            "ledge at hip height, the arm on the right of the image hanging "
            "naturally beside the body with the hand relaxed, one leg "
            "straight and the other slightly bent"
        ),
        "pallu": "nivi_shoulder",
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
        "pallu": "nivi_shoulder",
    },
    "three_quarter_hand_adjust": {
        "pose": (
            "standing nearly front-facing with the torso turned slightly "
            "toward the left of the image, the head tilted down with the "
            "eyes looking at the raised hand, the arm on the left of the "
            "image bent with the forearm raised in front of the chest and "
            "the fingers loosely curled, the arm on the right of the image "
            "bent with the forearm crossing the abdomen and its hand gently "
            "holding the wrist of the raised arm, the legs nearly straight "
            "with the feet slightly apart and the foot on the left of the "
            "image slightly forward"
        ),
        "pallu": "nivi_shoulder",
    },
}

# Pose used when no pose is requested, by camera_view (None = not sent).
# Written for a saree: the generic texts in camera_data.py talk about
# "pant legs", which is wrong here.
DEFAULT_POSES = {
    None: "standing straight in a natural, relaxed pose facing the camera directly",
    "front": "standing straight in a natural, relaxed pose facing the camera directly",
    "side": (
        "standing in a natural, relaxed pose with the body turned to a "
        "clear side or three-quarter side view, both feet visible below "
        "the saree hem"
    ),
    "close_up": "standing in a natural, relaxed pose facing the camera",
}

# Catches a typo in a pose or pallu-style name as soon as Django starts.
for _pose_name, _entry in SAREE_POSES.items():
    if _entry["pallu"] not in PALLU_STYLES:
        raise ValueError(
            f"SAREE_POSES['{_pose_name}'] uses unknown pallu style "
            f"'{_entry['pallu']}'"
        )


def get_pose_parts(pose, camera_view=None):
    """
    Returns a dict with the resolved pose parts:
        pose_text   -> reads after "the person is ..."
        pallu_text  -> ALWAYS filled (every pose owns its pallu)
        prop        -> sentence for the background line, or ""
        one_person  -> True for seated poses
    """
    fall = FALL_CLOSE if camera_view == "close_up" else FALL_FULL

    if pose and pose in SAREE_POSES:
        entry = SAREE_POSES[pose]
        pose_text = entry["pose"]
        style = entry["pallu"]
        prop = entry.get("prop", "")
        one_person = entry.get("one_person", False)
    elif pose:
        logger.warning(
            "Saree pose '%s' has no entry in saree/poses.py; generic text used",
            pose,
        )
        pose_text = POSE_INSTRUCTIONS.get(pose, DEFAULT_POSES[None])
        style = DEFAULT_PALLU_STYLE
        prop = ""
        one_person = False
    else:
        pose_text = DEFAULT_POSES.get(camera_view, DEFAULT_POSES[None])
        style = DEFAULT_PALLU_STYLE
        prop = ""
        one_person = False

    return {
        "pose_text": pose_text,
        "pallu_text": PALLU_STYLES[style].format(fall=fall),
        "prop": prop,
        "one_person": one_person,
    }