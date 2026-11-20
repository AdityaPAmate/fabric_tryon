"""Separate product-region tasks; template fabric is never product evidence."""
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.saree.catalog.layout import OUTPUT_SIZES
from fabricapp.ai.garments.saree.catalog.regions import source_regions


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

BORDER_PROMPT = (
    'Edit image 0 into a macro photograph of the LONG SIDE BORDER / SELVEDGE from image 1. '
    'Image 0 supplies only the curved outer cloth boundary, fold and camera framing. '
    'The border is the continuous woven or printed band along the long side of a saree, '
    'not the main body print and not the broad pallu end artwork. '
    'Identify the actual side edge visible in image 1 and extract its band colours, stripe '
    'count, motif sequence, orientation and width relative to adjacent body cloth. '
    'Reproduce this real design along the curved edge, with adjoining body cloth inside '
    'and a small area of neutral background outside the physical cloth boundary. '
    'Do not copy image 0 black double stripes, white colour or decorative border. '
    'Do not turn scattered body motifs into a border band. '
    'If image 1 contains only body fabric and no distinct border is visible, use a plain '
    'finished edge matching that body fabric; never invent zari, embroidery or stripes '
    'or imply that an unseen decorative border was extracted. '
    'Preserve realistic cloth thickness and fold shadows. No people, hands, text, inset or collage. '
)


def build_detail_config(data, shot, seed):
    if shot.key == 'pleats':
        raise ValueError('Pleats must be cropped from the generated front, not generated independently.')
    options = data.get('options') or {}
    flatlay = shot.key == 'fabric_texture'
    regions = source_regions(data)
    crop = None if flatlay else regions['border']
    context = {**data, 'options': {**options, 'fabric_crop_box': crop}}
    dimensions = OUTPUT_SIZES[shot.key]
    if options.get('draft_mode', False):
        scale = min(1, 512 / max(dimensions))
        dimensions = tuple(max(256, round(value * scale / 32) * 32) for value in dimensions)
    config = {
        'prompt': FULL_FABRIC_PROMPT if flatlay else BORDER_PROMPT,
        'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': dimensions, 'safety_retry_count': 0,
        'fabric_source_format': 'PNG', 'classified_recovery': True,
        'fabric_crop_box': crop,
        'fabric_region': 'full_saree' if flatlay else 'border',
        'fabric_region_selection': 'full_source' if flatlay else regions['border_selection'],
    }
    config = apply_fabric_conditioning(config,context,'saree',lead_with_edit=flatlay)
    config['prompt'] += ' Use even neutral white light. Preserve the actual source colour and pattern.'
    if flatlay:
        config['prompt'] += (' FINAL COMPOSITION: the same flat rectangular cloth as image 0, '
                             'all four corners on the table; no body, no blouse and no draped wearer.')
    config['prompt_version'] = 'saree-catalog-v7-' + shot.key
    return config
