"""Six reference photographs for the Plain Kurta catalog."""
from PIL import Image

from fabricapp.ai.fabric.body_region import select_body_fabric_region
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.kurta.details import DUPATTA_REMOVE, KURTA_DUPATTA_ADD, SLEEVES_FOLDED
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot

REFERENCES = CATALOG_REFERENCE_DIR / 'kurta' / 'plain'
IDENTITY_VIEWS = {'front', 'side'}
PORTRAITS = IDENTITY_VIEWS | {'back'}
DETAIL_FRAMING = {
    'collar': (
        'Match the tight crop in image 0: the bottom of the chin at the top edge, a little neck, '
        'the collar and the first buttons. The cloth continues through the bottom and side edges. '
        'Keep the eyes, sleeves, hands, waist, hem and trousers out of the frame.'
    ),
    'cuff': (
        'Match the diagonal sleeve end in image 0. Show a single cuff and the small patch of wrist '
        'immediately below it. Keep the collar, full torso, head, hands and trousers out of the frame.'
    ),
    'side_slit': (
        'Match the tight lower side view in image 0: show the two hem edges around the side opening '
        'and the small visible area behind it. The top edge cuts through the lower kurta cloth. '
        'Keep the front opening, waist, arms, hands, neck, head and feet out of the frame.'
    ),
}

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
    return Layout('kurta-plain-six-panel-3x4-v2', (1800, 2400), (
        Panel('front', (0, 0, 800, 2400)),
        Panel('side', (812, 0, 1280, 1194)),
        Panel('back', (812, 1206, 1280, 2400)),
        Panel('collar', (1292, 0, 1800, 792)),
        Panel('cuff', (1292, 804, 1800, 1596)),
        Panel('side_slit', (1292, 1608, 1800, 2400)),
    ))


def build_config(data, shot, seed):
    ready_made = data.get('garment_image') is not None
    portrait = shot.key in PORTRAITS
    details = data.get('garment_details') or ()
    prompt = [f'Edit image 0 in place for this Plain Kurta catalog view: {shot.description}. '
              'Keep its camera angle, framing, perspective and subject scale.']
    if ready_made:
        prompt.append('Image 1 shows the finished kurta. Copy its actual cut, length, seams, trim, closures, '
                      'colour, weave and print. Image 0 supplies composition only. Follow the construction '
                      'visible in image 1, including its actual collar and sleeve end. If there is no side '
                      'slit, show the real side seam and hem at the same scale. Continue the observed cloth and construction '
                      'on unseen areas without inventing decoration. Preserve any matching bottoms in '
                      'image 1; otherwise use simple coordinating trousers in full-length views.')
    else:
        prompt.append('Image 1 is the fabric swatch. Replace every visible kurta cloth pixel with its '
                      'colour, weave and pattern, following the existing cloth volume and seam directions. '
                      'Keep the garment outline, closures, stitching, skin and studio background in place. '
                      'Where visible, preserve the plain white trousers. Preserve the source pattern scale '
                      'and repeat. Plain cloth stays plain, including through folds. Do not turn wrinkles, '
                      'selvedges or weave texture into stripes, checks, piping or decorative seams.')
        if shot.key in PORTRAITS or shot.key == 'side_slit':
            prompt.append('When the swatch has a distinct decorative border, place it only at the lower hem. '
                          'Keep the body pattern continuous above it. Use a plain stitched hem when the source has no border.')
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
        prompt.append('Keep natural head, torso and leg proportions and the head-to-shoe framing of image 0. '
                      'Keep the shoulders and garment width natural in the narrow portrait frame.')
        if shot.key == 'back':
            prompt.append('Keep the face out of view and the back clearly visible. Keep the uninterrupted '
                          'back panel free of a front placket, added seams or bands.')
        background = get_background_description(data.get('background'))
        prompt.append(f'Use {background} behind the subject.' if background else 'Keep the studio setting of image 0.')
        if data.get('additional_style_note'):
            prompt.append(f"Styling direction: {data['additional_style_note']}. Keep the garment source and framing.")
    else:
        framing = DETAIL_FRAMING[shot.key]
        if ready_made and shot.key == 'side_slit':
            framing = ('Match the tight lower side view in image 0. Show the real side seam and hem, '
                       'including the opening only if present. Keep the waist, arms, face and feet out of frame.')
        prompt.append(framing)

    prompt.append('Under soft neutral lighting, match the source hue, saturation and lightness in the '
                  'garment midtones. Keep pale colours pale and dark colours dark. Keep scene reflections '
                  'off the cloth. Preserve local fold shadows without boosting vibrance, warmth or contrast. '
                  'Output one photograph with no text, watermark or collage.')
    with Image.open(shot.reference) as reference:
        width, height = reference.size
    max_side = 768 if data.get('options', {}).get('draft_mode') else 1536
    scale = max_side / max(width, height)
    config = {'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
              'output_dimensions': tuple(max(256, round(side * scale / 32) * 32) for side in (width, height)),
              'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0}
    if not ready_made:
        crop, selection = select_body_fabric_region(data)
        options = data.get('options', {})
        body_detail = shot.key in ('collar', 'cuff')
        context = {**data, 'options': {**options, 'fabric_crop_box': crop}}
        if not portrait:
            context['garment_details'] = ()
        if body_detail:
            config.update(fabric_crop_box=crop, fabric_region='body', fabric_region_selection=selection)
            config['prompt'] += ' Use the body cloth at the collar or cuff; keep decorative hem borders outside this crop.'
        elif selection == 'detected_body_crop':
            config['prompt'] += ' The measured palette describes the main cloth; use image 1 for any real hem trim.'
        # Use the standard midtone anchor for single-family swatches and a
        # sampled body palette for multi-colour and bordered fabrics.
        conditioned = apply_fabric_conditioning(config, context, 'kurta', 'plain')
        if selection == 'detected_body_crop' or 'fabric_colour_reference' not in conditioned:
            conditioned = apply_fabric_conditioning(config, context, 'kurta', 'plain', match_pattern_colours=True)
        config = conditioned
    config['prompt_version'] = f'kurta-plain-catalog-v2-{shot.key}'
    return config


DEFINITION = CatalogDefinition('kurta', 'plain-v1', SHOTS, build_config, layout)
