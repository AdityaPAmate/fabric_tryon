"""Fifth panel: hand-held saree drape, replacing the isolated border macro."""


BORDER_PROMPT = (
    'Edit image 0 IN PLACE into ONE natural saree fabric-detail photograph. '
    'Keep the EXACT tight framing, two hands, wrist positions, bangles and soft hanging '
    'cloth folds from image 0. Show the same hands resting over the draped saree; '
    'do not introduce a face, head, full body, mannequin or extra hands. '
    'Image 0 supplies ONLY hand pose, anatomy, framing and drape geometry. '
    'Image 1 is the submitted saree product and the ONLY source of fabric colour and design. '
    'Replace ALL visible saree cloth in image 0, including cloth behind the hands and '
    'the hanging front fold, with image 1 fabric. Preserve its actual body colour, '
    'motif shapes, pattern scale and weave. Keep body print on body cloth and use only '
    'the actual narrow long-side border along the hanging finished edge. '
    'Do not move the broad pallu end artwork onto the body. '
    'Remove every template red/maroon patch, gold border, dot, zigzag and stripe unless '
    'it exists in image 1. If the source shows no decorative border, use a plain finished edge '
    'matching the source fabric; never invent zari, embroidery or stripes. '
    'Render crisp textile detail wrapped naturally around the existing three-dimensional '
    'folds, with the hands naturally occluding the cloth. Do not paste fabric over skin or bangles. '
    'Use even neutral white light and gentle physical fold shading, no sunlight, '
    'warm cast, harsh shadows, cutout edges, text, inset or collage. '
)


def build_border_config(data, seed):
    # No global body-colour conditioning: border colours can differ from the body.
    return {
        'prompt': BORDER_PROMPT, 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': (384, 512) if (data.get('options') or {}).get('draft_mode') else (800, 1056),
        'subject_input_max_side': 768, 'fabric_crop_box': None,
        'fabric_source_format': 'PNG', 'classified_recovery': True,
        'fabric_type': data.get('fabric_type', 'unspecified'),
        'fabric_region': 'hand_drape', 'fabric_region_selection': 'full_source',
        'prompt_version': 'saree-hand-drape-v1', 'safety_retry_count': 0,
    }
