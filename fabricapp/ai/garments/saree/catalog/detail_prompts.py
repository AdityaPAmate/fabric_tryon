"""Separate product-region tasks; template fabric is never product evidence."""
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.saree.catalog.layout import OUTPUT_SIZES


FULL_FABRIC_PROMPT = (
    'EDIT IMAGE 0 IN PLACE: keep its single FLAT RECTANGLE of cloth lying on a table, '
    'its overhead camera, all four visible corners and its surrounding studio surface. '
    'Replace the entire rectangular textile surface with the supplied product from image 1. '
    'The result is a COMPLETE SAREE FLAT-LAY, spread flat and photographed directly from above. '
    'Show its body, BOTH long side borders and COMPLETE pallu end TOGETHER, with all four '
    'outer edges and corners inside the frame. Image 0 supplies only the flat-lay placement '
    'on a neutral studio surface, never textile colour or design. Preserve every supplied '
    'region and its actual colours, motifs and relative proportions. Keep the body pattern '
    'on the body, side-border design on the sides and broad end artwork on the pallu end. '
    'Use a few shallow settling folds without hiding any region. Match the source weave; '
    'replace all reference white cloth and pale lines with the actual product. If only a '
    'body swatch is supplied, use that cloth consistently with plain finished edges; do not '
    'invent unseen ornamental borders or a pallu design. Keep the whole outline inside '
    'small natural studio margins; do not zoom into a fabric macro. '
    'The subject is a rectangular piece of fabric, not a dressed figure. '
    'Do not form shoulders, a neckline, sleeves, a waist or a human silhouette. '
    'No wearer, mannequin, blouse, face, hands, text, inset or collage. '
)

def build_detail_config(data, shot, seed):
    if shot.key == 'border':
        from fabricapp.ai.garments.saree.catalog.border_ai import build_border_config
        return build_border_config(data, seed)
    if shot.key == 'pleats':
        raise ValueError('Pleats must be cropped from the generated front, not generated independently.')
    options = data.get('options') or {}
    if shot.key != 'fabric_texture':
        raise ValueError(f'Unsupported Saree detail: {shot.key}')
    crop = None
    context = {**data, 'options': {**options, 'fabric_crop_box': crop}}
    dimensions = OUTPUT_SIZES[shot.key]
    if options.get('draft_mode', False):
        scale = min(1, 512 / max(dimensions))
        dimensions = tuple(max(256, round(value * scale / 32) * 32) for value in dimensions)
    config = {
        'prompt': FULL_FABRIC_PROMPT,
        'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': dimensions, 'safety_retry_count': 0,
        'fabric_source_format': 'PNG', 'classified_recovery': True,
        'fabric_crop_box': crop,
        'fabric_region': 'full_saree',
        'fabric_region_selection': 'full_source',
    }
    config = apply_fabric_conditioning(config,context,'saree',lead_with_edit=True)
    config['prompt'] += ' Use even neutral white light. Preserve the actual source colour and pattern.'
    config['prompt'] += (' FINAL COMPOSITION: the same flat rectangular cloth as image 0, '
                         'all four corners on the table; no body, no blouse and no draped wearer.')
    config['prompt_version'] = 'saree-catalog-v7-' + shot.key
    return config
