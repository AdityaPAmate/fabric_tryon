"""Keep reference composition and use the uploaded fabric for the kurti."""
from PIL import Image, ImageChops, ImageStat

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.kurti_pant.details import (
    DUPATTA_ADD, KURTI_SLEEVES_FULL_EDIT, KURTI_SLEEVES_HALF_EDIT,
)
from fabricapp.ai.scene.backgrounds import get_background_description


SLEEVE_OPTIONS = {
    'full_sleeves': KURTI_SLEEVES_FULL_EDIT,
    'half_sleeves': KURTI_SLEEVES_HALF_EDIT,
}

DETAIL_PROMPTS = {
    'neckline': (
        'Reproduce the exact crop of image 0: a neckline macro with only the mouth and chin at '
        'the top edge and fabric continuing past the bottom edge. The eyes, nose, full head, '
        'waist and hands are outside the frame. Keep the round neckline, '
        'binding and shoulder positions. Preserve the single narrow floral vine below the binding '
        'and its small central flower with thread drops. The rest of the upper chest shows the '
        'uploaded fabric. The kurti continues past the '
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


def _has_dense_lower_border(fabric):
    sample = fabric.convert('RGB')
    sample.thumbnail((192, 192))
    width, height = sample.size
    if min(width, height) < 16:
        return False

    def edge_strength(top):
        band = sample.crop((round(width * .27), round(height * top),
                            round(width * .80), round(height * (top + .28))))
        left = band.crop((0, 0, band.width - 1, band.height))
        right = band.crop((1, 0, band.width, band.height))
        return sum(ImageStat.Stat(ImageChops.difference(left, right)).mean) / 3

    # Require a substantial increase in detail below the body before treating it as trim.
    body, lower = edge_strength(.12), edge_strength(.62)
    return lower >= body * 1.45 and lower - body >= 5


def _sleeve_fabric_region(data):
    selected = data.get('options', {}).get('fabric_crop_box')
    if selected is not None:
        return selected, 'explicit_crop'

    source = data.get('fabric_image')
    if source is not None:
        position = source.tell()
        try:
            source.seek(0)
            with Image.open(source) as fabric:
                width, height = fabric.size
                if min(width, height) >= 256 and _has_dense_lower_border(fabric):
                    return [round(width * .35), round(height * .12),
                            round(width * .78), round(height * .40)], 'upper_body_crop'
        finally:
            source.seek(position)
        # Long garment panels often carry trim at the top and a wide hem at the bottom.
        # Sample the body above the hem, keeping the width for the motif repeat.
        if height >= 1.5 * width and height >= 256:
            return [0, round(height * 0.30), width, round(height * 0.60)], 'body_band'
    return None, 'full_source'


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
        background = get_background_description(data.get('background'), garment_type='kurti_pant')
        prompt += f'Use {background} as the background where visible. ' if background else 'Retain the reference setting. '
    else:
        prompt += 'Keep the close-up studio composition in image 0. Do not widen the frame to show a scene. '
    if data.get('additional_style_note'):
        prompt += f"Style direction: {data['additional_style_note']}. Preserve the supplied kurti textile and reference framing. "
    prompt += 'Use natural cloth shading. Produce one opaque clothing photograph without text, a watermark or a collage.'
    if shot.key == 'back':
        prompt += (' FINAL BACK VIEW LIGHTING: keep the setting and pose in image 0. Light the back '
                   'of the kurti with soft, neutral daylight from the camera side. The broad cloth '
                   'areas between folds should match the lightness, hue and saturation of image 1. '
                   'Reserve darker shading for individual folds and seams. Keep the ambient '
                   'background warmth out of the kurti fabric.')
    config = {
        'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': _output_dimensions(shot, data.get('options', {}).get('draft_mode', False)),
        'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0,
    }
    context = data if portrait else {**data, 'garment_details': ()}
    if shot.key == 'sleeve':
        crop, selection = _sleeve_fabric_region(data)
        config.update(fabric_crop_box=crop, fabric_region='body', fabric_region_selection=selection)
        context['options'] = {**data.get('options', {}), 'fabric_crop_box': crop}
    config = apply_fabric_conditioning(config, context, 'kurti_pant', match_pattern_colours=True)
    version = {'neckline': 'v5', 'sleeve': 'v6', 'back': 'v5'}.get(shot.key, 'v3')
    config['prompt_version'] = f'kurti-pant-catalog-{version}-{shot.key}'
    return config
