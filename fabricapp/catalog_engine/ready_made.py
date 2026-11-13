"""Catalog for a photo of a finished garment, independent of garment type."""
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot


def build_config(data, shot, seed):
    box = next(panel.box for panel in layout({}).panels if panel.shot == shot.key)
    width, height = box[2] - box[0], box[3] - box[1]
    if shot.operation == 'crop':
        return {'output_dimensions': (width, height)}
    draft = data.get('options', {}).get('draft_mode', False)
    scale = (768 if draft else 1536) / height
    prompt = (
        f'Create one catalog photograph: {shot.description}. '
        'Image 0 is a blank canvas. Image 2 shows the established model and outfit. '
        'Image 1 is the original finished garment and is the authority for its cut, colour, pattern, '
        'texture, and visible construction. Preserve these details at their original scale. '
        'Image 2 is the sole source of the human wearer, including their skin tone, build, hair '
        'and visible facial features. Treat any mannequin, hanger or person in image 1 as a display prop. '
        'Show the same human wearer from head to shoes, filling the tall frame with a small margin. '
        'Keep the established model, outfit, background and lighting consistent where visible. '
        'For a surface hidden in the source, continue the observed material and cut with simple, '
        'plausible construction. Do not invent decoration, closures, seams or accessories. '
        'No collage, text or watermark.'
    )
    return {'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
            'prompt_version': 'catalog-ready-made-v2', 'safety_retry_count': 0,
            'output_dimensions': (max(256, round(width * scale / 32) * 32), round(height * scale / 32) * 32)}


SHOTS = (
    Shot('front', 'front full-length view', 'pipeline', 'full_body', camera_view='front',
         pipeline_options={'_catalog_config': {
             'framing': ' CATALOG FRAMING: Frame the same human from head to shoes, filling the tall '
                        'frame with a small margin. The garment image supplies clothing only. Ignore any '
                        'mannequin or wearer in that image. Keep the uploaded garment fully visible.',
             'portrait_dimensions': ((256, 768), (512, 1536)),
             'version_suffix': '-catalog-ready-made-v2',
         }}),
    Shot('side', 'side profile showing the complete garment', 'anchor_edit', 'full_body',
         ('front',), scenario='person_pose'),
    Shot('back', 'rear view showing the complete garment from behind with the face out of view',
         'anchor_edit', 'rear_view', ('front',), scenario='person_pose'),
    Shot('upper_detail', 'upper garment crop', 'crop', 'detail_close_up', ('front',),
         source_crop=(.18, .16, .82, .37)),
    Shot('construction_detail', 'side construction crop', 'crop', 'detail_close_up', ('side',),
         source_crop=(.20, .32, .80, .56)),
    Shot('lower_detail', 'lower garment crop', 'crop', 'detail_close_up', ('front',),
         source_crop=(.20, .48, .80, .72)),
)


def layout(_product):
    return Layout('ready-made-3x4-v2', (1800, 2400), (
        Panel('front', (0, 0, 816, 2400)),
        Panel('side', (828, 0, 1308, 1194)),
        Panel('back', (828, 1206, 1308, 2400)),
        Panel('upper_detail', (1320, 0, 1800, 792), 'cover'),
        Panel('construction_detail', (1320, 804, 1800, 1596), 'cover'),
        Panel('lower_detail', (1320, 1608, 1800, 2400), 'cover'),
    ))


DEFINITION = CatalogDefinition('ready_made', 'ready-made-v1', SHOTS, build_config, layout)
