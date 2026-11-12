"""Keep reference composition and use the uploaded fabric for the kurti."""
from PIL import Image

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.kurti_pant.details import (
    DUPATTA_ADD, KURTI_SLEEVES_FULL_EDIT, KURTI_SLEEVES_HALF_EDIT,
)
from fabricapp.ai.scene.backgrounds import get_background_description


SLEEVE_OPTIONS = {
    'full_sleeves': KURTI_SLEEVES_FULL_EDIT,
    'half_sleeves': KURTI_SLEEVES_HALF_EDIT,
}


def _output_dimensions(shot, draft):
    with Image.open(shot.reference) as reference:
        width, height = reference.size
    scale = min(1, (512 if draft else 1536) / max(width, height))
    return tuple(max(256, round(side * scale / 32) * 32) for side in (width, height))


def build_config(data, shot, seed):
    details = data.get('garment_details') or ()
    portrait = shot.key in ('front', 'side', 'back')
    prompt = (f'Edit image 0 into one product photograph: {shot.description}. '
              'Use image 0 for the garment cut, camera angle, pose and fold geometry. ')
    if shot.key == 'pant':
        prompt += ('Show only the plain opaque white straight-cut pants. Preserve their waistband, '
                   'seams and natural folds. Image 1 is for the kurti only. Keep the pants solid '
                   'white, with no fabric print, decorative border or embroidery. ')
    else:
        prompt += ('Image 1 is the sole source for the kurti textile. Apply its real base colour, '
                   'weave, motifs and repeat scale across all visible kurti fabric, including the '
                   'neckline, sleeves, cuffs, side seams and hem wherever visible. '
                   'Replace the template textile completely, including pale patches in folds. '
                   'Keep the neckline and cuff shapes while removing template embroidery unless '
                   'the supplied textile shows it. Place any real trim from image 1 at the '
                   'finished garment edges. Keep any visible pants plain opaque solid white, '
                   'separate from the printed kurti. ')
    if portrait or shot.key == 'sleeve':
        sleeves = next((SLEEVE_OPTIONS[key] for key in details if key in SLEEVE_OPTIONS), None)
        prompt += f'Use {sleeves}. ' if sleeves else 'Keep the sleeve length shown in image 0. '
    if portrait:
        if shot.identity_from and any(data.get(key) for key in ('person_image', 'face_image', 'face_choice')):
            prompt += ('Image 2 provides the requested model identity. Match the face, hair and '
                       'skin tone while retaining the pose and complete framing of image 0. ')
        else:
            prompt += 'Retain the reference model and viewing angle. '
        prompt += DUPATTA_ADD if 'with_dupatta' in details else 'Keep the outfit free of a dupatta. '
        prompt += 'Include the complete kurti hem, both ankles and shoes in the frame. '
    else:
        prompt += 'Keep the requested close-up framing and isolate the garment detail. '

    background = get_background_description(data.get('background'), garment_type='kurti_pant')
    prompt += f'Use {background} as the background where visible. ' if background else 'Retain the reference setting. '
    if data.get('additional_style_note') and shot.key != 'pant':
        prompt += f"Style direction: {data['additional_style_note']}. Preserve the supplied kurti textile and white pants. "
    prompt += 'Use natural cloth shading. Produce one opaque clothing photograph without text, a watermark or a collage.'
    config = {
        'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': _output_dimensions(shot, data.get('options', {}).get('draft_mode', False)),
        'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0,
    }
    if shot.key != 'pant':
        context = data if portrait else {**data, 'garment_details': ()}
        config = apply_fabric_conditioning(config, context, 'kurti_pant')
    config['prompt_version'] = f'kurti-pant-catalog-v1-{shot.key}'
    return config
