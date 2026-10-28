"""Shirt-owned instructions, assembled once by builder.py in priority order."""

GARMENT_TYPE = "shirt"
GARMENT_STYLE_OPTIONS = {}
TASK = (
    "TASK: create one realistic clothing-catalogue photograph featuring a "
    "properly fitted collared button-up shirt made from fabric image 1. "
    "Image 1 supplies only the shirt fabric, not a garment shape or scenery. "
)
FACE_SUBJECT = (
    "SUBJECT: image 0 is a blank canvas. Image 2 supplies the person's facial "
    "identity, skin tone and hairstyle; preserve those features and apparent "
    "age. Generate the body separately using the selected build below. "
)
PERSON_EDIT_SUBJECT = (
    "SUBJECT: edit the person in image 0, preserving their face, hair, skin "
    "tone, expression, accessories, body build, pose and framing. Replace "
    "the source upper and lower clothing with the outfit below. "
)
PERSON_POSE_SUBJECT = (
    "SUBJECT: image 0 is a blank canvas. Image 2 supplies the person's face, "
    "hair, skin tone, apparent age, gender presentation, accessories and "
    "body build. Preserve this identity and body proportions while creating "
    "the requested pose and outfit. "
)
CHILD_SUBJECT = (
    "AGE: a 12-year-old child with age-appropriate proportions and child-sized clothing. "
)
BODY_BUILD = {
    "slim": "BODY BUILD: a slim physique with a narrow torso, slender arms and legs. ",
    "trim": (
        "BODY BUILD: an ATHLETIC, toned physique with broad shoulders, "
        "a tapered waist and defined arms and legs. "
    ),
    "plus": (
        "BODY BUILD: a visibly PLUS-SIZE physique with a broad torso, "
        "full waist and abdomen, fuller upper arms and thighs. "
    ),
}
BODY_FIT = (
    "The shirt and trousers follow this body build, with enough room at "
    "the chest, abdomen, waist and arms; keep the requested build in every "
    "pose. "
)
OUTFIT = (
    "OUTFIT: a button-up shirt with a structured collar, visible front "
    "button placket and closed opaque coverage from the upper chest, "
    "paired with newly generated plain dark solid-colour trousers reaching "
    "the ankles and ordinary closed footwear. "
)
PRESSED_SLEEVES = (
    "The extended sleeves have a pressed finish with a few natural elbow bends. "
)
FABRIC = (
    "FABRIC: reproduce image 1's base colours, pattern, motif scale and "
    "close spacing across the shirt, including its sleeves. Keep dark or "
    "muted fabric dark or muted. Allow natural perspective around seams "
    "and folds and local shading around the original midtones. The fabric "
    "belongs exclusively on the shirt; trousers and scenery stay separate. "
)
ANATOMY = "Show one person with two arms, two hands, two legs and two feet. "
LIGHTING = (
    "LIGHTING: illuminate the person and shirt with soft neutral fill light "
    "and neutral white balance, preserving fabric hue, saturation and "
    "midtone brightness. Keep the background's atmospheric lighting in "
    "the scenery. "
)
NOTE_PRIORITY = (
    "Apply this note to remaining styling choices while retaining the "
    "selected body build, sleeve treatment, shirt hem placement and identity. "
)
FINAL = "FINAL PRESENTATION: one fully clothed person in a realistic fashion-catalogue photograph. "
RETRY_PRESENTATION = (
    "Keep the outfit opaque and fully buttoned from upper chest, with "
    "full-length trousers, retaining the selected shirt hem and sleeve treatment. "
)
