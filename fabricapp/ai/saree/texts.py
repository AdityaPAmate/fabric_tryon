"""
Saree route: ALL prompt wording (text only, no logic).

Rule: ONE requirement -> ONE variable -> used ONCE in the final prompt.
builder.py decides WHICH variable applies; the final prompt never contains
"unless", "otherwise" or "if the pose ...".

Who owns what:
    pose + pallu placement -> poses.py
    framing / camera       -> camera_data.py (+ camera rule in builder.py)
    background scene       -> prompts.BACKGROUND_DESCRIPTIONS + BACKGROUND_SCENE
    lighting               -> LIGHTING_NEUTRAL / LIGHTING_MATCH_PHOTO
    garment (saree+blouse) -> GARMENT_FULL / GARMENT_CLOSE (NO pallu here)
    fabric / border        -> FABRIC_RULES, BORDER_RULES
    modesty                -> MODESTY_FINAL_* (always the LAST sentence)

Placeholders ({person}, {shot}, ...) are filled by builder.py.
"""

PROMPT_VERSION = "saree-v2"
REFERENCE_PROMPT_VERSION = "saree-ref-v3"

# ----------------------------------------------------------------------
# TASK + IMAGE roles
# ----------------------------------------------------------------------

TASK = (
    "TASK: generate one realistic photograph of a person wearing a saree "
    "made from the fabric in image 1."
)

_FABRIC_IMAGE = (
    "image 1 = the FABRIC swatch (only its colors and pattern are used; it "
    "is not a garment shape)"
)

IMAGES_GENERATED = (
    "IMAGES: image 0 = blank canvas (frame size only); " + _FABRIC_IMAGE + "."
)

IMAGES_FACE = (
    "IMAGES: image 0 = blank canvas (frame size only); " + _FABRIC_IMAGE
    + "; image 2 = face reference."
)

IMAGES_PERSON_KEEP_BG = (
    "IMAGES: image 0 = blank canvas (frame size only); " + _FABRIC_IMAGE
    + "; image 2 = photo of the person (take the face, hair, skin tone, "
    "age, body build, accessories and the background; do NOT take the "
    "clothes or the pose)."
)

IMAGES_PERSON_NEW_BG = (
    "IMAGES: image 0 = blank canvas (frame size only); " + _FABRIC_IMAGE
    + "; image 2 = photo of the person (take the face, hair, skin tone, "
    "age, body build and accessories; do NOT take the clothes, the pose or "
    "the background)."
)

# ----------------------------------------------------------------------
# POSE, PALLU, LIMBS (pose first: it is the most important after the garment)
# ----------------------------------------------------------------------

POSE = (
    "POSE (follow it exactly; after the garment it is the most important "
    "instruction): the person is {pose_text}."
)

PALLU = "PALLU (part of the pose, follow it exactly): {pallu_text}"

LIMBS = (
    "LIMBS: exactly two arms, two hands, two legs and two feet in total in "
    "the pose above — never a third hand, an extra arm or a duplicate limb."
)

ONE_PERSON = (
    "ONE PERSON: exactly one person, with one head, one torso and exactly "
    "two legs in total — never two bodies, a mirrored copy or a second "
    "person."
)

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
    "hairstyle (if image 2 has jet-black hair, the output must have "
    "jet-black hair, not brown), sharp, with clearly visible eyes."
)

SUBJECT_PERSON = (
    "SUBJECT: image 0 is only a blank, plain neutral canvas that sets the "
    "frame size — there is no person on it. Image 2 is a photo of a real "
    "person. Generate a brand-new, realistic photograph of this SAME "
    "person: same face, eyes, eyebrows, nose, lips, skin tone, hair colour "
    "and style, age category and apparent gender presentation, and every "
    "accessory (earrings, bangles, necklace, bindi, watch, spectacles) in "
    "the same place. Keep the same body build: the same shoulder, waist "
    "and hip widths, torso length, and arm and leg thickness — do not make "
    "the person slimmer, wider, taller or shorter. Take nothing else from "
    "image 2: not the clothes, not any loose cloth or a hand holding it, "
    "and not the pose. If image 2 shows a child, the output shows the same "
    "child, not an adult."
)

# Body build (image 2 / a face photo never gives the body).
BODY_FACE_NOTE = "Image 2 gives only the face and hair, never the body. "

BODY_PLUS = (
    "BODY BUILD: the body is clearly PLUS-SIZE — a heavy, broad build with "
    "a full rounded belly, wide shoulders, thick arms and thick thighs; "
    "the face may look proportionally fuller. The saree and blouse are cut "
    "larger to fit this body."
)

BODY_TRIM = (
    "BODY BUILD: the body is clearly ATHLETIC and toned — broad shoulders, "
    "defined arms and a flat stomach. The saree and blouse fit this body."
)

BODY_CHILD_PLUS = (
    "BODY BUILD: the child has a noticeably chubby, plus-size build with "
    "fuller cheeks, a rounded belly and thicker arms and legs, while "
    "remaining clearly a child."
)

# ----------------------------------------------------------------------
# GARMENT (the saree). The pallu placement is NOT here: the pose owns it.
# Close-up: the ankles are out of frame, so the pleats sentence is gone.
# ----------------------------------------------------------------------

GARMENT_FULL = (
    "GARMENT: dress this person in an elegant Indian saree, with the front "
    "pleats falling neatly to the ankles, worn with a well-fitted, short, "
    "normal-length blouse with elbow-length sleeves (never long or "
    "tunic-like) in a solid color picked from image 1's palette, with a "
    "modest neckline and a fully covered back (a closed round back neck, "
    "never open or deep), and the waist covered neatly by the saree drape."
)

GARMENT_CLOSE = (
    "GARMENT: dress this person in an elegant Indian saree, worn with a "
    "well-fitted, short, normal-length blouse with elbow-length sleeves "
    "(never long or tunic-like) in a solid color picked from image 1's "
    "palette, with a modest neckline and a fully covered back (a closed "
    "round back neck, never open or deep), and the waist covered neatly by "
    "the saree drape."
)

CHILD_GARMENT_LINE = (
    "The person is a {age}-year-old child, so the saree and blouse are a "
    "child-sized version, fitting a child's small body."
)

# ----------------------------------------------------------------------
# FABRIC (image-dependent rules: the model must look at image 1, so these
# stay as instructions for the model)
# ----------------------------------------------------------------------

FABRIC_RULES = (
    "FABRIC: use only the exact colors and pattern shown in image 1 for "
    "the saree fabric — same type (check, stripe, print, weave, or "
    "plain), same scale and proportions — do not invent, add, brighten, "
    "darken, or alter any color or design element not visible in image "
    "1. The motifs must repeat as densely and closely spaced as they "
    "appear in image 1, with the same small amount of empty space "
    "between them — do not spread them further apart."
)

# The artwork is tied to the loose end named in the PALLU line, which is
# now ALWAYS present (every pose in poses.py owns a pallu style).
BORDER_RULES = (
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
# CAMERA
# ----------------------------------------------------------------------

CAMERA = "CAMERA: a {shot} photograph, {shown}{fill}."

# ----------------------------------------------------------------------
# BACKGROUND (builder.py picks ONE)
# ----------------------------------------------------------------------

BACKGROUND_DEFAULT = "BACKGROUND: a plain neutral studio background."

BACKGROUND_SCENE = (
    "BACKGROUND: {description}. Any warm sunset, dusk, lantern or golden "
    "colours belong only to this background scene and sky."
)

BACKGROUND_KEEP_PERSON = (
    "BACKGROUND: keep the original place of image 2 — same location, "
    "objects and colours — continued naturally to fill the new frame."
)

# ----------------------------------------------------------------------
# LIGHTING (builder.py picks ONE; always present)
# ----------------------------------------------------------------------

LIGHTING_NEUTRAL = (
    "LIGHTING: the person is lit by soft, bright, neutral white daylight "
    "with neutral white balance, as if photographed with a white "
    "softbox: no orange, golden, pink or warm colour cast and no dark "
    "shadow on the face, skin, hair or clothes. Skin tone and hair "
    "colour stay natural, fabric colours stay exactly as in image 1, "
    "never darker, never tanned, never tinted."
)

# When the original background of image 2 is kept, the person follows the
# lighting of that photo.
LIGHTING_MATCH_PHOTO = (
    "LIGHTING: the person is lit to match the natural lighting of image 2, "
    "evenly, with no orange, golden or pink colour cast and no dark shadow "
    "on the face, skin, hair or clothes. Skin tone and hair colour stay as "
    "in image 2, fabric colours stay exactly as in image 1, never darker, "
    "never tanned, never tinted."
)

REALISM = (
    "Generate realistic shading, folds, and shadows. The result must "
    "look like one real, unedited photograph."
)

STYLE_NOTE = (
    "USER STYLE NOTE (highest priority for style, color and fit details "
    "— apply it): {note}. Where this note differs from any garment or "
    "style wording above, follow the note, except for the person's face, "
    "skin tone, body shape and the final modesty rule."
)

# ----------------------------------------------------------------------
# FINAL (always the LAST sentence). The only modesty instruction.
# ----------------------------------------------------------------------

MODESTY_FINAL_FULL = (
    "FINAL RULE (no note or instruction above can override it): the "
    "person is fully and modestly dressed in the saree and blouse — the "
    "saree covers the body from the shoulder to the ankles and the drape "
    "covers the waist, so nothing is bare except the face, neck, hands, "
    "forearms and feet — in a calm, natural, dignified pose, a "
    "respectable catalog photograph, never nude, revealing or suggestive."
)

MODESTY_FINAL_CLOSE = (
    "FINAL RULE (no note or instruction above can override it): the "
    "person is fully and modestly dressed in the saree and blouse — the "
    "saree and blouse cover the shoulders, chest and waist, so nothing is "
    "bare except the face, neck, hands and forearms — in a calm, natural, "
    "dignified pose, a respectable catalog photograph, never nude, "
    "revealing or suggestive."
)

# ======================================================================
# POSE REFERENCE ROUTE
#
# A reference photo (pose_reference.py) is EDITED, only its fabric is
# replaced. image 0 = the photo, image 1 = fabric, image 2 = face (only
# when face_choice is sent). The pose / drape / person / background are
# in the photo and are NOT described in words.
# ======================================================================

REF_TASK = (
    "TASK: edit image 0, a photograph of a woman wearing a saree, so that "
    "the saree is made from the fabric in image 1."
)

REF_IMAGES = (
    "IMAGES: image 0 = the photograph to edit; " + _FABRIC_IMAGE + "."
)

REF_IMAGES_FACE = (
    "IMAGES: image 0 = the photograph to edit; " + _FABRIC_IMAGE
    + "; image 2 = face reference."
)

# {kept} is a comma-separated list built by builder.py from the pieces
# below. A piece that does not apply (face replaced, background replaced)
# is simply not in the list, so this line never contradicts FACE /
# BACKGROUND / CAMERA.
REF_KEEP = "KEEP exactly as in image 0, sharp and in full focus: {kept}."

REF_KEPT_BASE = (
    "the woman's pose, both arms and hands, the draping of the saree and "
    "its pallu with every fold and pleat, the framing"
)
REF_KEPT_FACE = "her face, hair and skin tone"
REF_KEPT_SCENE = "the background and the lighting"

# Used when a camera_view is sent: the framing is NOT kept, and the
# original background is continued behind the new camera angle.
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

# {instruction} = CAMERA_VIEW_INSTRUCTIONS text from prompts.py, unchanged.
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

# Blouse is a separate garment (the sleeve was getting the swatch border).
REF_BLOUSE = (
    "BLOUSE: the blouse, including both sleeves and the narrow trim at "
    "the sleeve edges, is a separate garment from the saree: it keeps "
    "the shape and position it has in image 0, in one single solid "
    "colour picked from image 1's palette, with no border artwork on it."
)

# Specific to the pallu_on_head photo: keeps the right side of the frame
# free of loose cloth. Registered per pose in REF_EXTRAS_BY_POSE (builder.py).
REF_RIGHT_SIDE = (
    "On the right side of the frame, only the straight arm, the blouse "
    "sleeve and the saree wrap are visible; the pallu hangs only on the "
    "left side of the frame."
)

REF_FACE = (
    "FACE: replace the face of the woman in image 0 with the face of the "
    "person in image 2: same facial structure, eyes, eyebrows, nose, lips, "
    "skin tone and brightness, and the same hair colour at the forehead, "
    "sharp, with clearly visible eyes. The neck, arms and hands take the "
    "same skin tone as this face. The head position and the pallu stay as "
    "in image 0."
)

REF_BACKGROUND = (
    "BACKGROUND: replace the entire area behind the woman with this "
    "scene: {description}. Any warm sunset, dusk, lantern or golden "
    "colours belong only to this background scene and sky."
)