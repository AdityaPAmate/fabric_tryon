"""
Stage: Pose data (data only, no logic).

Every pose is ONE short sentence written so that it reads correctly
after "the person is ..." (person_photo path) and inside a longer
sentence (own-model paths).

To add a new pose: add one entry to POSE_INSTRUCTIONS. Nothing else
needs to change.

POSE_OVERRIDES gives a garment its own wording for a pose. The SAREE has
its own wording for all 9 poses, because:
    - the pallu must be placed explicitly (the pose decides where it hangs),
    - a hand that holds or lifts the pallu in the ORIGINAL photo is the
      main cause of "three hands" (the old arm stays, two new arms are
      drawn), so every saree sentence says "exactly two arms and two hands
      in total" and says where the pallu rests,
    - generic words like "trouser pocket" or "cuff of the sleeve" do not
      fit a saree.

KURTA (NEW, 2026-10-10 reports): one kurta override (cross_leg_chair_recline:
"two bodies for two legs"). A kurta override applies to every kurta style,
on every path. The "three hands" report is solved by the LIMBS rule in
prompt_builder.py, not by a pose text, so the pose sentences stay as tested.

SAREE_POSE_PARTS (NEW) is used ONLY by the saree resolver path
(prompt_builder._build_saree_resolved: generated_person / face_photo).
There the pose owns the pallu placement, as a separate "pallu" variable,
and the garment text does not repeat it. A saree pose that is not listed
in SAREE_POSE_PARTS keeps using its POSE_OVERRIDES text (the pallu is
inside that text). POSE_OVERRIDES itself is NOT changed, so the old
paths (person_pose etc.) behave exactly as before.

Left / right rule used in the wording:
    "left arm", "right hand", "left foot"  -> the model's OWN left / right
    "toward the viewer's left / right"     -> direction on the screen
(When the model stands with her back to the camera, her own left is also
the viewer's left.)

POSE_PHRASE_REPLACEMENTS: the prompts in prompts.py say things like
"keep the body pose unchanged". When a pose is requested on the old
edit-mode path, those exact phrases are replaced (only in the in-memory
copy of the prompt, prompts.py itself is never edited). When NO pose is
requested, no replacement happens.
"""

# Used by the own-model paths when no pose is requested. This is the
# exact wording that was already in prompt_builder.py.
DEFAULT_OWN_MODEL_POSE = "standing in a natural, relaxed pose facing the camera"

POSE_INSTRUCTIONS = {
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
}

POSE_OPTIONS = list(POSE_INSTRUCTIONS.keys())

# Poses where the face is not visible: not allowed together with
# face_choice (checked in serializers.py).
POSES_HIDING_FACE = ["back_turn_hair_touch"]


# Garment-specific pose wording.
# Key: (garment_type, variant, pose_name). variant = garment_style, or a
# garment_details key (e.g. "with_dupatta"), or None for "any style".
# Lookup order: style -> each selected detail -> None -> generic POSE_INSTRUCTIONS.
#
# SAREE: every sentence also fixes the pallu (shoulder, fall, length) and
# says "exactly two arms and two hands in total". The saree modesty rules
# (modest blouse, covered back, covered waist) are in GARMENT_SPECS["saree"]
# in prompt_builder.py (old path) and in prompt_parts.py (resolver path).
POSE_OVERRIDES = {
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
    ("saree", None, "hands_on_hips_side_look"): (
        "standing upright with the body facing the camera"
        " and the head turned in profile toward the viewer's left, the eyes looking in the same direction,"
        " both hands placed on the hips over the saree wrap with the elbows pointing outward,"
        " exactly two arms and two hands in total,"
        " legs straight with the feet slightly apart,"
        " the saree pallu resting on the left shoulder and hanging down behind the left elbow"
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
    ("saree", None, "pallu_on_head"): (
        "standing straight facing the camera with a soft smile,"
        " the pallu lifted from the left shoulder and drawn forward over the top of the head and hair"
        " as a soft, loose veil, opened wide so that it covers the whole head and frames the face"
        " in gentle folds, with the hair parting just visible at the forehead,"
        " the veil falling from the head over the shoulder on the viewer's left in soft folds,"
        " the main length of the pallu hanging down on the viewer's right side only to the knee, not to the floor,"
        " exactly two arms and two hands in total,"
        " the hands softly clasped together low in front of the waist,"
        " the front pleats falling neatly to the ankles"
    ),
    ("saree", None, "pocket_walk"): (
        "walking toward the camera in a relaxed mid-stride with the body facing forward"
        " and the head upright, the eyes looking into the camera with a soft smile,"
        " the left arm hanging relaxed at the side and the right arm hanging down at the side"
        " with the hand relaxed and slightly open,"
        " exactly two arms and two hands in total,"
        " one foot stepping forward ahead of the other with the saree hem swaying gently,"
        " the saree pallu resting on the left shoulder and falling in soft pleats to the knee or below,"
        " the front pleats falling to the ankles"
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

    # kurti_pant only. Directions (right / left) are kept, because a text
    # without them made the model keep the pose of image 2. The left hand
    # is placed in ONE spot only (holding the right wrist), which avoids
    # the third hand.
    ("kurti_pant", None, "cross_leg_chair_recline"): (
        "seated in one low upholstered armchair in an upright, relaxed recline with the back supported by the chair"
        " and the torso angled slightly toward the viewer's left, head upright and turned slightly toward the viewer's left,"
        " both forearms resting separately across the lap with both relaxed hands together on the upper knee,"
        " one leg crossed over the other at the knee with the top foot pointing toward the viewer's left,"
        " with the complete chair, both legs and both feet visible"
    ),
    ("kurti_pant", None, "sleeve_adjust_stand"): (
        "standing in a three-quarter stance with the body turned slightly toward the viewer's left"
        " and the head turned to look toward the viewer's left,"
        " the right elbow bent with the right forearm diagonally across the torso and the right fingers visibly pinching the left sleeve cuff at the left wrist,"
        " the left arm hanging naturally beside the body with the left hand open beside the left thigh,"
        " both hands separate and visible, legs nearly straight with the feet slightly apart"
    ),
    ("kurti_pant", None, "three_quarter_hand_adjust"): (
        "standing nearly front-facing with the torso turned slightly toward the model's right,"
        " head tilted down with the eyes looking at the hands,"
        " the right elbow bent with the right forearm raised diagonally across the upper torso and the right hand loosely closed at chest height,"
        " the left forearm crossing the lower abdomen with the left hand visibly holding the right wrist from below,"
        " both hands separate and visible below the chin, away from the hair and face,"
        " legs naturally separated, with the right leg nearly straight and the left leg slightly relaxed,"
        " both feet flat on the ground, with the left foot slightly forward"
    ),
    ("kurti_pant", None, "pocket_walk"): (
        "walking toward the camera in a relaxed mid-stride with the body facing forward and the head upright looking straight ahead,"
        " exactly two arms and two hands in total,"
        " the left elbow bent with the left hand resting firmly on the left hip,"
        " the right arm hanging down at the side with the hand relaxed and slightly open,"
        " and the left leg stepping forward ahead of the right leg"
    ),

    # kurta only (NEW, 2026-10-10 report 5; applies to every kurta style).
    # cross_leg_chair_recline: "2 bodies for 2 legs" -> one person, one
    # chair, exactly two legs, and the long garment hem rests over the
    # thighs.
    ("kurta", None, "cross_leg_chair_recline"): (
        "seated on ONE low upholstered armchair, one person only, in an upright, relaxed recline"
        " with the back supported by the chair and the torso angled slightly toward the viewer's left,"
        " head upright and turned slightly toward the viewer's left,"
        " both forearms resting across the lap with both hands together on the upper knee,"
        " exactly two legs in total, one leg crossed over the other at the knee"
        " with the top foot pointing toward the viewer's left,"
        " the hem of the long garment resting over the thighs and knees,"
        " with the complete chair, both legs and both feet visible"
    ),
}

# Catches a typo in a pose name as soon as Django starts.
for _garment, _variant, _pose_name in POSE_OVERRIDES:
    if _pose_name not in POSE_INSTRUCTIONS:
        raise ValueError(f"POSE_OVERRIDES has unknown pose '{_pose_name}'")


# ----------------------------------------------------------------------
# SAREE resolver path (NEW). Used only by prompt_builder._build_saree_resolved.
#
# SAREE_POSE_PARTS[pose] = {"pose": <body pose>, "pallu": <pallu placement>}
#   - "pose"  reads after "the person is ..." (no pallu inside, no pleats:
#             the pleats belong to the garment text in prompt_parts.py)
#   - "pallu" is a full sentence block; it is the ONLY place that says
#             where the pallu is for this pose.
# Poses not listed here keep their POSE_OVERRIDES text (pallu inside it).
#
# PALLU WRITING RULES (FLUX.2 Klein):
#   1. Positive wording only: Klein does not follow "no ..." / "must not ..."
#      well, and every mention of the unwanted place primes cloth there.
#      So the clean side is described by what IS visible there.
#   2. ONE direction language only: the position in the IMAGE
#      ("left side of the image"), never "model's right (viewer's left)".
#   3. Short: describe the one visible result, nothing else.
#   4. Name the drape. The model's default saree has the pallu over the
#      wearer's LEFT shoulder (Nivi). Gujarati "seedha pallu" brings the
#      pallu from the back, over the RIGHT shoulder, to the front, which is
#      the wanted geometry, so the style name is used to replace that default.
# Reference image: the pallu hangs on the LEFT side of the IMAGE
# (= the model's right side), ending at mid-thigh. The arm on the LEFT of the image is gently bent and touches the pallu; the arm on the RIGHT of the image hangs straight.
# ----------------------------------------------------------------------

# Pallu used when no pose is requested (Python picks it; the model is not
# told "if the pose does not describe it").
SAREE_DEFAULT_PALLU = (
    "The pallu falls over the left shoulder in soft pleats to the knee or below."
)

SAREE_POSE_PARTS = {
    "pallu_on_head": {
        "pose": (
            "standing upright and straight, facing the camera directly,"
            " head upright with the eyes looking forward and a soft smile,"
            " exactly two arms and two hands in total,"
            " the arm on the right of the image hanging straight down with the elbow straight"
            " and the hand relaxed beside the thigh,"
            " the arm on the left of the image gently bent at the elbow"
            " with the hand held lightly at waist height"
        ),
        "pallu": (
            "The saree is draped in the Gujarati seedha pallu style: the loose end of the saree"
            " comes from behind the back, rises over the top of the head and hair like a soft hood"
            " framing the face, then falls over the shoulder on the left of the image"
            " and hangs down that side of the body over the outside of the bent arm,"
            " ending at mid-thigh, with the hand of the bent arm gently touching the pallu at waist height."
            " The right side of the frame shows only the straight arm, the blouse sleeve and the saree wrap."
        ),
    },
}

for _pose_name in SAREE_POSE_PARTS:
    if _pose_name not in POSE_INSTRUCTIONS:
        raise ValueError(f"SAREE_POSE_PARTS has unknown pose '{_pose_name}'")


# (old phrase in the prompts, replacement used only when a pose
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
    # kurti_pant prompt
    ("given the person's current arm position in image 0",
     "given the person's arm position in the new pose"),
    # GARMENT_IMAGE_PROMPT
    ("body and pose in image 0",
     "body and the new pose"),
]

# Used only by check_pose_prompts.py: after a pose is applied, none of
# these leftover fragments may remain in a prompt.
POSE_LEFTOVER_FRAGMENTS = [
    "body pose",
    "same pose",
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


def get_saree_pose_parts(pose, default_pose_text):
    """
    Saree resolver path. Returns (pose_text, pallu_text).

    pallu_text is None when the pallu is already described inside
    pose_text (the poses that still use their POSE_OVERRIDES text).

        no pose            -> (default_pose_text, SAREE_DEFAULT_PALLU)
        pose in SAREE_POSE_PARTS -> its own pose + its own pallu
        saree override exists    -> (override text, None)
        anything else            -> (generic pose text, SAREE_DEFAULT_PALLU)
    """
    if not pose:
        return default_pose_text, SAREE_DEFAULT_PALLU

    parts = SAREE_POSE_PARTS.get(pose)
    if parts:
        return parts["pose"], parts["pallu"]

    override = POSE_OVERRIDES.get(("saree", None, pose))
    if override:
        return override, None

    generic = POSE_INSTRUCTIONS.get(pose)
    if generic:
        return generic, SAREE_DEFAULT_PALLU
    return default_pose_text, SAREE_DEFAULT_PALLU