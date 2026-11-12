"""Catalog for a photo of a finished garment, independent of garment type."""
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot


def build_config(data, shot, seed):
    reference = ('Image 0 is a blank canvas. Image 2 shows the established model and outfit. '
                 if shot.scenario == 'person_pose' else 'Image 0 shows the established model and outfit. ')
    prompt = (
        f'Create one catalog photograph: {shot.description}. {reference}'
        'Image 1 is the original finished garment and is the authority for its cut, colour, pattern, '
        'texture, and visible construction. Preserve these details at their original scale. '
        'Keep the established model, outfit, background and lighting consistent where visible. '
        'For a surface hidden in the source, continue the observed material and cut with simple, '
        'plausible construction. Do not invent decoration, closures, seams or accessories. '
        'No collage, text or watermark.'
    )
    return {'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
            'prompt_version': 'catalog-ready-made-v1', 'safety_retry_count': 0}


SHOTS = (
    Shot('front', 'front full-length view', 'pipeline', 'full_body', camera_view='front',
         pipeline_options={'_catalog_config': {
             'framing': ' CATALOG FRAMING: Center the model in a portrait frame and keep the entire '
                        'uploaded garment visible, with room around its outline.',
             'version_suffix': '-catalog-ready-made-v1',
         }}),
    Shot('side', 'side profile showing the complete garment', 'anchor_edit', 'full_body',
         ('front',), scenario='person_pose'),
    Shot('back', 'rear view showing the complete garment from behind with the face out of view',
         'anchor_edit', 'rear_view', ('front',), scenario='person_pose'),
    Shot('upper_detail', 'tight crop of a visible feature near the top of the supplied garment, '
         'such as its neckline, waistband or upper edge, with the face outside the frame',
         'anchor_edit', 'detail_close_up', ('front',)),
    Shot('construction_detail', 'tight crop of a visible construction or textile detail on the '
         'body of the supplied garment, with the face outside the frame',
         'anchor_edit', 'detail_close_up', ('front',)),
    Shot('lower_detail', 'tight crop of the supplied garment’s lower edge or hem, '
         'with the face outside the frame', 'anchor_edit', 'detail_close_up', ('front',)),
)


def layout(_product):
    return Layout('ready-made-3x4-v1', (1800, 2400), (
        Panel('front', (0, 0, 816, 2400)),
        Panel('side', (828, 0, 1308, 1194)),
        Panel('back', (828, 1206, 1308, 2400)),
        Panel('upper_detail', (1320, 0, 1800, 792), 'cover'),
        Panel('construction_detail', (1320, 804, 1800, 1596), 'cover'),
        Panel('lower_detail', (1320, 1608, 1800, 2400), 'cover'),
    ))


DEFINITION = CatalogDefinition('ready_made', 'ready-made-v1', SHOTS, build_config, layout)
