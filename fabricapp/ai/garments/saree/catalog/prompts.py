"""Saree-only template tasks: geometry from references, product fabric from swatch."""
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.garments.saree.catalog.layout import OUTPUT_SIZES


def build_config(data, shot, seed):
    if shot.operation == 'crop':
        return {'output_dimensions': OUTPUT_SIZES[shot.key], 'seed': seed,
                'prompt_version': 'saree-catalog-derived-border-v1'}
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
    if identity and shot.key == 'neckline':
        prompt = (
            'Edit image 0: replace its model with the SAME person from image 2, including the exact '
            'face, loose or tied hairstyle, hair length and skin tone. Image 0 supplies only the pose '
            'and camera crop, never the original face or hairstyle. '
        ) + prompt
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
    if shot.reference_role == 'composition':
        if shot.identity_from:
            prompt = (
                'Generate a NEW side/three-quarter portrait of the SAME woman in image 2. '
                'Image 0 is a blank canvas. Image 1 is the product fabric swatch. '
                'Image 2 is the approved person identity: copy her exact face, skin tone and long or short, '
                'loose or tied hairstyle, plus the same solid blouse. Image 3 is ONLY the camera angle '
                'and shoulder-drape guide, cropped below the face. Generate the complete head '
                'from image 2, with the same hairstyle and facial features. Frame head to hips '
                'at the torso angle shown in image 3; do not copy the guide\'s cropped top edge. '
                'Apply image 1\'s exact printed cloth over the entire saree and pallu, retaining its colours '
                'and motifs with natural folds. Keep the blouse separate and opaque. '
            )
    background = get_background_description(data.get('background'), garment_type='saree')
    prompt += ('BACKGROUND: ' + (background or 'a neutral grey studio, consistent across all seven images')
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
              'prompt_version': 'saree-catalog-editorial-v4-' + shot.key,
              'output_dimensions': dimensions, 'safety_retry_count': 0,
              'fabric_source_format': 'PNG', 'classified_recovery': True}
    config = apply_fabric_conditioning(config, data, 'saree')
    config['prompt'] += ' FINAL SHOT: ' + shot.description + '. '
    config['prompt'] += ('Image 3 controls framing only; image 1 controls all cloth design. '
                         if shot.reference_role == 'composition' else 'Preserve reference crop and all fabric edges. ')
    if shot.key == 'neckline':
        config['prompt'] += ('CROP PRIORITY: match image 0\'s tight shoulder-and-neckline crop. '
                             'Image 2 is only the face/hair identity; do not copy its torso crop. '
                             'Bottom lip at top edge, bust at bottom edge, no waist, hands or forearms. ')
    return config
