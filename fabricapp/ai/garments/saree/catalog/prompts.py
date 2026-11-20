"""Saree-only template tasks: geometry from references, product fabric from swatch."""
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.garments.saree.catalog.layout import OUTPUT_SIZES
from fabricapp.ai.garments.saree.catalog.detail_prompts import build_detail_config
from fabricapp.ai.garments.saree.catalog.regions import source_regions


def _reference_output_size(data, shot):
    """Preserve the reference aspect instead of squeezing a spread pallu into its panel."""
    from fabricapp.ai.images.image_utils import get_output_dimensions
    side = 512 if data.get('options', {}).get('draft_mode', False) else 1536
    with shot.reference.open('rb') as source:
        width, height = get_output_dimensions(source, side)
    return max(256, width // 32 * 32), max(256, height // 32 * 32)


def _back_reference_config(data, shot, seed):
    prompt = (
        'Edit the full-length REAR photograph in image 0. Replace ALL visible saree cloth '
        'with the actual product in image 1: the rear wrap, lower skirt, pallu, pleats and '
        'edge borders. Keep the EXACT pallu silhouette, angle, grip and lower end already '
        'in image 0. Do not straighten, move or redesign its drape. Preserve the visible '
        'lower skirt and complete floor-level hem. Preserve natural gravity and soft cloth folds. '
        'Image 0 fixes only the rear stance, arms, grip, framing and cloth geometry. '
        'Remove the reference white colour and black lines unless present in image 1. '
        'Map body motifs onto the wrapped saree; map broad end artwork ONLY onto the pallu '
        'end; keep narrow side borders along the real edges. Do not replace the entire lower '
        'skirt with end artwork or leave any original white cloth. '
        'Do not invent a decorative border or pallu artwork absent from image 1. '
        'The blouse is separate, opaque and solid-coloured to coordinate with the source; '
        'no saree artwork on it. '
        'Keep the template wearer, hair and rear-facing torso. No face/person identity '
        'reference is used. EXACTLY ONE PERSON, the existing wearer in image 0. '
        'Do not add another head, body, person, duplicate silhouette or an overlapping figure. '
        'One natural product photograph, with no text or collage. '
    )
    background = get_background_description(data.get('background'), garment_type='saree')
    if background:
        prompt += 'Place only the setting behind the wearer: ' + background + '. '
    if data.get('additional_style_note'):
        prompt += 'Styling: ' + data['additional_style_note'] + '. '
    context = {**data, 'options': {**data.get('options', {}), 'fabric_crop_box': None}}
    config = apply_fabric_conditioning({
        'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': _reference_output_size(data, shot), 'output_size_multiple': 32,
        'subject_input_max_side': 768, 'fabric_crop_box': None,
        'safety_retry_count': 0, 'fabric_source_format': 'PNG', 'classified_recovery': True,
        'forbid_identity_references': True,
    }, context, 'saree', match_pattern_colours=True, lead_with_edit=True)
    config['prompt'] += (' FINAL REAR GEOMETRY: keep image 0’s existing single wearer and pallu geometry, '
                         'including the visible lower skirt. Keep all cloth edges '
                         'inside the frame. Use even neutral white light, not warm sunlight.')
    config['prompt_version'] = 'saree-catalog-single-back-v3'
    return config


def _side_portrait_config(data, shot, seed):
    has_identity = bool(data.get('face_image') or data.get('face_choice') or data.get('person_image'))
    prompt = (
        'Edit image 0 in place. Keep its exact three-quarter/side-facing body and head angle, '
        'camera crop, hand positions, blouse silhouette and hanging pallu shape. '
        'Image 1 is the product fabric swatch. Replace all visible saree cloth with its exact '
        'colours, print, motif scale and texture, following the existing folds. '
        'Keep the same angle rather than turning the model to face the camera. '
        'The blouse remains a separate opaque solid coordinating garment. '
        'The long pallu continues BELOW the bottom frame edge. Its terminal end and broad '
        'decorative end panel are outside this head-to-upper-thigh crop; show only its '
        'continuing length, never a short pallu ending beside the hand or knee. '
        'Remove the template white cloth and black stripes unless the product references '
        'actually show them. Use only an evidenced side border, or a plain matching edge. '
    )
    prompt += ('Image 2 supplies only the requested face/hair identity; preserve the head orientation '
               'and pose in image 0 and take no clothing or posture from image 2. '
               if has_identity else 'Keep the person, face, hairstyle and skin tone already in image 0. ')
    background = get_background_description(data.get('background'), garment_type='saree')
    prompt += ('BACKGROUND: ' + background + '. ' if background else 'Keep image 0 studio backdrop. ')
    prompt += 'One realistic photograph, no text, watermarks, collage or inset. '
    dimensions = OUTPUT_SIZES[shot.key]
    if data.get('options', {}).get('draft_mode', False):
        scale = min(1, 512 / max(dimensions))
        dimensions = tuple(max(256, round(value * scale / 32) * 32) for value in dimensions)
    regions = source_regions(data)
    crop = regions['body']
    context = {**data, 'options': {**data.get('options', {}), 'fabric_crop_box': crop}}
    config = apply_fabric_conditioning({
        'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': dimensions, 'safety_retry_count': 0,
        'fabric_source_format': 'PNG', 'classified_recovery': True,
        'subject_input_max_side': 768, 'fabric_crop_box': crop,
        'fabric_region': 'body', 'fabric_region_selection': regions['body_selection'],
    }, context, 'saree')
    if regions['border'] is not None:
        slot = 3 if has_identity else 2
        config['fabric_reference_crops'] = {'side_border': regions['border']}
        config['prompt'] += f' Image {slot} supplies only the actual narrow side border for the visible long edge. '
    config['prompt_version'] = 'saree-catalog-side-template-v2'
    config['prompt'] += (' FINAL POSE: preserve image 0 side angle and exact crop, not a frontal portrait. '
                         'The pallu end stays below the frame, with no visible terminal end panel. '
                         'Use even neutral white light on the cloth, with no direct sunlight or warm cast.')
    return config


def build_config(data, shot, seed):
    if shot.key == 'side_portrait':
        return _side_portrait_config(data, shot, seed)
    if shot.key == 'back_pallu':
        return _back_reference_config(data, shot, seed)
    if shot.key in ('fabric_texture', 'border', 'pleats'):
        return build_detail_config(data, shot, seed)
    identity = bool(shot.identity_from and (shot.identity_from != 'request' or
                    data.get('person_image') or data.get('face_image') or data.get('face_choice')))
    prompt = (
        f'Create ONE realistic saree catalog photograph: {shot.description}. '
        'Image 0 supplies the pose, drape geometry and camera crop. Image 1 is the product fabric swatch. '
        'Replace ALL visible saree body, pleats, pallu and border cloth using image 1, preserving '
        'its actual colours, print, motif scale and texture across the entire saree. '
        'Do not retain the reference saree\'s white colour, black stripes, silver edging or other '
        'design unless visible in the submitted swatch. Do not invent an ornamental border absent from image 1. '
        'Preserve one continuous saree and natural fold shading; do not paste a flat texture. '
    )
    if shot.identity_from:
        if identity:
            prompt += ('Image 2 supplies the SAME person, face, hair, skin tone, age and body build '
                       'for this catalog. Preserve that identity while using image 0 only for pose and crop. '
                       'Do not copy the template model\'s identity or body proportions. ')
        else:
            prompt += 'SUBJECT: ' + _person_description(data.get('gender'), data.get('body_type')) + '. '
        prompt += ('Keep a modest opaque blouse and covered lower body, one person with natural anatomy. '
                   'The blouse is separate: one solid colour matching the swatch\'s dominant colour, '
                   'without saree prints or decorative borders. Use the front anchor\'s blouse '
                   'when image 2 is the approved front. ')
    else:
        prompt += 'Fabric-only detail: do not introduce a face, person, hands or extra garments. '
    background = get_background_description(data.get('background'), garment_type='saree')
    prompt += ('BACKGROUND: ' + (background or 'the neutral studio backdrop in image 0')
               + '. Replace the template\'s palace or architectural background when present. '
               'Use neutral white light, preserving fabric colours. No text, watermarks, swatch inset or collage. ')
    if data.get('additional_style_note'):
        prompt += ('STYLE NOTE: ' + data['additional_style_note']
                   + '. Preserve product fabric, requested identity, coverage and shot framing. ')
    dimensions = OUTPUT_SIZES[shot.key]
    if data.get('options', {}).get('draft_mode', False):
        scale = min(1, 512 / max(dimensions))
        dimensions = tuple(max(256, round(value * scale / 32) * 32) for value in dimensions)
    config = {'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
              'prompt_version': 'saree-catalog-six-panel-v1-' + shot.key,
              'output_dimensions': dimensions, 'safety_retry_count': 0,
              'fabric_source_format': 'PNG', 'classified_recovery': True}
    config = apply_fabric_conditioning(config, data, 'saree')
    config['prompt'] += ' FINAL SHOT: ' + shot.description + '. '
    config['prompt'] += 'Preserve reference crop and all fabric edges. '
    return config
