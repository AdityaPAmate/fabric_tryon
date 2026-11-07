"""Saree-only template tasks: geometry from references, product fabric from swatch."""
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.garments.saree.catalog.layout import OUTPUT_SIZES
from fabricapp.ai.garments.saree.catalog.detail_prompts import build_detail_config


def _reference_output_size(data, shot):
    """Preserve the reference aspect instead of squeezing a spread pallu into its panel."""
    from fabricapp.ai.images.image_utils import get_output_dimensions
    side = 512 if data.get('options', {}).get('draft_mode', False) else 1536
    with shot.reference.open('rb') as source:
        width, height = get_output_dimensions(source, side)
    return max(256, width // 32 * 32), max(256, height // 32 * 32)


def _back_reference_config(data, shot, seed):
    from fabricapp.ai.garments.saree.builder import build_prompt as build_saree_prompt
    # Reuse the normal saree route, including its shared KEEP / pallu / border rules.
    context = {
        'pose': 'back_showing_pallu', 'use_face_reference': False,
        'fabric_image': data.get('fabric_image'), 'fabric_type': data.get('fabric_type', 'unspecified'),
        'background': data.get('background'), 'options': data.get('options', {}),
        'additional_style_note': data.get('additional_style_note'),
    }
    config = build_saree_prompt(scenario='pose_reference', garment_type='saree', context=context,
                                seed=seed, guidance=data.get('guidance'))
    return {**config, 'output_dimensions': _reference_output_size(data, shot),
            'prompt_version': 'saree-catalog-normal-back-reference-v1',
            'safety_retry_count': 0, 'fabric_source_format': 'PNG', 'classified_recovery': True,
            'forbid_identity_references': True}


def _side_portrait_config(data, shot, seed):
    has_identity = bool(data.get('face_image') or data.get('face_choice') or data.get('person_image'))
    prompt = (
        'Edit image 0 in place. Keep its exact three-quarter/side-facing body and head angle, '
        'camera crop, hand positions, blouse silhouette and hanging pallu shape. '
        'Image 1 is the product fabric swatch. Replace all visible saree cloth with its exact '
        'colours, print, motif scale and texture, following the existing folds. '
        'Keep the same angle rather than turning the model to face the camera. '
        'The blouse remains a separate opaque solid coordinating garment. '
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
    config = apply_fabric_conditioning({
        'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': dimensions, 'safety_retry_count': 0,
        'fabric_source_format': 'PNG', 'classified_recovery': True,
    }, data, 'saree')
    config['prompt_version'] = 'saree-catalog-side-template-v1'
    config['prompt'] += ' FINAL POSE: preserve image 0 side angle and exact crop, not a frontal portrait. '
    return config


def build_config(data, shot, seed):
    if shot.key == 'side_portrait':
        return _side_portrait_config(data, shot, seed)
    if shot.key == 'back_pallu':
        return _back_reference_config(data, shot, seed)
    if shot.key in ('fabric_texture', 'border'):
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
