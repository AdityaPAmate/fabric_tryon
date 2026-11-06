"""Catalog shot selection and instructions, separate from HTTP orchestration."""
from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours, has_single_colour_family, colour_reference_prompt, SHIRT_COLOUR_PRIORITY
from fabricapp.ai.fabric.fabric_material import material_prompt, fabric_target
from fabricapp.ai.garments.shirt.prompts import PRESSED_FINISH
from fabricapp.ai.scene.garment_lighting import apply_garment_lighting
from fabricapp.ai.scene.backgrounds import get_background_description

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
    if garment == 'shirt':
        back_crop = ('the entire back of the head with a little space above the hair, shoulders, '
                     'and the full shirt down to its lower hem. Keep the face turned away')
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
    angle = ('three_quarter', 'FRONT THREE-QUARTER close-up photograph: rotate the ENTIRE torso and hips '
             '45 degrees to the model\'s left from the front reference. Show a clearly diagonal chest, '
             'a visible side panel from armpit to hem, a foreshortened far shoulder and the front button line. '
             'The near shoulder is substantially closer to the camera than the far shoulder. '
             'Keep the front and side of the shirt both visible. The head follows the torso turn. '
             'Do not repeat the straight-on front pose and do not rotate all the way to a 90-degree side profile. '
             'Frame from head to just below the garment hem; exclude lower legs and shoes')
    if garment == 'shirt':
        angle = ('close_up', 'standard camera close-up')
    return [('front', 'front full-body view'), angle,
            ('back', 'REAR CLOSE-UP product photograph, facing directly away from the camera. '
             'Fill the frame with ' + back_crop + '. Do not frame a complete head-to-feet person')] + details


def edit_config(data, shot, anchor_seed, *, reference_template=None, view=None):
    target = fabric_target(data['garment_type'], data.get('garment_style'), data.get('garment_details'))
    profile = measure_fabric_colours(data['fabric_image'], data.get('options', {}).get('fabric_crop_box'))
    shirt_colour_lock = data['garment_type'] == 'shirt'
    colour = (colour_reference_prompt(
        profile, target, preserve_palette=shirt_colour_lock and
        not all(c["name"] == "deep orange-brown" for c in profile["colours"]))
              if shirt_colour_lock or has_single_colour_family(profile) else '')
    material = material_prompt(data.get('fabric_type', 'unspecified'), data['garment_type'],
                               data.get('garment_style'), data.get('garment_details'))
    # Full trouser construction applies to the outfit, not to a close-up crop.
    if view not in ('front', 'three_quarter'):
        material = material.split('TROUSER CONSTRUCTION:')[0]
    if reference_template:
        prompt = (
            'Edit image 0 in place. Replace ALL visible shirt fabric with the fabric from image 1. '
            'Keep the exact crop, camera angle, garment silhouette, seams and button positions of image 0. '
            'Use image 1 only for the cloth colour, printed pattern and texture, not for composition. '
            'Remove the original plain cloth colour. Follow the existing fabric volume and panel directions '
            'with natural fold shading and visible stitching, rather than a flat pasted texture. '
            'Keep all non-fabric areas as in image 0. Output one edited photograph. '
        )
        if view == 'collar':
            prompt += (
                'Replace both collar leaves, the inner collar stand and every visible shirt panel. '
                'Keep the existing chin, neck, collar opening, buttons and background. '
                'Retain soft shadows beneath the collar points. '
            )
        elif view == 'cuff':
            prompt += (
                'This reference shows one vertical sleeve ending in a broad horizontal cuff, '
                'with a pointed sleeve placket above it and one white cuff button. '
                'Replace all visible sleeve, cuff and sleeve-placket cloth with the same swatch; '
                'leave no original plain white cloth. Preserve the complete cuff, its stitched edges, '
                'single button and the exposed wrist below it. The grey areas on both sides are '
                'background, not shirt fabric. Keep them and the skin unchanged. '
                'There is no shirt torso or front button placket in this reference; do not add them. '
                'Keep the sleeve vertical and do not rotate the arm or tighten the crop. '
                'Keep the print as distinct and saturated as image 1, not grey, blurred or washed out. '
            )
        elif view == 'hem':
            prompt += (
                'This is a tight waist-level macro of an untucked shirt bottom edge: keep the gently curved '
                'hem, its stitched edge, the single white button and the nearly vertical front placket exactly where '
                'they are in image 0. The dark trousers below the hem remain unchanged. '
                'Preserve the small opening between the front panels at the bottom and the grey '
                'background outside the shirt on both sides. Replace all visible shirt panels, '
                'including the front placket and narrow turned hem, without changing their outlines. '
                'The reference has no visible arms, hands, sleeves, collar or face; add none. '
                'Do not pull the camera back or show any more of the person. '
            )
    else:
        anchor_slot = 2 if view == 'three_quarter' or (view == 'back' and data['garment_type'] == 'shirt') else 0
        prompt = (
            f'Create exactly ONE NEW photograph: {shot}. Image {anchor_slot} is the approved front photograph of this catalogue. '
            + ('Image 0 is a blank canvas, not the pose to preserve. Compose the requested new framing and pose '
               'using image 2 only as the identity, outfit and location reference. ' if anchor_slot == 2 else '') +
            'Show the SAME person wearing the SAME finished outfit, with the same fit, seams, buttons, '
            'colours, fabric pattern size and material. Change only camera angle or framing as requested. '
            f'The garment being catalogued is {target}. Image 1 is its original fabric swatch: '
            'preserve its texture and motifs; keep the same finished garment and all separate clothing. '
            'Preserve shirt hem placement symmetrically: if untucked, the complete hem remains outside the trousers '
            'on both sides, never half-tucked. If tucked, both sides remain fully tucked. '
        )
        background = get_background_description(data.get('background'), garment_type=data['garment_type'])
        prompt += ('BACKGROUND: retain this actual location around the person: ' + background +
                   '. Keep visible location details behind the person; do not replace it with a white/grey studio. '
                   if background else f'BACKGROUND: retain the same actual setting from image {anchor_slot}. ')
        prompt += ('Preserve realistic lighting and fold shading. For details retain the existing construction. '
                   'No collage, panels, swatch inset, text or watermark. ')
        if view == 'back' and data['garment_type'] == 'shirt':
            prompt += ('REAR CROP PRIORITY: a new head-to-hip rear close-up, with the complete back '
                       'of the head and the entire shirt from shoulders to hem filling the frame. '
                       'The bottom edge stops just below the shirt hem, with only a narrow strip of trousers. '
                       'No thighs, knees, lower legs or shoes. Image 2 supplies identity and body build, '
                       'not its full-body framing. Keep the back facing the camera and the face hidden. ')
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
    if data['garment_type'] == 'shirt':
        if reference_template:
            prompt += ('Give the replacement fabric a smooth pressed appearance within the existing '
                       'folds and silhouette. Preserve the reference geometry. ')
        else:
            prompt += PRESSED_FINISH
    # Repeat the short framing requirement last, after material instructions.
    prompt += ('FINAL CROP: match image 0 exactly. ' if reference_template else
               'FINAL CAMERA REQUIREMENT: an obvious oblique front-and-side view, not the original frontal pose; close-up from head to just below garment hem, no lower legs or shoes. '
               if view == 'three_quarter' else 'FINAL CAMERA REQUIREMENT: ' + shot + '. ')
    if shirt_colour_lock:
        prompt += SHIRT_COLOUR_PRIORITY
    if reference_template and view == 'hem':
        prompt += 'FINAL REGION LOCK: edit only the existing shirt fabric in image 0. Preserve all other regions. '
    config = {'prompt': prompt, 'seed': anchor_seed, 'guidance': data.get('guidance', 7),
            'prompt_version': ('catalog-template-v5-direct-ai' if reference_template else
                               'catalog-angle-v2' if view == 'three_quarter' else 'catalog-edit-v2')
                              + ('-swatch-v2' if shirt_colour_lock else '')
                              + ('-brown-v2' if 'COLOUR PRIORITY:' in colour else ''),
            **({'output_size_multiple': 32} if reference_template else {}),
            'safety_retry_count': 0}
    if data['garment_type'] == 'shirt' and (reference_template or view == 'back'):
        from fabricapp.ai.images.catalog_collage import SHIRT_OUTPUT_SIZES
        config['output_dimensions'] = SHIRT_OUTPUT_SIZES[view]
        config['prompt_version'] += '-catalog-panel-v2'
    return apply_garment_lighting(config, data['garment_type'], reference_detail=bool(reference_template))
