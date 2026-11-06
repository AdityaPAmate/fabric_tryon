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
    "Use image 2 only for facial identity: do not copy its crop, source shirt, "
    "clothing position or room background into the new photograph. "
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
CLOSE_UP_CAMERA = (
    "CAMERA PRIORITY: a close-up portrait from the top of the hair to just below "
    "the shirt hem at the hips. Keep the complete head, both shoulders and entire "
    "shirt visible, with only a narrow strip of trousers below the hem. "
    "The head and shirt fill the image height, with little empty space. "
    "The lower frame ends at the hips: no knees, lower legs or shoes in the image. "
    "Use normal portrait perspective and preserve natural head-to-torso proportions; "
    "move the camera closer rather than shrinking or narrowing the body. "
)
CLOSE_UP_OUTFIT = (
    "OUTFIT: a button-up shirt with a structured collar, visible front button "
    "placket and closed opaque coverage from the upper chest. Only the top of "
    "plain dark trousers is visible at the bottom of the head-to-hip crop. "
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
    "LIGHTING: use soft, colour-neutral ambient daylight in open shade. "
    "Keep illumination balanced across the shirt and both sleeves, without direct sunlight. "
    "Preserve the swatch hue, saturation, midtone lightness and visible texture. "
    "Keep only shallow natural fold shadows with smooth transitions. "
)

NOTE_PRIORITY = (
    "Apply this note to remaining styling choices while retaining the "
    "selected body build, sleeve treatment, shirt hem placement and identity. "
)
PRESSED_FINISH = (
    "SHIRT FINISH: show a professionally tailored, freshly pressed shirt with smooth panels, crisp collar points and straight, neat seams. "
    "Keep the fabric texture and only small natural folds at bends. Avoid bunched fabric, puckered seams and deep wrinkles across the chest, back and sleeves. "
)
FINAL = "FINAL PRESENTATION: one fully clothed person in a realistic fashion-catalogue photograph. "
RETRY_PRESENTATION = (
    "Keep the outfit opaque and fully buttoned from upper chest, with "
    "full-length trousers, retaining the selected shirt hem and sleeve treatment. "
)


def output_contract(scenario, camera, details):
    if camera == 'close_up':
        frame = 'Use the requested head-to-hip crop, keeping the complete shirt torso within that crop. '
    elif scenario == 'person_photo':
        frame = 'Keep the source photograph framing. '
    else:
        frame = ('Show the complete person from the top of the head to both shoes, '
                 'with the entire shirt, both sleeve ends and its waist/hem visible. '
                 'Reconstruct the full body independently of any cropped face reference. ')
    hem = ('Both sides of the shirt are fully tucked into the waistband. ' if 'tucked' in details
           else 'The entire shirt hem stays outside the trousers on BOTH sides, continuous across the waist; '
                'no half-tuck, missing panel, open lower half or fabric entering one side of the waistband. ')
    return 'FINAL OUTFIT AND FRAMING: ' + frame + hem + 'Keep the selected garment a collared button-up shirt. '
