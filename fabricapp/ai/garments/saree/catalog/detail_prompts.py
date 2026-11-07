"""Separate product-region tasks; template fabric is never product evidence."""
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.saree.catalog.layout import OUTPUT_SIZES


BODY_PROMPT = (
    'Edit image 0 into a macro photograph of the MAIN BODY FABRIC from image 1. '
    'Image 0 supplies only shallow folds, lighting and camera framing, never product design. '
    'Identify the uninterrupted central body cloth in image 1, excluding long-side borders, '
    'selvedges, pallu end panels and hems. Extract its actual base colour, woven texture, '
    'motifs, repeat spacing and relative motif scale. Fill the frame with that body fabric '
    'over gentle folds. Preserve printed motifs if present; do not substitute the template '
    'white weave or invent microscopic yarn detail beyond the supplied evidence. '
    'No border bands, edge stripes, people, hands, text, inset or collage. '
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
    body = shot.key == 'fabric_texture'
    # Border must see the original image when a global body-only crop excludes its edge.
    crop = options.get('fabric_body_crop_box', options.get('fabric_crop_box')) if body else options.get('fabric_border_crop_box')
    context = {**data, 'options': {**options, 'fabric_crop_box': crop}}
    dimensions = OUTPUT_SIZES[shot.key]
    if options.get('draft_mode', False):
        scale = min(1, 512 / max(dimensions))
        dimensions = tuple(max(256, round(value * scale / 32) * 32) for value in dimensions)
    config = apply_fabric_conditioning({
        'prompt': BODY_PROMPT if body else BORDER_PROMPT,
        'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': dimensions, 'safety_retry_count': 0,
        'fabric_source_format': 'PNG', 'classified_recovery': True,
        'fabric_crop_box': crop,
        'fabric_region': 'body' if body else 'border',
        'fabric_region_selection': 'explicit_crop' if crop is not None else 'full_source',
    }, context, 'saree')
    config['prompt_version'] = 'saree-catalog-body-texture-v2' if body else 'saree-catalog-side-border-v2'
    return config
