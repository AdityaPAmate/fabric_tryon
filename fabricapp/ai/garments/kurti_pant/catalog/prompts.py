"""Keep reference composition and use the uploaded fabric for the kurti."""
from PIL import Image

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.kurti_pant.catalog.fabric_region import select_body_fabric_region
from fabricapp.ai.garments.kurti_pant.details import (
    DUPATTA_ADD, KURTI_SLEEVES_FULL_EDIT, KURTI_SLEEVES_HALF_EDIT,
)
from fabricapp.ai.scene.backgrounds import get_background_description


SLEEVE_OPTIONS = {
    'full_sleeves': KURTI_SLEEVES_FULL_EDIT,
    'half_sleeves': KURTI_SLEEVES_HALF_EDIT,
}

CATALOG_SCENERY = {
    'white_marble_terrace': 'a carved white marble terrace overlooking a lake and distant hills',
    'festive_street': 'a heritage street with marigold garlands, decorative lanterns and carved balconies',
    'royal_courtyard': 'a palace courtyard with carved archways, columns, a pavilion and a fountain',
    'riverside_ghat': 'a riverside ghat with stone steps, floating lamps and distant temple spires',
}

FABRIC_LIGHTING = (
    ' FINAL FABRIC LIGHTING: light the visible outfit with a broad, diffused neutral-white studio '
    'softbox and gentle fill, with neutral camera white balance. Keep the selected scenery behind '
    'the subject. No direct sunlight, warm sunset light, coloured reflections or strong shadows '
    'on the garment. Use the fabric colour reference for the cloth under this lighting and retain soft local fold shadows. '
    'Keep the original motif colours, fabric weave and surface finish.'
)

DETAIL_PROMPTS = {
    'neckline': (
        'Reproduce the exact crop of image 0: a neckline macro with only the mouth and chin at '
        'the top edge and fabric continuing past the bottom edge. The eyes, nose, full head, '
        'waist and hands are outside the frame. Keep the round neckline, '
        'binding and shoulder positions. Preserve the single narrow floral vine below the binding '
        'and its small central flower with thread drops. Use a continuous field of the same body '
        'cloth around the stitchwork. Keep large hem artwork, edge bands and contrasting panels '
        'outside this crop. The kurti continues past the '
        'bottom edge of the photograph. Show no lower hem, waistband or trousers. '
    ),
    'sleeve': (
        'Reproduce image 0 as a tabletop macro of ONE kurti cuff lying flat on folded matching '
        'kurti cloth. The whole frame is filled with the textile, including underneath the cuff. '
        'Keep the exact diagonal angle, single cuff opening, scalloped edge and pearl buttons. '
        'Apply image 1 across the entire outer sleeve, cuff, button placket, inner fold and '
        'surrounding cloth. Keep the floral stitching in place and use thread colours sampled '
        'from image 1. The buttons keep their pearl finish. Match the uploaded body motif shape '
        'and spacing. The inside of the opening is the reverse of the same fabric in shadow. '
        'Show no hem artwork, unedited template cloth, second sleeve, '
        'contrasting lining, extra fabric layer, dark piping or trousers. '
    ),
}


def _output_dimensions(shot, draft):
    with Image.open(shot.reference) as reference:
        width, height = reference.size
    scale = min(1, (512 if draft else 1536) / max(width, height))
    return tuple(max(256, round(side * scale / 32) * 32) for side in (width, height))


def build_config(data, shot, seed):
    details = data.get('garment_details') or ()
    portrait = shot.key in ('front', 'side', 'back')
    if shot.key == 'pant':
        scene = get_background_description(data.get('background'))
        return {
            'prompt': f'Photograph this empty setting: {scene}. Render an unobstructed, softly out-of-focus '
                      'background for a close-up product photograph. The entire frame contains scenery only. '
                      'No people, garments, objects in the foreground, lettering or watermarks.',
            'seed': seed, 'guidance': data.get('guidance', 7),
            'output_dimensions': _output_dimensions(shot, data.get('options', {}).get('draft_mode', False)),
            'classified_recovery': True, 'safety_retry_count': 0,
            'prompt_version': 'kurti-pant-catalog-background-v1',
        }
    if shot.key in DETAIL_PROMPTS:
        prompt = DETAIL_PROMPTS[shot.key]
        prompt += ('Replace the template cloth with the actual colour, weave and motif spacing '
                   'from image 1. Continue the cloth naturally through the folds '
                   'and around the stitchwork. Keep the original close-up boundaries. ')
    else:
        prompt = (f'Edit image 0 into one product photograph: {shot.description}. '
                   'Use image 0 for the garment cut, camera angle, pose and fold geometry. '
                   'Image 1 is the sole source for the kurti base cloth. Apply its real base colour, '
                   'weave, motifs and repeat scale across all visible kurti fabric, including the '
                   'neckline, sleeves, cuffs, side seams and hem wherever visible. '
                   'Replace the template textile completely, including pale patches in folds. '
                   'Keep any visible pants plain opaque solid white, '
                   'separate from the printed kurti. ')
        if shot.key == 'back':
            prompt += ('Keep the plain, shallow rounded back neck seam and uninterrupted upper back '
                       'from image 0. Continue the repeating body print up to that seam. Keep any '
                       'wide decorative fabric border at the lower hem. The upper back has no '
                       'front neckline embroidery, yoke, vertical placket or ornamental patch. ')
        else:
            prompt += ('Preserve the sewn floral embroidery shown at the neckline and cuffs of '
                       'image 0, using image 1 for the cloth underneath. ')
    if portrait:
        sleeves = next((SLEEVE_OPTIONS[key] for key in details if key in SLEEVE_OPTIONS), None)
        prompt += f'Use {sleeves}. ' if sleeves else 'Keep the sleeve length shown in image 0. '
        if shot.identity_from and any(data.get(key) for key in ('person_image', 'face_image', 'face_choice')):
            prompt += ('Image 2 provides the requested model identity. Match the face, hair and '
                       'skin tone while retaining the pose and complete framing of image 0. ')
        else:
            prompt += 'Retain the reference model and viewing angle. '
        prompt += DUPATTA_ADD if 'with_dupatta' in details else 'Keep the outfit free of a dupatta. '
        prompt += 'Include the complete kurti hem, both ankles and shoes in the frame. '
    else:
        prompt += 'Keep the requested close-up framing and isolate the garment detail. '

    if portrait:
        background = CATALOG_SCENERY.get(data.get('background'))
        prompt += f'Use {background} as the scenery behind the subject. ' if background else 'Retain the reference setting. '
    else:
        prompt += 'Keep the close-up studio composition in image 0. Do not widen the frame to show a scene. '
    if data.get('additional_style_note'):
        prompt += f"Style direction: {data['additional_style_note']}. Preserve the supplied kurti textile and reference framing. "
    prompt += 'Use natural cloth shading. Produce one opaque clothing photograph without text, a watermark or a collage.'
    prompt += FABRIC_LIGHTING
    config = {
        'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': _output_dimensions(shot, data.get('options', {}).get('draft_mode', False)),
        'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0,
    }
    crop, selection = select_body_fabric_region(data)
    context = {**data, 'options': {**data.get('options', {}), 'fabric_crop_box': crop}}
    if portrait:
        if selection == 'detected_body_crop':
            config['prompt'] += (' The measured palette describes the main cloth. Use image 1 '
                                 'for the distinct colours and motifs of the original hem trim.')
    else:
        config.update(fabric_crop_box=crop, fabric_region='body', fabric_region_selection=selection)
        context['garment_details'] = ()
    config = apply_fabric_conditioning(config, context, 'kurti_pant', match_pattern_colours=True)
    config['prompt_version'] = f'kurti-pant-catalog-v9-{shot.key}'
    return config
