"""Common non-saree pose prompts for this garment package.

This file is intentionally self-contained so pose_data.py can be removed
after all callers are switched to this garment-level pose API.
"""

GARMENT_TYPE = __package__.rsplit(".", maxsplit=1)[-1]


# Shared pose wording copied from the current pose_data.py.
POSE_PROMPTS = {
    "back_turn_hair_touch": (
        "standing with the back toward the camera, body turned slightly toward the model's right,"
        " head turned over the right shoulder so that the face is visible,"
        " exactly two arms and two hands,"
        " the left arm raised with the elbow bent and the left hand gently touching the hair at the back of the head,"
        " the right arm hanging naturally down with the right hand near the hip,"
        " one leg straight while the other leg crosses slightly behind it with the foot resting lightly on the toe"
    ),
    "cross_leg_chair_recline": (
        "seated upright in a low upholstered armchair with a straight, composed posture,"
        " the body angled slightly toward the viewer's left and the back resting lightly against the chair,"
        " head upright with the eyes looking slightly away toward the viewer's left,"
        " both forearms resting naturally over the lap with the hands loosely overlapped on the upper thigh,"
        " legs crossed neatly at the knee with the top foot pointing toward the viewer's left,"
        " with the whole chair and both full legs and feet visible"
    ),
    "hands_on_hips_side_look": (
        "standing upright with the body facing the camera and the head turned in profile toward the viewer's left,"
        " both hands placed on the hips with the elbows pointing outward"
        " and the fingers resting at the front of the hips,"
        " legs straight with the feet slightly apart"
    ),
    "low_hand_clasp_front": (
        "standing facing the camera with the head upright and directed forward,"
        " both elbows slightly bent with the right hand loosely cupping the left fingers"
        " and the left hand resting over the right low in front of the pelvis,"
        " legs nearly straight and feet slightly apart with the left foot a little forward"
    ),
    "pallu_on_head": (
        "standing upright facing the camera directly, head upright and looking forward,"
        " a light stole or dupatta drawn over the top of the head and hair as a formal head drape,"
        " exactly two arms and two hands in total,"
        " the hands softly clasped together in front of the lower waist"
    ),
    "pocket_walk": (
        "walking toward the camera in a relaxed mid-stride with the body facing forward"
        " and the head upright looking straight ahead,"
        " the left arm bent with its hand tucked into the side trouser pocket"
        " (or lightly at the hip if the outfit has no pocket),"
        " the right arm hanging down at the side with the hand relaxed and slightly open,"
        " and one leg stepping forward ahead of the other"
    ),
    "rail_wide_arm_side_look": (
        "standing upright facing the camera directly with the body squared to the viewer,"
        " head turned to look in profile toward the viewer's left,"
        " both arms extended down and out to the sides with hands resting flat on the top edge"
        " of a low wall or ledge at hip height,"
        " one leg straight with the other slightly bent and one foot crossed behind the other,"
        " weight settled evenly against the ledge"
    ),
    "sleeve_adjust_stand": (
        "standing in a three-quarter stance with the body turned slightly toward the viewer's left"
        " and the head turned to look toward the viewer's left,"
        " the right arm bent horizontally across the stomach with its fingers holding the left sleeve near the wrist,"
        " the left arm hanging down and slightly forward with the hand relaxed near the thigh,"
        " legs nearly straight with the feet slightly apart, the sleeve staying fully down"
    ),
    "three_quarter_hand_adjust": (
        "standing nearly front-facing with the torso turned slightly toward the model's right,"
        " head tilted down and turned slightly toward the raised right hand,"
        " right elbow bent with the forearm raised in front of the upper body and fingers loosely curled,"
        " left elbow bent with the left forearm crossing the abdomen and the left hand gently holding the right wrist,"
        " legs naturally separated, with the right leg nearly straight and the left leg slightly relaxed,"
        " both feet flat on the ground, with the left foot slightly forward"
    ),
    "back_showing_pallu": (
        "Follow the supplied pose reference image closely."
        "Preserve the same body orientation, posture, arm and hand placement, saree draping, pallu direction, and overall silhouette."
        "Apply the input fabric to the saree while maintaining the reference pose and keeping the complete garment visible."
    ),
    "seated_floor_spread": (
        "Follow the supplied pose reference image closely."
        "Preserve the same body orientation, posture, arm and hand placement, saree draping, pallu direction, and overall silhouette."
        "Apply the input fabric to the saree while maintaining the reference pose and keeping the complete garment visible."
    ),
    "royal_standing_front": (
        "Follow the supplied pose reference image closely."
        "Preserve the same body orientation, posture, arm and hand placement, saree draping, pallu direction, and overall silhouette."
        "Apply the input fabric to the saree while maintaining the reference pose and keeping the complete garment visible."
    ),
}


# Existing garment-specific wording from pose_data.py.
# The keys are (garment_type, style_or_detail, pose_name).
POSE_OVERRIDES = {}


# Existing legacy rule from pose_data.py.
POSES_HIDING_FACE = {"back_turn_hair_touch"}


POSE_OPTIONS = tuple(POSE_PROMPTS)

POSE_SUFFIXES = {
    "three_quarter_hand_adjust": (
        " POSE HAND LOCK: The right elbow is bent and the right hand is "
        "held at upper-chest height. The left elbow is bent across the "
        "abdomen, and the left hand visibly holds the right wrist. Both "
        "hands must meet at the right wrist; do not leave the right hand "
        "raised alone or replace this with clasped hands."
    ),
}

# These poses are only meaningful when the complete action fits in frame.
# In particular, the chair-recline prompt explicitly requires the chair,
# legs and feet; a close-up crop makes that request impossible.
POSES_REQUIRING_FULL_BODY = {
    "cross_leg_chair_recline",
    "pocket_walk",
    "rail_wide_arm_side_look",
}

POSE_CAMERA_VARIANTS = {
    ("low_hand_clasp_front", "close_up"): (
        "standing facing the camera with the head upright and directed "
        "forward, both elbows slightly bent, with both hands clearly visible "
        "together at the lower abdomen just above the waistband: the right "
        "hand loosely cups the left fingers and the left hand rests over the "
        "right; keep both forearms and the clasped hands inside the crop"
    ),
}


def requires_full_body_framing(pose):
    """Whether the selected shirt pose cannot be represented in a close-up."""
    return pose in POSES_REQUIRING_FULL_BODY


def get_camera_pose_prompt(pose, camera_view):
    """Return wording adapted to a camera crop when the pose has a variant."""
    return POSE_CAMERA_VARIANTS.get((pose, camera_view))


def get_pose_prompt(pose, garment_style=None, detail_keys=None):
    """Return this garment's current pose wording, including its overrides."""
    if not pose:
        return None

    # Preserve the legacy lookup order:
    # style -> selected garment details -> None -> generic pose wording.
    variants = [garment_style, *(detail_keys or []), None]

    for variant in variants:
        override = POSE_OVERRIDES.get((GARMENT_TYPE, variant, pose))
        if override is not None:
            sentence = override
            break
    else:
        sentence = POSE_PROMPTS.get(pose)

    if not sentence:
        return None
    if pose == "sleeve_adjust_stand" and "folded_sleeves" in (detail_keys or []):
        sentence = sentence.replace(", the sleeve staying fully down", "")
    suffix = POSE_SUFFIXES.get(pose)
    return f"{sentence}{suffix}" if suffix else sentence


def get_pose_metadata(pose):
    """Return metadata used by the serializer for a known pose."""
    if pose not in POSE_PROMPTS:
        return None

    return {
        "hides_face": pose in POSES_HIDING_FACE,
        "requires_full_body": pose in POSES_REQUIRING_FULL_BODY,
    }


# Public registry data: each pose entry contains its prompt and metadata.
POSES = {
    pose_name: {
        "prompt": get_pose_prompt(pose_name),
        **get_pose_metadata(pose_name),
    }
    for pose_name in POSE_OPTIONS
}
