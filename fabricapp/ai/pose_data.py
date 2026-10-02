"""
Stage: Pose data (data only, no logic).

Every pose is ONE short sentence written so that it reads correctly
after "the person is ..." (person_photo path) and inside a longer
sentence (own-model paths).

To add a new pose: add one entry to POSE_INSTRUCTIONS. Nothing else
needs to change.

POSE_OVERRIDES gives a garment its own wording for a pose (for example
the saree, because of the pallu). POSE_ONLY_FOR lists poses that exist
only for some garments (they have NO generic wording and work only
through POSE_OVERRIDES).

Left / right rule used in the wording:
    "left arm", "right hand", "left foot"  -> the model's OWN left / right
    "toward the viewer's left / right"     -> direction on the screen
(When the model stands with her back to the camera, her own left is also
the viewer's left.)

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

# Poses that exist only for some garment types: pose -> allowed garment types.
# They have no generic wording above; each one MUST have an entry in
# POSE_OVERRIDES for every garment type listed here (checked below).
POSE_ONLY_FOR = {
    "seated_look_down": ["saree"],
    "pallu_shawl_wrap": ["saree"],
    "pallu_on_head": ["saree"],
    "back_pallu_on_shoulder": ["saree"],
    "back_showing_pallu": ["saree"],
}

POSE_OPTIONS = list(POSE_INSTRUCTIONS.keys()) + list(POSE_ONLY_FOR.keys())

# Poses where the face is not visible: not allowed together with
# face_choice (checked in serializers.py).
POSES_HIDING_FACE = [
    "back_turn_hair_touch",
    "back_pallu_on_shoulder",
    "back_showing_pallu",
]


# Garment-specific pose wording.
# Key: (garment_type, variant, pose_name). variant = garment_style, or a
# garment_details key (e.g. "with_dupatta"), or None for "any style".
# Lookup order: style -> each selected detail -> None -> generic POSE_INSTRUCTIONS.
#
# SAREE: every sentence also fixes the pallu (shoulder, fall, length) and
# says "exactly two arms and two hands", so that no hand or pallu of the
# original photo's pose is carried over. The saree modesty rules (modest
# blouse, covered back, covered waist) are in GARMENT_SPECS["saree"] in
# prompt_builder.py.
POSE_OVERRIDES = {
    # ---------------- saree: the 8 common poses ----------------
    ("saree", None, "three_quarter_hand_adjust"): (
        "standing nearly front-facing with the torso turned slightly toward the model's right,"
        " the head tilted down with the eyes looking down at the raised right hand,"
        " the right elbow bent with the forearm raised in front of the chest and the fingers loosely curled,"
        " the left elbow bent with the left forearm crossing the abdomen and the left hand gently holding the right wrist,"
        " exactly two arms and two hands in total,"
        " legs nearly straight with the feet slightly apart and the left foot slightly forward,"
        " the saree pallu resting on the left shoulder and hanging straight down behind the left arm"
        " in soft pleats to the knee or below, the front pleats falling neatly to the ankles"
    ),
    ("saree", None, "low_hand_clasp_front"): (
        "standing straight facing the camera with the head upright and the eyes looking straight into the camera"
        " with a soft, gentle smile,"
        " both elbows slightly bent with the hands clasped low in front of the waist,"
        " the right hand loosely cupping the left fingers,"
        " exactly two arms and two hands in total,"
        " legs nearly straight with the feet slightly apart and the left foot a little forward,"
        " the pleated saree pallu resting on the left shoulder and hanging down behind the left arm"
        " to the knee or below, the saree drape crossing the chest diagonally from the left shoulder to the right hip,"
        " the front pleats falling neatly to the ankles"
    ),
    ("saree", None, "rail_wide_arm_side_look"): (
        "standing upright with the body facing the camera at a slight angle"
        " and the head turned in profile to look toward the viewer's left, the eyes looking in the same direction,"
        " the right arm extended down and out to the side with the palm resting flat on the top edge"
        " of a low wall or ledge at hip height,"
        " the left arm hanging naturally down beside the body with the hand relaxed,"
        " exactly two arms and two hands in total,"
        " one leg straight with the other slightly bent,"
        " the saree pallu resting on the left shoulder and hanging down behind the left arm"
        " in soft pleats to the knee or below, the front pleats falling neatly to the ankles"
    ),
    ("saree", None, "back_turn_hair_touch"): (
        "standing with the back toward the camera and the body turned slightly toward the model's right,"
        " the head turned over the right shoulder so that the face is seen in a soft three-quarter profile,"
        " the eyes looking toward the viewer's right,"
        " the left arm raised with the elbow bent and the left hand gently touching the hair at the back of the head,"
        " the right arm hanging down with the right hand resting near the hip,"
        " exactly two arms and two hands in total,"
        " one leg straight with the other crossed slightly behind it, resting lightly on the toe,"
        " the saree seen from behind: the full-length pallu falling from the left shoulder down the back"
        " in soft pleats to the knee or below, the saree wrapped neatly around the hips and falling to the ankles,"
        " the blouse short and modest, fully covering the back with a closed round back neck"
    ),
    ("saree", None, "pocket_walk"): (
        "walking toward the camera in a relaxed mid-stride with the body facing forward"
        " and the head upright, the eyes looking into the camera with a soft smile,"
        " the left arm hanging relaxed with the pallu draped over the forearm and falling down beside the knee,"
        " the right arm hanging down at the side with the hand relaxed and slightly open,"
        " exactly two arms and two hands in total,"
        " one foot stepping forward ahead of the other with the saree hem swaying gently,"
        " the saree pallu coming from the left shoulder in soft pleats, the front pleats falling to the ankles"
    ),
    ("saree", None, "hands_on_hips_side_look"): (
        "standing upright with the body facing the camera"
        " and the head turned in profile toward the viewer's left, the eyes looking in the same direction,"
        " both hands placed on the hips over the saree wrap with the elbows pointing outward,"
        " exactly two arms and two hands in total,"
        " legs straight with the feet slightly apart,"
        " the saree pallu resting on the left shoulder and hanging down behind the left elbow"
        " in soft pleats to the knee or below, the front pleats falling neatly to the ankles"
    ),
    ("saree", None, "sleeve_adjust_stand"): (
        "standing in a three-quarter stance with the body turned slightly toward the viewer's left"
        " and the head turned with the eyes looking toward the viewer's left,"
        " the right arm bent across the body with the right hand lightly holding the left upper arm"
        " near the blouse sleeve as if adjusting it,"
        " the left arm hanging down with the hand relaxed beside the thigh,"
        " exactly two arms and two hands in total,"
        " legs nearly straight with the feet slightly apart,"
        " the saree pallu resting on the left shoulder and hanging down behind the left arm"
        " in soft pleats to the knee or below, the front pleats falling neatly to the ankles"
    ),
    ("saree", None, "cross_leg_chair_recline"): (
        "seated in a low upholstered armchair in a relaxed, upright recline with the back against the chair"
        " and the body angled slightly toward the viewer's left,"
        " the head turned slightly toward the viewer's left with the eyes looking in the same direction"
        " and a soft smile,"
        " both forearms resting over the lap with the hands loosely overlapped,"
        " exactly two arms and two hands in total,"
        " legs crossed at the knee with the top foot pointing out toward the viewer's left,"
        " the saree pleats falling over the crossed legs to the ankles,"
        " the pallu coming from the left shoulder and resting across the lap and over the knees,"
        " with the whole chair and both full legs and feet visible"
    ),

    # ---------------- saree-only poses (from the reference photos) ----------------
    ("saree", None, "seated_look_down"): (
        "seated sideways on a low bench or step in a three-quarter view with the back upright,"
        " the head tilted down with the eyes looking down toward the hands,"
        " both hands gently clasped together on the lap with the right hand resting over the left,"
        " exactly two arms and two hands in total,"
        " the legs together with the knees side by side and the feet hidden under the saree,"
        " the saree pleats falling over the lap to the ground,"
        " the full-length pallu coming down from the left shoulder and hanging in broad soft folds"
        " in front of the body all the way to the floor beside the seat,"
        " with the whole seat visible"
    ),
    ("saree", None, "pallu_shawl_wrap"): (
        "standing gracefully in a three-quarter stance with the body turned slightly toward the viewer's right,"
        " the head turned with the eyes looking softly toward the viewer's left,"
        " both hands held gently together in front of the waist with one hand resting over the other,"
        " exactly two arms and two hands in total,"
        " the broad decorative pallu draped like a shawl across both shoulders,"
        " rising lightly behind the head without covering the face or the hair,"
        " with both ends of the pallu hanging down the front on each side of the body"
        " to the knee or below, framing the body,"
        " the front pleats of the saree falling neatly to the ankles"
    ),
    ("saree", None, "pallu_on_head"): (
        "standing straight facing the camera with the head upright"
        " and the eyes looking into the camera with a gentle, composed smile,"
        " the pallu lifted from the back over the head so that it softly covers the top and back of the hair"
        " while the face stays fully visible,"
        " the pallu then falling over the shoulders with its wide decorative border"
        " hanging down in front of the right shoulder and arm to about the knee,"
        " both hands gently held together in front of the waist with one hand over the other,"
        " exactly two arms and two hands in total,"
        " legs nearly straight with the feet slightly apart,"
        " the saree drape crossing the chest diagonally to the right hip and the front pleats falling neatly to the ankles"
    ),
    ("saree", None, "back_pallu_on_shoulder"): (
        "standing straight with the back toward the camera,"
        " the head turned toward the viewer's right in a soft side profile"
        " with the eyes looking toward the viewer's right and a gentle smile,"
        " both arms bent forward with the hands held together in front of the waist, out of sight from behind,"
        " exactly two arms and two hands in total,"
        " the pleated pallu neatly gathered on the left shoulder and falling from it down the back"
        " in broad soft pleats, sweeping diagonally toward the right side and reaching the hem near the floor,"
        " the blouse short and modest, fully covering the back with a closed round back neck,"
        " the saree falling straight to the ankles with the feet close together"
    ),
    ("saree", None, "back_showing_pallu"): (
        "standing with the back toward the camera and the body turned slightly toward the viewer's right,"
        " the head turned over the right shoulder with the face in profile"
        " and the eyes looking toward the viewer's right,"
        " the left arm extended out to the side and slightly raised,"
        " the left hand lifting the edge of the pallu so that it spreads open across the back,"
        " the right arm bent with the right hand resting at the right hip,"
        " exactly two arms and two hands in total,"
        " the full-length pallu falling from the left shoulder diagonally across the back"
        " and spreading wide so that its whole design is displayed down to the floor,"
        " the blouse short and modest, fully covering the back with a closed round back neck,"
        " legs nearly straight with the feet slightly apart"
    ),
    # ("kurti_pant", "with_dupatta", "low_hand_clasp_front"): "...",
    # ("kurta", "sherwani", "pocket_walk"): "...",
}

# Catches a typo in a pose name as soon as Django starts.
for _garment, _variant, _pose_name in POSE_OVERRIDES:
    if _pose_name not in POSE_OPTIONS:
        raise ValueError(f"POSE_OVERRIDES has unknown pose '{_pose_name}'")

# A garment-only pose must have its wording for every allowed garment.
for _pose_name, _garments in POSE_ONLY_FOR.items():
    for _garment in _garments:
        if (_garment, None, _pose_name) not in POSE_OVERRIDES:
            raise ValueError(f"POSE_ONLY_FOR pose '{_pose_name}' has no POSE_OVERRIDES entry for '{_garment}'")


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