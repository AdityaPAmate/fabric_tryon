"""Six reference photographs for the Plain Kurta catalog."""
from PIL import Image

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.kurta.details import DUPATTA_REMOVE, KURTA_DUPATTA_ADD, SLEEVES_FOLDED
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot

REFERENCES = CATALOG_REFERENCE_DIR / 'kurta' / 'plain'
IDENTITY_VIEWS = {'front', 'side'}
PORTRAITS = IDENTITY_VIEWS | {'back'}

SHOTS = tuple(
    Shot(key, description, 'template_edit', framing, reference=REFERENCES / f'{index:02}_{key}.png',
         identity_from='request' if key in IDENTITY_VIEWS else None,
         scenario='pose_reference' if key in IDENTITY_VIEWS else 'person_photo')
    for index, (key, framing, description) in enumerate((
        ('front', 'full_body', 'front view from head to shoes, with both hands and the entire kurta visible'),
        ('side', 'side_full_body', 'full-length side view matching the angle and stance in image 0'),
        ('back', 'rear_full_body', 'full-length straight rear view, with the head facing away'),
        ('collar', 'collar_detail', 'tight collar and front opening crop, with only the chin at the top edge'),
        ('cuff', 'cuff_detail', 'tight sleeve-end crop showing the cuff and adjacent cloth'),
        ('side_slit', 'side_slit_detail', 'tight lower-side crop showing the hem and its side opening if present'),
    ), start=1)
)


def layout(_product):
    return Layout('kurta-plain-six-panel-3x4-v1', (1800, 2400), (
        Panel('front', (0, 0, 800, 2400), 'cover'),
        Panel('side', (812, 0, 1280, 1194), 'cover'),
        Panel('back', (812, 1206, 1280, 2400), 'cover'),
        Panel('collar', (1292, 0, 1800, 792), 'cover'),
        Panel('cuff', (1292, 804, 1800, 1596), 'cover'),
        Panel('side_slit', (1292, 1608, 1800, 2400), 'cover'),
    ))


def build_config(data, shot, seed):
    ready_made = data.get('garment_image') is not None
    portrait = shot.key in PORTRAITS
    details = data.get('garment_details') or ()
    prompt = [f'Create one Plain Kurta catalog photograph: {shot.description}. '
              'Image 0 sets the camera angle, pose and framing.']
    if ready_made:
        prompt.append('Image 1 shows the finished kurta. Copy its actual cut, length, seams, trim, closures, '
                      'colour, weave and print. Image 0 supplies composition only. Follow the construction '
                      'visible in image 1, including its actual collar and sleeve end. If there is no side '
                      'slit, show the real side seam and hem. Continue the observed cloth and construction '
                      'on unseen areas without inventing decoration. Preserve any matching bottoms in '
                      'image 1; otherwise use simple coordinating trousers in full-length views.')
    else:
        prompt.append('Image 1 is the fabric swatch. Apply its colour, weave and pattern to all visible '
                      'kurta cloth, including collar, placket, cuff, folds and both edges of the slit. '
                      'Keep the Plain Kurta construction in image 0 and preserve plain opaque white '
                      'trousers wherever visible. Keep the swatch pattern scale and repeat consistent.')
        if shot.key in PORTRAITS or shot.key == 'cuff':
            prompt.append(SLEEVES_FOLDED.format(noun='kurta') if 'folded_sleeves' in details else
                          'Keep the full-length sleeves and wrist finish from image 0.')
        if portrait:
            prompt.append(KURTA_DUPATTA_ADD if 'with_dupatta' in details else DUPATTA_REMOVE)

    if portrait:
        if shot.key in IDENTITY_VIEWS and data.get('person_image'):
            prompt.append('Image 2 supplies the subject’s face, hairstyle and body build. '
                          'Dress that subject in the requested kurta, in the pose in image 0.')
        elif data.get('gender'):
            prompt.append('Subject: ' + _person_description(data['gender'], data.get('body_type')) + '.')
            if shot.key in IDENTITY_VIEWS and (data.get('face_image') or data.get('face_choice')):
                prompt.append('Image 2 supplies face and hairstyle. Use the requested body build.')
        if shot.key == 'back':
            prompt.append('Keep the face out of view and the back of the kurta clearly visible.')
        background = get_background_description(data.get('background'))
        prompt.append(f'Use {background} behind the subject.' if background else 'Keep the studio setting of image 0.')
        if data.get('additional_style_note'):
            prompt.append(f"Styling direction: {data['additional_style_note']}. Keep the garment source and framing.")
    else:
        prompt.append('Keep the exact close-up and studio setting. Keep the eyes and full face outside the frame.')

    prompt.append('Use soft neutral lighting and keep the true garment colours. '
                  'Output one photograph with no text, watermark or collage.')
    with Image.open(shot.reference) as reference:
        width, height = reference.size
    max_side = 768 if data.get('options', {}).get('draft_mode') else 1536
    scale = max_side / max(width, height)
    config = {'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
              'output_dimensions': tuple(max(256, round(side * scale / 32) * 32) for side in (width, height)),
              'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0}
    if not ready_made:
        config = apply_fabric_conditioning(config, data, 'kurta', 'plain', match_pattern_colours=True)
    config['prompt_version'] = f'kurta-plain-catalog-v1-{shot.key}'
    return config


DEFINITION = CatalogDefinition('kurta', 'plain-v1', SHOTS, build_config, layout)
