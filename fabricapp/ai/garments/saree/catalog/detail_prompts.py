"""Separate product-region tasks; template fabric is never product evidence."""
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.saree.catalog.layout import OUTPUT_SIZES
from fabricapp.ai.garments.saree.catalog.regions import source_regions
from fabricapp.ai.garments.saree.catalog.product_details import border_reference_box
from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours
from fabricapp.ai.fabric.fabric_material import validate_fabric_type
from fabricapp.ai.pipeline.router import PromptRoutingError


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
    'EDIT IMAGE 0 IN PLACE: this is a tightly cropped photograph of FOLDED TEXTILE. '
    'Change only its cloth surface using image 1. Keep exactly the existing fan of '
    'vertical folds on the left, the diagonal overlapping cloth at the upper left, '
    'and the straight hanging cloth panel on the right. Keep all overlap boundaries, '
    'fold shadows, camera distance and the curved stitched bottom hem fixed. '
    'At the top edge there is only cropped fabric; the complete lower hem remains '
    'near the bottom. Keep the same tiny grey floor area under that hem. '
    'Copy the supplied cloth colour, print, motif scale and weave into these existing '
    'folds. Keep the hanging panel lower edge exactly where image 0 puts it. '
    'Do not zoom out or reconstruct a whole garment display. '
    'No mannequin, body parts, blouse, hanger, stand, new scene, inset or text. '
)


def _condition_pleats(config, context):
    """Cloth-detail conditioning; no whole-outfit prompt before the edit task.

    Every fabric uses this same path, including majority-colour patterned cloth.
    Shared utilities measure samples but do not change this shot's subject.
    """
    material = context.get('fabric_type','unspecified')
    error = validate_fabric_type(material,'saree')
    if error:
        raise PromptRoutingError(error)
    profile = measure_fabric_colours(context['fabric_image'],
        (context.get('options') or {}).get('fabric_crop_box'),palette_size=24,min_coverage=.005)
    samples = ', '.join(sample['hex'] for sample in profile['colours'][:8])
    if samples:
        config['prompt'] += (' Measured cloth samples: '+samples+'. Image 1 determines their '
                             'actual positions and proportions; keep its print on the existing folds. ')
    surface = {
        'unspecified': 'Keep the actual photographed weave and finish from image 1.',
        'cotton': 'Use a fine matte cotton weave with soft diffuse fold highlights.',
        'silk': 'Use a fine silk weave with restrained lustre and smooth fold highlights.',
        'velvet': 'Use dense velvet pile with soft directional nap and broad fold highlights.',
    }[material]
    config['prompt'] += ' MATERIAL: '+surface+' Change only the photographed cloth surface. '
    return {**config,'fabric_type':material,'fabric_colour_reference':profile}

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
        regions['border'] = border_reference_box(data, regions)
    crop = None if flatlay else regions['body' if shot.key == 'pleats' else 'border']
    context = {**data, 'options': {**options, 'fabric_crop_box': crop}}
    dimensions = OUTPUT_SIZES[shot.key]
    if options.get('draft_mode', False):
        scale = min(1, 512 / max(dimensions))
        dimensions = tuple(max(256, round(value * scale / 32) * 32) for value in dimensions)
    config = {
        'prompt': FULL_FABRIC_PROMPT if flatlay else PLEATS_PROMPT if shot.key == 'pleats' else BORDER_PROMPT,
        'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': dimensions, 'safety_retry_count': 0,
        'fabric_source_format': 'PNG', 'classified_recovery': True,
        'fabric_crop_box': crop,
        'fabric_region': 'full_saree' if flatlay else 'body' if shot.key == 'pleats' else 'border',
        'fabric_region_selection': 'full_source' if flatlay else regions['body_selection' if shot.key == 'pleats' else 'border_selection'],
    }
    config = (_condition_pleats(config,context) if shot.key == 'pleats' else
              apply_fabric_conditioning(config,context,'saree',lead_with_edit=flatlay))
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
    config['prompt_version'] = 'saree-catalog-v7-' + shot.key
    return config
