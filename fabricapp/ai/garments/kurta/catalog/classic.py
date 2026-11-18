"""Compatibility catalog for this garment’s classic-v1 edition."""
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.ai.scene.garment_lighting import append_garment_lighting
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot
from fabricapp.catalog_engine.legacy import classic_layout


LIGHTING = (
    'FINAL GARMENT LIGHTING: use a broad, soft, colour-neutral frontal key light and gentle fill '
    'from the opposite side. Balance illumination across the kurta or sherwani. Keep smooth '
    'transitions from the chest or central panels to the sides. Use gentle contact shadows beneath '
    'collars, lapels, overlaps and seams, and soften deep shadows at elbows, knees and existing '
    'folds. Retain subtle highlights, visible weave and natural three-dimensional fabric depth. Keep '
    'diffuse fabric midtones faithful to image 1 in hue, saturation and lightness. Do not brighten '
    'dark fabric into a pale shade, grey out saturated fabric, clip light fabric to pure white, or '
    'tint the cloth with background colours. Keep printed motifs distinct with their original colour '
    'contrast. Keep scene lighting coherent while using neutral fill to protect garment colour. '
    "Preserve the selected material's matte, glossy or plush surface response. "
)


def build_config(data, shot, seed):
    prompt = (f'Create exactly ONE NEW photograph: {shot.description}. '
              + ('Image 0 is a blank canvas. Image 2 is the approved front image. '
                 if shot.scenario == 'person_pose' else 'Image 0 is the approved front image. ')
              + 'Keep the SAME person, body build, finished outfit, separate clothing, '
              'construction, colours and fabric pattern scale. Image 1 supplies the original fabric. '
              'Change only the requested camera and framing. No collage, text or watermark. ')
    background = get_background_description(data.get('background'), garment_type=data['garment_type'])
    prompt += 'BACKGROUND: ' + (background or 'retain the same setting as the front image') + '. '
    config = {'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
              'prompt_version': 'catalog-classic-v3', 'safety_retry_count': 0}
    config = apply_fabric_conditioning(config, data, data['garment_type'], data.get('garment_style'))
    config['prompt'] += ' FINAL CAMERA REQUIREMENT: ' + shot.description + '. '
    return append_garment_lighting(config, LIGHTING, '-lighting-v1')


DETAILS = (
    ('neckline', 'neckline'),
    ('cuff', 'sleeve end'),
    ('hem', 'lower garment hem'),
)

SHOTS = (
    Shot('front', 'front full-body view', 'pipeline', 'full_body', camera_view='front',
         pipeline_options={'_catalog_config': {'lighting': (LIGHTING, '-lighting-v1')}}),
    Shot('three_quarter',
         'FRONT THREE-QUARTER close-up: camera 45 degrees around the person; '
         'show front and side from head to garment hem',
         'anchor_edit', 'three_quarter_close_up', ('front',), scenario='person_pose'),
    Shot('back',
         'REAR CLOSE-UP product photograph: back of garment from shoulders to its hem, excluding face, legs and shoes',
         'anchor_edit', 'rear_close_up', ('front',)),
) + tuple(
    Shot(key, 'tight product detail photograph of the ' + part + ' only', 'anchor_edit',
         'detail_close_up', ('front',))
    for key, part in DETAILS
)


def layout(_product):
    return classic_layout(SHOTS)


DEFINITION = CatalogDefinition('kurta', 'classic-v1', SHOTS, build_config, layout)
