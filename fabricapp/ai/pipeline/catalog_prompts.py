"""Catalog shot selection and instructions, separate from HTTP orchestration."""
from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours, has_single_colour_family, colour_reference_prompt
from fabricapp.ai.fabric.fabric_material import material_prompt, fabric_target
from fabricapp.ai.scene.backgrounds import BACKGROUND_DESCRIPTIONS

DETAILS = {
    'shirt': [('collar', 'collar and neckline'), ('cuff', 'sleeve cuff'), ('hem', 'lower shirt hem')],
    'blazer': [('lapel', 'lapel and collar'), ('cuff', 'sleeve cuff'), ('hem', 'lower jacket hem')],
    'kurta': [('neckline', 'neckline'), ('cuff', 'sleeve end'), ('hem', 'lower garment hem')],
    'kurti_pant': [('neckline', 'kurti neckline'), ('sleeve', 'kurti sleeve end'), ('hem', 'lower kurti hem')],
    'pant': [('waistband', 'trouser waistband'), ('pocket', 'trouser side pocket'), ('hem', 'trouser ankle hem')],
    'saree': [('pallu', 'pallu'), ('border', 'saree border'), ('pleats', 'saree pleats')],
}


def catalog_plan(garment):
    back_crop = ('the rear waistband, seat and trouser legs down to their hems, excluding head, upper torso and shoes'
                 if garment == 'pant' else 'the back of the garment from shoulders to its lower hem, excluding the face, legs and shoes')
    details = [(key, f'tight product detail photograph of the {part} only; fill the frame with this area, not the full person')
               for key, part in DETAILS[garment]]
    if garment == 'shirt':
        details = [
            ('collar', 'extreme close-up of the shirt collar, collar points and top two buttons; '
             'frame from below the chin to the upper chest only; exclude the face, eyes, hair, waist and arms'),
            ('cuff', 'extreme close-up of one existing shirt sleeve cuff and its seam, '
             'with only a small adjoining area of sleeve and arm; exclude face and full torso'),
            ('hem', 'extreme close-up of the lower shirt hem, curved edge and hem stitching, '
             'with only a small adjoining section of shirt fabric and trousers; exclude face and chest'),
        ]
    return [('front', 'front full-body view'),
            ('three_quarter', 'FRONT THREE-QUARTER close-up photograph: rotate the ENTIRE torso and hips '
             '45 degrees to the model\'s left from the front reference. Show a clearly diagonal chest, '
             'a visible side panel from armpit to hem, a foreshortened far shoulder and the front button line. '
             'The near shoulder is substantially closer to the camera than the far shoulder. '
             'Keep the front and side of the shirt both visible. The head follows the torso turn. '
             'Do not repeat the straight-on front pose and do not rotate all the way to a 90-degree side profile. '
             'Frame from head to just below the garment hem; exclude lower legs and shoes'),
            ('back', 'REAR CLOSE-UP product photograph, facing directly away from the camera. '
             'Fill the frame with ' + back_crop + '. Do not frame a complete head-to-feet person')] + details


def edit_config(data, shot, anchor_seed, *, reference_template=None, view=None):
    target = fabric_target(data['garment_type'], data.get('garment_style'), data.get('garment_details'))
    profile = measure_fabric_colours(data['fabric_image'], data.get('options', {}).get('fabric_crop_box'))
    detail_colour_lock = bool(reference_template and data['garment_type'] == 'shirt'
                              and view in ('cuff', 'hem'))
    colour = (colour_reference_prompt(
        profile, target, preserve_palette=detail_colour_lock and
        not all(c["name"] == "deep orange-brown" for c in profile["colours"]))
              if detail_colour_lock or has_single_colour_family(profile) else '')
    material = material_prompt(data.get('fabric_type', 'unspecified'), data['garment_type'],
                               data.get('garment_style'), data.get('garment_details'))
    # Full trouser construction applies to the outfit, not to a close-up crop.
    if view not in ('front', 'three_quarter'):
        material = material.split('TROUSER CONSTRUCTION:')[0]
    if reference_template:
        prompt = (
            f'Edit image 0, the supplied {view} close-up reference photograph. '
            'Keep its exact crop, camera angle, garment geometry, collar/cuff/hem shape, seams, button positions, '
            'skin, arm or neck pose and actual non-cloth background. Replace ALL visible shirt fabric in image 0 with '
            'the fabric in image 1, including the collar leaves, collar stand, placket, cuff and adjoining '
            'shirt panels wherever present. Remove the original white or blue cloth colour and texture. '
            'Image 1 supplies the new fabric colour, print and texture, not the crop or garment shape. '
            'Retain realistic folds, stitching and shadows on the replaced cloth. Keep buttons and skin separate. '
            'Do not zoom out, add a person, show a whole face/body, or add text, panels or collage. '
        )
        if view == 'cuff':
            prompt += ('REGION CHECK: the large shirt torso behind the arm, on the upper and right side '
                       'of the photograph, is ALSO shirt fabric, not background. Replace that entire torso '
                       'and its vertical button placket with the same swatch pattern as the cuff and sleeve. '
                       'Replace the complete sleeve, cuff face, cuff edges, sleeve placket and all torso fabric. '
                       'Carry the same pattern continuously across each cloth region with realistic fold shading. '
                       'Do not leave white patches or transfer fabric onto the exposed wrist, hand or buttons. '
                       'Preserve the entire visible cuff and arm from the reference without tightening the crop. '
                       'Leave no original plain white shirt panels behind the arm. ')
        if view == 'hem':
            prompt += ('Replace all white shirt fabric including the curved hem edge and button placket. '
                       'Keep the dark trousers and non-cloth background unchanged. '
                       'Preserve the full curved hem, seam stitching and button positions. '
                       'Every region above the curved hem seam is SHIRT FABRIC, including the far left '
                       'and right edges. There are NO arms, hands or exposed skin in this reference; '
                       'do not invent skin or limbs. The only regions below the seam are the existing '
                       'dark trousers and the narrow background at the left edge. ')
    else:
        anchor_slot = 2 if view == 'three_quarter' else 0
        prompt = (
            f'Create exactly ONE NEW photograph: {shot}. Image {anchor_slot} is the approved front photograph of this catalogue. '
            + ('Image 0 is a blank canvas, not the pose to preserve. Reconstruct the requested new camera angle '
               'using image 2 only as the identity, outfit and location reference. ' if anchor_slot == 2 else '') +
            'Show the SAME person wearing the SAME finished outfit, with the same fit, seams, buttons, '
            'colours, fabric pattern size and material. Change only camera angle or framing as requested. '
            f'The garment being catalogued is {target}. Image 1 is its original fabric swatch: '
            'preserve its texture and motifs; keep the same finished garment and all separate clothing. '
            'Preserve shirt hem placement symmetrically: if untucked, the complete hem remains outside the trousers '
            'on both sides, never half-tucked. If tucked, both sides remain fully tucked. '
        )
        background = BACKGROUND_DESCRIPTIONS.get(data.get('background'))
        prompt += ('BACKGROUND: retain this actual location around the person: ' + background +
                   '. Keep visible location details behind the person; do not replace it with a white/grey studio. '
                   if background else f'BACKGROUND: retain the same actual setting from image {anchor_slot}. ')
        prompt += ('Preserve realistic lighting and fold shading. For details retain the existing construction. '
                   'No collage, panels, swatch inset, text or watermark. ')
        if view == 'three_quarter':
            # A compact camera task avoids the long preservation instructions
            # overpowering the requested rotation of a frontal reference.
            prompt = (
                'CAMERA TASK: generate a NEW close-up FRONT THREE-QUARTER PROFILE photograph. '
                'Image 0 is a blank canvas. Image 2 is the person and outfit identity reference only. '
                'Move the camera 45 degrees around the person toward their left side, halfway between '
                'a straight front view and a side profile. Show the front chest AND the left side panel '
                'of the garment. The far shoulder is partly hidden behind the chest, the near shoulder '
                'is prominent, and the front button line is offset from the visible torso centre. '
                'Head, torso and hips must share this oblique orientation. Show both eyes in a '
                'three-quarter face, not a straight-on face. Keep the SAME person and finished outfit '
                'from image 2. Frame head to just below the garment hem, filling the frame with the upper body. Exclude lower legs and shoes. Image 1 supplies the fabric. '
                'Preserve the hem placement and all separate clothing. '
                + ('LOCATION: ' + background + '. ' if background else 'Keep the location from image 2. ')
                + 'One realistic photograph, no collage or text. '
            )
    prompt += colour + material
    # Repeat the short framing requirement last, after material instructions.
    prompt += ('FINAL CROP: match image 0 exactly. ' if reference_template else
               'FINAL CAMERA REQUIREMENT: an obvious oblique front-and-side view, not the original frontal pose; close-up from head to just below garment hem, no lower legs or shoes. '
               if view == 'three_quarter' else 'FINAL CAMERA REQUIREMENT: ' + shot + '. ')
    if reference_template and view == 'hem':
        prompt += ('FINAL REGION LOCK: no arms, hands or skin. The complete area above the curved '
                   'hem is fabric, including both image edges. Preserve the reference crop and dark trousers. ')
    if detail_colour_lock:
        prompt += (
            'FINAL FABRIC COLOUR: Image 1 is the authority for the exact fabric colours. '
            'Match its base shade, lightness and saturation under neutral diffuse light. '
            'Preserve each printed colour separately and retain its contrast with the base cloth. '
            'Keep realistic local fold shadows, but do not apply a warm or cool cast, boost vibrance, '
            'wash out the print, or inherit the brightness or tint of the original template cloth. '
            'Apply these instructions only to shirt fabric; preserve skin, buttons, trousers and background. '
        )
    return {'prompt': prompt, 'seed': anchor_seed, 'guidance': data.get('guidance', 7),
            'prompt_version': ('catalog-template-v3' if reference_template else
                               'catalog-angle-v2' if view == 'three_quarter' else 'catalog-edit-v2')
                              + ('-swatch-v1' if detail_colour_lock else '')
                              + ('-brown-v2' if 'COLOUR PRIORITY:' in colour else ''),
            **({'output_size_multiple': 32} if reference_template else {}),
            'safety_retry_count': 0}
