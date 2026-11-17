"""Six-panel Business Blazer catalog for swatches and finished jackets."""
from dataclasses import replace

from PIL import Image

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.blazer.catalog.colour import align_portrait_colour, jacket_midtone, profile_midtone
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
from fabricapp.ai.scene.backgrounds import BACKGROUND_DESCRIPTIONS
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot


REFERENCES = CATALOG_REFERENCE_DIR / 'blazer' / 'business'
PORTRAITS = (
    Shot('front', 'full-length front view', 'template_edit', 'full_body',
         reference=REFERENCES / '01_front.png', identity_from='request', scenario='pose_reference'),
    Shot('side', 'full-length three-quarter side view', 'template_edit', 'side_full_body',
         reference=REFERENCES / '02_side.png', identity_from='request', scenario='pose_reference'),
    Shot('back', 'full-length rear view with the face out of frame', 'template_edit', 'rear_full_body',
         reference=REFERENCES / '03_back.png', identity_from='request', scenario='pose_reference'),
)
DETAILS = (
    ('lapel', 'lapel and upper chest', 'front', (.24, .17, .83, .36)),
    ('cuff', 'sleeve and cuff', 'side', (.44, .38, .77, .52)),
    ('pocket', 'lower jacket pocket', 'side', (.35, .335, .62, .463)),
)


def layout(_product):
    return Layout('blazer-business-six-panel-3x4-v1', (1800, 2400), (
        Panel('front', (0, 0, 800, 2400), 'cover'),
        Panel('side', (812, 0, 1276, 1194), 'cover'),
        Panel('back', (812, 1206, 1276, 2400), 'cover'),
        Panel('lapel', (1288, 0, 1800, 940), 'cover'),
        Panel('cuff', (1288, 952, 1800, 1592), 'cover'),
        Panel('pocket', (1288, 1604, 1800, 2400), 'cover'),
    ))


def output_dimensions(data, shot):
    limit = 768 if data.get('options', {}).get('draft_mode') else 1536
    if shot.operation == 'crop':
        left, top, right, bottom = next(panel.box for panel in layout({}).panels if panel.shot == shot.key)
        width, height = right - left, bottom - top
    else:
        with Image.open(shot.reference) as image:
            width, height = image.size
    scale = limit / max(width, height)
    return tuple(max(256, round(side * scale / 32) * 32) for side in (width, height))


def build_config(data, shot, seed):
    config = {'output_dimensions': output_dimensions(data, shot)}
    if shot.operation == 'crop':
        return config

    ready = data.get('garment_image') is not None
    prompt = [
        f'Edit image 0 in place to make a Business Blazer catalog photograph: {shot.description}.',
        'Keep the pose, camera angle, subject size and complete head-to-shoes framing of image 0.',
    ]
    if ready:
        prompt.append(
            'Image 1 is the finished blazer. Put that exact jacket on the wearer, keeping its cut, '
            'lapels, sleeves, buttons, pockets, stitching, textile, pattern and colour. '
            'Ignore the display mannequin, hanger, wearer and scene of image 1. Use its matching '
            'trousers if they are part of the uploaded outfit. For unseen jacket surfaces continue '
            'the same cloth and use plausible tailoring based on the visible construction.'
        )
        if shot.identity_from == 'front':
            prompt.append(
                'Image 2 shows the established wearer and outfit in the front view. Match its wearer, '
                'body build, jacket midtone, shirt, trousers and shoes while keeping the pose of image 0.'
            )
    else:
        prompt.append(
            'Image 1 is the only cloth source. Replace all blazer cloth including the lapels, sleeves, '
            'cuffs and pocket flaps with this exact fabric. Keep the single-breasted business cut '
            'and the same tailoring as image 0. Preserve weave, print proportions and chroma. '
            'The shirt, tie, pocket square, trousers, shoes, buttons and skin retain their own materials.'
        )
    if shot.key == 'back':
        prompt.append('Show the back of the blazer and both sleeves. Keep the face turned away.')
    if data.get('gender'):
        prompt.append('Subject: ' + _person_description(data['gender'], data.get('body_type')) + '.')
    if shot.identity_from == 'request' and shot.key == 'back' and (
        data.get('person_image') or data.get('face_choice') or data.get('face_image')
    ):
        prompt.append('Match the wearer’s visible hair and skin tone to image 2 and keep the face hidden.')
        if data.get('person_image'):
            prompt.append('Keep the body build of the person in image 2.')
    elif shot.identity_from == 'request' and data.get('person_image'):
        prompt.append('Image 2 supplies the wearer’s identity and build. Keep the catalog pose in image 0.')
    elif shot.identity_from == 'request' and (data.get('face_choice') or data.get('face_image')):
        prompt.append('Use the face, hair and skin tone of image 2 with the requested body build.')
    background = data.get('background')
    if background:
        prompt.append(f'Background: {BACKGROUND_DESCRIPTIONS[background]}')
    if data.get('additional_style_note'):
        prompt.append(f"Styling: {data['additional_style_note']}. Preserve the jacket, fabric and framing.")
    prompt.append(
        'Use soft neutral daylight with a fixed white balance and consistent cloth midtones. '
        'Keep natural seam and fold shadows and avoid coloured reflections or overexposed cloth. '
        'Output one photograph.'
    )
    config.update(prompt=' '.join(prompt), seed=seed, guidance=data.get('guidance', 7),
                  fabric_source_format='PNG', classified_recovery=True, safety_retry_count=0)
    if not ready:
        config = apply_fabric_conditioning(config, data, 'blazer', 'business',
                                           match_pattern_colours=True, lead_with_edit=True)
        target = profile_midtone(config['fabric_colour_reference'])
        if target is not None:
            shade = '#%02X%02X%02X' % tuple(round(float(channel)) for channel in target)
            config['prompt'] += f' Match the swatch jacket midtone {shade} in the softly lit cloth.'
    config['prompt_version'] = f'blazer-business-catalog-{"ready" if ready else "swatch"}-v1-{shot.key}'
    return config


def finish_shot(data, shot, generation):
    if shot.operation != 'template_edit':
        return generation
    return align_portrait_colour(generation, shot.key, jacket_midtone(data))


def validate_request(data):
    crop = data.get('options', {}).get('fabric_crop_box')
    if crop:
        source = data['fabric_image']
        position = source.tell()
        try:
            source.seek(0)
            with Image.open(source) as image:
                if crop[2] > image.width or crop[3] > image.height:
                    return {'options': {'fabric_crop_box': 'Choose a crop inside the original fabric image.'}}
        finally:
            source.seek(position)
    return None


SWATCH_SHOTS = tuple(
    Shot(key, description, 'swatch_composite', f'{key}_detail',
         reference=REFERENCES / f'{index:02}_{key}.png',
         reference_mask=REFERENCES / f'{index:02}_{key}_mask.png',
         swatch_original_orientation=True,
         composite_relief=REFERENCES / f'{index:02}_{key}_relief.png' if key != 'cuff' else None)
    for index, (key, description, _, _) in enumerate(DETAILS, 4)
)
READY_SHOTS = tuple(
    Shot(key, description, 'crop', f'{key}_detail', dependencies=(source,), source_crop=crop)
    for key, description, source, crop in DETAILS
)
DEFINITION = CatalogDefinition('blazer', 'business-v1', PORTRAITS + SWATCH_SHOTS, build_config,
                               layout, validate_request=validate_request, finish_shot=finish_shot)
READY_PORTRAITS = (PORTRAITS[0],) + tuple(
    replace(shot, dependencies=('front',), identity_from='front') for shot in PORTRAITS[1:]
)
READY_MADE_DEFINITION = replace(DEFINITION, shots=READY_PORTRAITS + READY_SHOTS, finish_shot=None)
