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
        "seated in a low upholstered armchair in a relaxed recline with the back against the chair"
        " and the body angled slightly toward the viewer's left, head upright and turned slightly toward the viewer's left,"
        " both forearms resting forward over the lap with the hands loosely overlapped on the upper thigh,"
        " legs crossed at the knee with the top foot pointing out toward the viewer's left,"
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
            return override

    return POSE_PROMPTS.get(pose)


def get_pose_metadata(pose):
    """Return metadata used by the serializer for a known pose."""
    if pose not in POSE_PROMPTS:
        return None

    return {
        "hides_face": pose in POSES_HIDING_FACE,
    }


# Public registry data: each pose entry contains its prompt and metadata.
POSES = {
    pose_name: {
        "prompt": get_pose_prompt(pose_name),
        **get_pose_metadata(pose_name),
    }
    for pose_name in POSE_OPTIONS
}