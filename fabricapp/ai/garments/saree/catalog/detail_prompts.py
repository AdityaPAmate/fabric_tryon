"""Separate product-region tasks; template fabric is never product evidence."""
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.saree.catalog.layout import OUTPUT_SIZES
from fabricapp.ai.garments.saree.catalog.regions import source_regions
from fabricapp.ai.garments.saree.catalog.product_details import selected_border


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

PLEATS_PROMPT = (
    'Retexture this existing WAIST-TO-HEM PLEATS CLOSE-UP in image 0 using the body cloth '
    'in image 1. Preserve the exact close camera distance, natural vertical folded pleats, '
    'their overlap and the stitched lower hem. The waist enters the TOP edge; the bottom '
    'hem sits near the BOTTOM edge. Only folded saree cloth fills the photograph. Keep the '
    'upper torso, shoulders, neck, blouse, face, hands and mannequin outside the frame. '
    'Keep the hanging pallu panel and its visible lower edge EXACTLY where image 0 places them. '
    'Do not extend it, shorten it or move its lower edge outside the frame. '
    'Reproduce actual body motifs through the natural three-dimensional folds, '
    'without a flat pasted texture. Use a plain neutral studio surface around the bottom '
    'hem, with no architecture or scenery. '
    'Replace the reference white fabric and black stripes with the actual product cloth. '
    'Use an evidenced edge design only; otherwise keep a plain matching stitched hem. '
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
    options = data.get('options') or {}
    flatlay = shot.key == 'fabric_texture'
    regions = source_regions(data)
    if shot.key == 'pleats':
        regions = {**regions}
        regions['border'], regions['border_selection'] = selected_border(data, regions)
    crop = None if flatlay else regions['body' if shot.key == 'pleats' else 'border']
    context = {**data, 'options': {**options, 'fabric_crop_box': crop}}
    dimensions = OUTPUT_SIZES[shot.key]
    if options.get('draft_mode', False):
        scale = min(1, 512 / max(dimensions))
        dimensions = tuple(max(256, round(value * scale / 32) * 32) for value in dimensions)
    config = apply_fabric_conditioning({
        'prompt': FULL_FABRIC_PROMPT if flatlay else PLEATS_PROMPT if shot.key == 'pleats' else BORDER_PROMPT,
        'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': dimensions, 'safety_retry_count': 0,
        'fabric_source_format': 'PNG', 'classified_recovery': True,
        'fabric_crop_box': crop,
        'fabric_region': 'full_saree' if flatlay else 'body' if shot.key == 'pleats' else 'border',
        'fabric_region_selection': 'full_source' if flatlay else regions['body_selection' if shot.key == 'pleats' else 'border_selection'],
    }, context, 'saree', lead_with_edit=flatlay)
    if shot.key == 'pleats' and regions['border'] is not None:
        config['fabric_reference_crops'] = {'side_border': regions['border']}
        config['prompt'] += (' Image 2 is only the actual long-side border cloth. Use its design '
                             'on the existing narrow edge and lower hem; do not put broad pallu '
                             'end artwork there. Keep image 0’s tight pleats crop.')
    config['prompt'] += ' Use even neutral white light. Preserve the actual source colour and pattern.'
    if shot.key == 'pleats':
        config['prompt'] += (' FINAL EDIT LIMIT: replace textile appearance only. Keep image 0’s '
                             'exact pleat count, fold boundaries, overlapping edges and hem contour. '
                             'Do not generate a different drape or a new garment pose.')
    if flatlay:
        config['prompt'] += (' FINAL COMPOSITION: the same flat rectangular cloth as image 0, '
                             'all four corners on the table; no body, no blouse and no draped wearer.')
    config['prompt_version'] = 'saree-catalog-v5-' + shot.key
    return config
