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

PROMPT_VERSION = "saree-v3"
REFERENCE_PROMPT_VERSION = "saree-ref-v4"

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
    "IMAGES: image 0 is a blank portrait canvas; image 1 is the saree "
    "fabric swatch; image 2 is ONLY a face-and-hair identity reference, "
    "not a pose, body, clothing or background reference."
)

IMAGES_PERSON_KEEP_BG = (
    "IMAGES: image 0 is a blank portrait canvas; image 1 is the saree "
    "fabric swatch; image 2 is the person's identity reference for face, "
    "hair, skin tone, age, body build, accessories and original background "
    "only. Do not copy image 2 clothing or pose."
)

IMAGES_PERSON_NEW_BG = (
    "IMAGES: image 0 is a blank portrait canvas; image 1 is the saree "
    "fabric swatch; image 2 is the person's identity reference for face, "
    "hair, skin tone, age, body build and accessories only. Do not copy "
    "image 2 clothing, pose or background."
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
    "SUBJECT: create one complete, realistic full person on the blank "
    "canvas. Use image 2 ONLY to reproduce the person's face, hairline, "
    "hairstyle and skin tone accurately. Do not copy image 2's crop, body, "
    "clothes, pose or background. The whole head must remain above the "
    "saree; never place the face inside or behind the fabric. The person is "
    "{person}, with a sharp, clearly visible face and eyes."
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
    "GARMENT: a correctly draped Indian saree with neat front pleats "
    "falling to the ankles. The blouse is a separate, short, normal-length "
    "blouse with elbow-length sleeves and a modest neckline; its back is "
    "fully covered with a closed round back neck. The blouse must be one "
    "solid colour matching the dominant/main colour of image 1, with no "
    "print, motifs, woven pattern or decorative border. The saree covers "
    "the waist and stomach completely."
)

GARMENT_CLOSE = (
    "GARMENT: a correctly draped Indian saree that fully covers the chest "
    "and waist. The blouse is a separate short blouse with elbow-length "
    "sleeves, a modest neckline and a closed, fully covered back. It is one "
    "solid colour matching the dominant/main colour of image 1, with no "
    "print, motifs, pattern or decorative border."
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
    "FABRIC MATCH — image 1 is the colour and pattern source. Reproduce "
    "its actual hue, saturation, brightness, contrast, motif shapes, motif "
    "size, spacing and pattern density on the saree. Do not desaturate, "
    "grey out, darken, brighten, recolour, simplify, enlarge or spread the "
    "motifs. Keep the source fabric's colours vivid to the same degree as "
    "image 1. Preserve realistic folds and shadows without changing the "
    "underlying fabric colour. The fabric must be fully opaque, not sheer "
    "or transparent, including over the stomach, waist and lap."
)

# The artwork is tied to the loose end named in the PALLU line, which is
# now ALWAYS present (every pose in poses.py owns a pallu style).
BORDER_RULES = (
    "BORDER MATCH: copy the border visible in image 1 exactly, including "
    "its colour, motif, orientation, relative width and position. If image 1 "
    "has a distinct border strip, keep that strip on the saree edge and pallu "
    "edge where the fabric construction naturally places it; do not turn it "
    "into a large panel, move it onto the blouse, or invent a different hem. "
    "If no border is visible in image 1, do not add one. Preserve any separate "
    "main-body pattern and border pattern as distinct source regions."
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
    "FINAL RULE: make a modest, dignified catalogue photograph. The saree "
    "is fully opaque and securely covers the chest, stomach, waist, hips and "
    "legs to the ankles; no skin or underwear shows through the fabric. Keep "
    "the pose natural and non-suggestive. Only the face, neck, hands, "
    "forearms and feet may remain uncovered."
)

MODESTY_FINAL_CLOSE = (
    "FINAL RULE: make a modest, dignified catalogue photograph. The saree "
    "and blouse fully cover the chest and waist; the saree is opaque, with "
    "no skin or underwear visible through it. Keep the pose natural and "
    "non-suggestive. Only the face, neck, hands and forearms may remain "
    "uncovered."
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
    "IMAGES: image 0 is the photograph to edit; image 1 is the fabric "
    "swatch; image 2 is ONLY a face-and-hair identity reference, not a "
    "body, pose, clothing or background reference."
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
    "BORDER MATCH: preserve the exact border shown in image 1, including "
    "its colour, motif, direction, relative width and spacing. Keep the "
    "border aligned with the existing saree and pallu edges in image 0. "
    "Do not invent, widen, remove or relocate the border, and do not apply "
    "border artwork to the blouse. If image 1 has distinct body and border "
    "regions, preserve those as separate regions."
)

# Blouse is a separate garment (the sleeve was getting the swatch border).
REF_BLOUSE = (
    "BLOUSE: keep the blouse shape and position from image 0. It is a "
    "separate garment in one solid colour matching the dominant colour of "
    "image 1, with no print, motifs, pattern or saree-border artwork on "
    "the blouse or sleeves."
)

# Specific to the pallu_on_head photo: keeps the right side of the frame
# free of loose cloth. Registered per pose in REF_EXTRAS_BY_POSE (builder.py).
REF_RIGHT_SIDE = (
    "On the right side of the frame, only the straight arm, the blouse "
    "sleeve and the saree wrap are visible; the pallu hangs only on the "
    "left side of the frame."
)

REF_FACE = (
    "FACE: replace only the woman's facial identity in image 0 with the "
    "face from image 2, preserving its facial structure, eyes, eyebrows, "
    "nose, lips, skin tone and hairline. Keep the head position, body, pose "
    "and pallu from image 0; do not place or blend the face into the fabric."
)

REF_BACKGROUND = (
    "BACKGROUND: replace the entire area behind the woman with this "
    "scene: {description}. Any warm sunset, dusk, lantern or golden "
    "colours belong only to this background scene and sky."
)
