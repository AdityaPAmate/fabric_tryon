"""
Stage: Pose data (data only, no logic).

Every pose is ONE short sentence written so that it reads correctly
after "the person is ..." (person_photo path) and inside a longer
sentence (own-model paths).

To add a new pose: add one entry to POSE_INSTRUCTIONS. Nothing else
needs to change.

POSE_PHRASE_REPLACEMENTS: the tested prompts in prompts.py say things
like "keep the body pose unchanged". When a pose is requested, those
exact phrases are replaced (only in the in-memory copy of the prompt,
prompts.py itself is never edited). When NO pose is requested, no
replacement happens and the tested prompts are used exactly as before.
"""

# Used by the own-model paths when no pose is requested. This is the
# exact wording that was already in prompt_builder.py.
DEFAULT_OWN_MODEL_POSE = "standing in a natural, relaxed pose facing the camera"

POSE_INSTRUCTIONS = {
    "three_quarter_hand_adjust": (
        "standing nearly front-facing with the torso turned slightly toward the model's right,"
        " head tilted down and turned slightly toward the raised right hand,"
        " right elbow bent with the forearm raised in front of the upper body and fingers loosely curled,"
        " left elbow bent with the left forearm crossing the abdomen and the left hand gently holding the right wrist,"
        " legs naturally separated, with the right leg nearly straight and the left leg slightly relaxed,"
        " both feet flat on the ground, with the left foot slightly forward"
    ),
    "low_hand_clasp_front": (
        "standing facing the camera with the head upright and directed forward,"
        " both elbows slightly bent with the right hand loosely cupping the left fingers"
        " and the left hand resting over the right low in front of the pelvis,"
        " legs nearly straight and feet slightly apart with the left foot a little forward"
    ),
    "rail_wide_arm_side_look": (
        "standing upright facing the camera directly with the body squared to the viewer,"
        " head turned to look in profile toward the left,"
        " both arms extended down and out to the sides with hands resting flat on the top edge"
        " of a low wall or ledge at hip height,"
        " one leg straight with the other slightly bent and one foot crossed behind the other,"
        " weight settled evenly against the ledge"
    ),
    "back_turn_hair_touch": (
        "standing with the back toward the camera, body turned slightly toward the model's right,"
        " head turned over the right shoulder with the front view of the face is visible,"
        " exactly two arms and two hands,"
        " the left arm raised with the elbow bent and the left hand gently touching the hair from  backside of the head,"
        " the right arm hanging naturally down with the rights hand near the hip,"
        " one leg straight while the other leg crosses slightly behind it with the foot resting lightly on the toe"
),
    "pocket_walk": (
        "walking toward the camera in a relaxed mid-stride with the body facing forward"
        " and the head upright looking straight ahead,"
        " the left arm bent with its hand tucked into the side trouser pocket"
        " (or lightly at the hip if the outfit has no pocket),"
        " the right arm hanging down at the side with the hand relaxed and slightly open,"
        " and one leg stepping forward ahead of the other"
    ),
    "hands_on_hips_side_look": (
        "standing upright with the body facing the camera and the head turned in profile toward the viewer's left,"
        " both hands placed on the hips with the elbows pointing outward"
        " and the fingers resting at the front of the hips,"
        " legs straight with the feet slightly apart"
    ),
    "sleeve_adjust_stand": (
        "standing in a three-quarter stance with the body turned slightly toward the viewer's left"
        " and the head turned to look toward the viewer's left,"
        " the right arm bent horizontally across the stomach with its fingers holding the cuff of the left sleeve near the elbow,"
        " the left arm hanging down and slightly forward with the hand relaxed near the thigh,"
        " legs nearly straight with the feet slightly apart, the sleeve staying fully down"
    ),
    "cross_leg_chair_recline": (
        "seated in a low upholstered armchair in a relaxed recline with the back against the chair"
        " and the body angled slightly toward the viewer's left, head upright and turned slightly toward the viewer's left,"
        " both forearms resting forward over the lap with the hands loosely overlapped on the upper thigh,"
        " legs crossed at the knee with the top foot pointing out toward the viewer's left,"
        " with the whole chair and both full legs and feet visible"
    ),
}

POSE_OPTIONS = list(POSE_INSTRUCTIONS.keys())

# Poses where the face is not visible: not allowed together with
# face_choice (checked in serializers.py).
POSES_HIDING_FACE = ["back_turn_hair_touch"]


# Garment-specific pose wording.
# Key: (garment_type, variant, pose_name). variant = garment_style, or a
# garment_details key (e.g. "with_dupatta"), or None for "any style".
# Lookup order: style -> each selected detail -> None -> generic POSE_INSTRUCTIONS.
POSE_OVERRIDES = {
    # ("saree", None, "low_hand_clasp_front"): "standing facing the camera ... pallu ...",
    # ("kurti_pant", "with_dupatta", "low_hand_clasp_front"): "...",
    # ("kurta", "sherwani", "pocket_walk"): "...",
}

# Catches a typo in a pose name as soon as Django starts.
for _garment, _variant, _pose_name in POSE_OVERRIDES:
    if _pose_name not in POSE_INSTRUCTIONS:
        raise ValueError(f"POSE_OVERRIDES has unknown pose '{_pose_name}'")


# (old phrase in the tested prompts, replacement used only when a pose
# is requested). Each old phrase is copied exactly from prompts.py.
POSE_PHRASE_REPLACEMENTS = [
    # kurta, kurti_pant, shirt, blazer prompts + GARMENT_IMAGE_PROMPT
    ("hands, arms, background, and body pose from image 0 completely unchanged",
     "and background from image 0 completely unchanged"),
    # pant prompt
    ("hands, arms, body pose, and the entire background",
     "and the entire background"),
    # closing line of kurta / kurti_pant / shirt / blazer prompts
    ("the same pose and background",
     "the requested new pose and the same background"),
    # closing line of the pant prompt
    ("the exact same pose, shirt, and background",
     "the requested new pose, the same shirt, and the same background"),
    # pant prompt
    ("footwear, face, pose, or background",
     "footwear, face, or background"),
    ("not the face, not the pose, not the background",
     "not the face, not the background"),
    # saree prompt
    ("hairstyle, pose, and background",
     "hairstyle, and background"),
    # kurti_pant prompt
    ("given the person's current arm position in image 0",
     "given the person's arm position in the new pose"),
    # GARMENT_IMAGE_PROMPT
    ("body and pose in image 0",
     "body and the new pose"),
]

# Used only by check_pose_prompts.py: after a pose is applied, none of
# these leftover fragments may remain in a tested prompt.
POSE_LEFTOVER_FRAGMENTS = [
    "body pose",
    "same pose",
    "hairstyle, pose",
    "not the pose",
    "face, pose, or background",
    "pose in image 0",
    "arm position in image 0",
]


def get_pose_sentence(pose, garment_type=None, garment_style=None, detail_keys=None):
    """Garment-specific pose sentence first, then the generic one."""
    if not pose:
        return None
    for variant in [garment_style] + list(detail_keys or []) + [None]:
        key = (garment_type, variant, pose)
        if key in POSE_OVERRIDES:
            return POSE_OVERRIDES[key]
    return POSE_INSTRUCTIONS.get(pose)



