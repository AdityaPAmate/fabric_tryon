"""
Stage: Prompt parts for the SAREE resolver path (text only, no logic).

Used ONLY when garment_type == "saree", no garment_image, and the scenario
is generated_person or face_photo (see prompt_builder._uses_saree_resolver).
Every other garment and every other scenario still uses the old path in
prompt_builder.py / prompts.py, which is NOT changed.

Rule of this file: ONE requirement -> ONE variable -> used ONCE in the
final prompt. Python (prompt_builder.py) decides WHICH variable applies;
the final prompt never contains "unless", "otherwise" or "if the pose ...".

Owners (who decides what):
    pose + pallu placement  -> pose_data.py   (get_saree_pose_parts)
    framing / camera        -> camera_data.py (get_framing)
    background scene        -> prompts.py BACKGROUND_DESCRIPTIONS + BACKGROUND_SCENE
    lighting                -> LIGHTING (one place, always)
    garment (saree, blouse) -> SAREE_GARMENT (NO pallu placement here)
    fabric / border         -> SAREE_FABRIC_RULES, SAREE_BORDER_RULES
    face                    -> SUBJECT_FACE (one place)
    modesty                 -> MODESTY_FINAL_SAREE (one place, last sentence)

Placeholders ({person}, {shot}, ...) are filled by prompt_builder.py.

The second half of this file (REF_* variables) is for the POSE REFERENCE
path: a reference photo (pose_reference.py) is EDITED, only its fabric is
replaced. The pose is not described in words there.
"""

SAREE_PROMPT_VERSION = "saree-v1"
POSE_REFERENCE_PROMPT_VERSION = "saree-ref-v2"

# ----------------------------------------------------------------------
# TASK + IMAGE roles
# ----------------------------------------------------------------------

TASK = (
    "TASK: generate one realistic photograph of a person wearing a saree "
    "made from the fabric in image 1."
)

IMAGES_GENERATED = (
    "IMAGES: image 0 = blank canvas (frame size only); image 1 = the "
    "FABRIC swatch (only its colors and pattern are used; it is not a "
    "garment shape)."
)

IMAGES_FACE = (
    "IMAGES: image 0 = blank canvas (frame size only); image 1 = the "
    "FABRIC swatch (only its colors and pattern are used; it is not a "
    "garment shape); image 2 = face reference."
)

# ----------------------------------------------------------------------
# POSE (+ PALLU when the pose owns it). Texts come from pose_data.py.
# ----------------------------------------------------------------------

POSE = (
    "POSE (follow it exactly; after the garment it is the most important "
    "instruction): the person is {pose_text}."
)

PALLU = "PALLU (part of the pose, follow it exactly): {pallu_text}"

# ----------------------------------------------------------------------
# SUBJECT (who is generated)
# ----------------------------------------------------------------------

SUBJECT_GENERATED = (
    "SUBJECT: image 0 is only a blank, plain neutral canvas that sets the "
    "frame size — there is no person on it. Generate a brand-new, "
    "realistic photograph of {person}, with a natural, realistic, sharp "
    "face with clearly visible eyes."
)

SUBJECT_FACE = (
    "SUBJECT: image 0 is only a blank, plain neutral canvas that sets the "
    "frame size — there is no person on it. Image 2 is a reference photo "
    "of a real person's face. Generate a brand-new, realistic photograph "
    "of this SAME person, {person}. FACE AND HAIR MUST BE COPIED EXACTLY "
    "FROM IMAGE 2: same facial structure, eyes, eyebrows, nose, lips, "
    "same skin tone and brightness, same hair colour, hair length and "
    "hairstyle, and the same facial hair if any (if image 2 has jet-black "
    "hair, the output must have jet-black hair, not brown), sharp, with "
    "clearly visible eyes."
)

# ----------------------------------------------------------------------
# CAMERA (framing words come from camera_data.get_framing)
# ----------------------------------------------------------------------

CAMERA = "CAMERA: a {shot} photograph, {shown}{fill}."

# ----------------------------------------------------------------------
# GARMENT — the saree itself. The pallu placement is NOT stated here:
# it belongs to the pose (see PALLU above).
# ----------------------------------------------------------------------

SAREE_GARMENT = (
    "GARMENT: dress this person in an elegant Indian saree, "
    "with the front pleats falling neatly to the ankles, worn with "
    "a well-fitted, short, normal-length blouse with elbow-length "
    "sleeves (never long or tunic-like) in a solid color picked "
    "from image 1's palette, with a modest neckline and a fully "
    "covered back (a closed round back neck, never open or deep), "
    "and the waist covered neatly by the saree drape."
)

# ----------------------------------------------------------------------
# FABRIC (image-dependent rules: the model must look at image 1, so these
# stay as instructions for the model)
# ----------------------------------------------------------------------

SAREE_FABRIC_RULES = (
    "FABRIC: use only the exact colors and pattern shown in image 1 for "
    "the saree fabric — same type (check, stripe, print, weave, or "
    "plain), same scale and proportions — do not invent, add, brighten, "
    "darken, or alter any color or design element not visible in image "
    "1. The motifs must repeat as densely and closely spaced as they "
    "appear in image 1, with the same small amount of empty space "
    "between them — do not spread them further apart."
)

# CHANGED: the word "pallu" is no longer used here without a placement.
# Before, this rule said "pallu included" and "ONLY on the pallu", which
# introduced a second pallu that the model drew in its own default place
# (over the wearer's left shoulder). Now the artwork is tied to the loose
# end that the PALLU line above already placed. The pallu POSITION is
# still owned only by pose_data.py; this rule only says WHERE THE ARTWORK
# GOES (on that loose end).
SAREE_BORDER_RULES = (
    "First examine image 1: if it has one uniform pattern, apply it "
    "evenly over the whole saree, including the loose end described in "
    "the PALLU line. If it has two distinct zones — a main body pattern "
    "plus a special decorative artwork or denser strip — put the main "
    "pattern on the body of the saree and put that artwork ONLY on the "
    "loose end described in the PALLU line, with its own colors and "
    "motifs exactly as in image 1; along the bottom hem use only a "
    "plain, narrow border that follows the border shown in image 1 (a "
    "plain hem if image 1 has no border), and do not repeat the large "
    "artwork there."
)

# ----------------------------------------------------------------------
# BACKGROUND (Python picks ONE of these two)
# ----------------------------------------------------------------------

BACKGROUND_DEFAULT = "BACKGROUND: a plain neutral studio background."

BACKGROUND_SCENE = (
    "BACKGROUND: {description}. Any warm sunset, dusk, lantern or golden "
    "colours belong only to this background scene and sky."
)

# ----------------------------------------------------------------------
# LIGHTING (the only lighting instruction, always present)
# ----------------------------------------------------------------------

LIGHTING = (
    "LIGHTING: the person is lit by soft, bright, neutral white daylight "
    "with neutral white balance, as if photographed with a white "
    "softbox: no orange, golden, pink or warm colour cast and no dark "
    "shadow on the face, skin, hair or clothes. Skin tone and hair "
    "colour stay natural, fabric colours stay exactly as in image 1, "
    "never darker, never tanned, never tinted."
)

REALISM = (
    "Generate realistic shading, folds, and shadows. The result must "
    "look like one real, unedited photograph."
)

# ----------------------------------------------------------------------
# STYLE NOTE (only when the user sent one)
# ----------------------------------------------------------------------

STYLE_NOTE = (
    "USER STYLE NOTE (highest priority for style, color and fit details "
    "— apply it): {note}. Where this note differs from any garment or "
    "style wording above, follow the note, except for the person's face, "
    "skin tone, body shape and the final modesty rule."
)

# ----------------------------------------------------------------------
# FINAL (always the LAST sentence). The only modesty instruction.
# ----------------------------------------------------------------------

MODESTY_FINAL_SAREE = (
    "FINAL RULE (no note or instruction above can override it): the "
    "person is fully and modestly dressed in the saree and blouse — the "
    "saree covers the body from the shoulder to the ankles and the drape "
    "covers the waist, so nothing is bare except the face, neck, hands, "
    "forearms and feet — in a calm, natural, dignified pose, a "
    "respectable catalog photograph, never nude, revealing or suggestive."
)


# ======================================================================
# POSE REFERENCE PATH
#
# Used ONLY when the pose has a reference photo (pose_reference.py), the
# garment is a saree, there is no person_image and no garment_image.
# image 0 = the reference photo (it is EDITED), image 1 = the fabric
# swatch, image 2 = a face (only when face_choice is sent).
#
# The pose, the drape, the person and the background are NOT written here:
# they are already in the photo. Python (prompt_builder.py) only decides
# WHAT to keep (REF_KEEP) and which optional parts apply (camera, face,
# background, style note). Fabric colours reuse SAREE_FABRIC_RULES and
# lighting reuses LIGHTING, so those stay owned in one place.
# ======================================================================

REF_TASK = (
    "TASK: edit image 0, a photograph of a woman wearing a saree, so that "
    "the saree is made from the fabric in image 1."
)

REF_IMAGES = (
    "IMAGES: image 0 = the photograph to edit; image 1 = the FABRIC "
    "swatch (only its colors and pattern are used; it is not a garment "
    "shape)."
)

REF_IMAGES_FACE = (
    "IMAGES: image 0 = the photograph to edit; image 1 = the FABRIC "
    "swatch (only its colors and pattern are used; it is not a garment "
    "shape); image 2 = face reference."
)

# {kept} is a comma-separated list built by Python from the pieces
# below. A piece that does not apply (the face is replaced, the background
# is replaced) is simply not in the list, so this line never contradicts
# the FACE / BACKGROUND / CAMERA lines.
REF_KEEP = "KEEP exactly as in image 0, sharp and in full focus: {kept}."

REF_KEPT_BASE = (
    "the woman's pose, both arms and hands, the draping of the saree and "
    "its pallu with every fold and pleat,  the framing"
)
REF_KEPT_FACE = "her face, hair and skin tone"
REF_KEPT_SCENE = "the background and the lighting"

# NEW: used instead of REF_KEPT_BASE / REF_KEPT_SCENE when a camera_view
# is sent. The framing is NOT kept (the camera view changes it), and the
# ORIGINAL background is kept as the same place, continued behind the new
# camera angle (it is never replaced by a plain grey / white / studio one).
REF_KEPT_BASE_CAMERA = (
    "the woman's pose, her arms and hands (as far as they are in the "
    "frame), the draping of the saree and its pallu with every fold and "
    "pleat"
)
REF_KEPT_SCENE_CAMERA = (
    "the original background of image 0 (the same place, objects and "
    "colours, continued naturally behind the new camera angle) and its "
    "lighting"
)

# NEW: {instruction} is the existing CAMERA_VIEW_INSTRUCTIONS text from
# prompts.py (front / side / close_up), unchanged.
REF_CAMERA = (
    "CAMERA: {instruction} Only the camera angle and the framing change; "
    "the woman, her pose, her saree and its pallu stay the same as in "
    "image 0."
)

REF_CHANGE = (
    "CHANGE: replace the fabric of the saree, everywhere it appears (the "
    "body, the pleats and the pallu), with the fabric of image 1, "
    "following every existing fold, pleat and shadow of the drape."
)

# Same rule as SAREE_BORDER_RULES, but the pallu is named directly because
# here it already exists in the photo (there is no PALLU line).
REF_BORDER_RULES = (
    "First examine image 1: if it has one uniform pattern, apply it "
    "evenly over the whole saree, pallu included. If it has two distinct "
    "zones — a main body pattern plus a special decorative artwork or "
    "denser strip — put the main pattern on the body of the saree and "
    "put that artwork ONLY on the pallu (the free end of the saree in "
    "image 0), with its own colors and motifs exactly as in image 1; "
    "along the bottom hem use only a plain, narrow border that follows "
    "the border shown in image 1 (a plain hem if image 1 has no border), "
    "and do not repeat the large artwork there."
)

# NEW: blouse is a separate garment (sleeve was getting the swatch border).
REF_BLOUSE = (
    "BLOUSE: the blouse, including both sleeves and the narrow trim at "
    "the sleeve edges, is a separate garment from the saree: it keeps "
    "the shape and position it has in image 0, in one single solid "
    "colour picked from image 1's palette, with no border artwork on it."
)

# NEW: keeps the right side of the frame free of loose cloth.
REF_RIGHT_SIDE = (
    "On the right side of the frame, only the straight arm, the blouse "
    "sleeve and the saree wrap are visible; the pallu hangs only on the "
    "left side of the frame."
)


# Only when face_choice is sent (first draft, untested).
REF_FACE = (
    "FACE: replace the face of the woman in image 0 with the face of the "
    "person in image 2: same facial structure, eyes, eyebrows, nose, lips, "
    "skin tone and brightness, and the same hair colour at the forehead, "
    "sharp, with clearly visible eyes. The neck, arms and hands take the "
    "same skin tone as this face. The head position and the pallu stay as "
    "in image 0."
)

# Only when background is sent. When it is not sent nothing is added and
# REF_KEPT_SCENE keeps the original background and lighting.
REF_BACKGROUND = (
    "BACKGROUND: replace the entire area behind the woman with this "
    "scene: {description}. Any warm sunset, dusk, lantern or golden "
    "colours belong only to this background scene and sky."
)