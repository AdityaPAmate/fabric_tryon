"""Six-panel Business Blazer catalog for swatches and finished jackets."""
from dataclasses import replace

from PIL import Image

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.fabric.body_region import select_body_fabric_region
from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours
from fabricapp.ai.garments.blazer.catalog.colour import align_portrait_colour, profile_midtone
from fabricapp.ai.garments.blazer.catalog.business_details import (
    TROUSER_REGIONS, clean_trouser_motifs, colour_lapel_tie, colour_portrait_tie,
)
from fabricapp.ai.garments.kurta.catalog.sherwani import SCENERY, WHITE_LIGHT
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
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
    if shot.key == 'back':
        prompt.insert(0, 'CAMERA PRIORITY: keep the straight back view from image 0. Show the back of '
                         'the head and both rear shoulders. The face, jacket front and shirt opening are out of sight.')
    elif shot.key == 'side':
        prompt.insert(0, 'CAMERA PRIORITY: keep the three-quarter side angle from image 0. Maintain the '
                         'same side shoulder, side seam and trouser-pocket pose.')
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
            'Keep the shirt, pocket square, shoes, buttons and skin in their own materials.'
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
    background = SCENERY.get(data.get('background'))
    if background:
        prompt.append(f'Use {background} behind the wearer. Light the outfit like a softly lit studio portrait.')
    if data.get('additional_style_note'):
        prompt.append(f"Styling: {data['additional_style_note']}. Preserve the jacket, fabric and framing.")
    prompt.append(WHITE_LIGHT + ' Keep the shoulders, sleeves and trousers evenly lit. Output one photograph.')
    config.update(prompt=' '.join(prompt), seed=seed, guidance=data.get('guidance', 7),
                  fabric_source_format='PNG', classified_recovery=True, safety_retry_count=0)
    if not ready:
        config = apply_fabric_conditioning(config, data, 'blazer', 'business',
                                           match_pattern_colours=True, lead_with_edit=True)
        profile = business_profile(data)
        target = business_base_colour(profile)
        if target is not None:
            shade = '#%02X%02X%02X' % tuple(round(float(channel)) for channel in target)
            outfit = (
                f'GARMENT COLOUR PRIORITY: the trousers are solid {shade} from waist to hem, including '
                'both legs. Replace the original reference trousers with plain dyed cloth in that colour. '
                'Use image 1 only on the jacket itself. Keep all prints, embroidery and sleeve trim above '
                'the jacket hem. The trousers have no artwork, stripes, checks or borders. '
            )
            if shot.key != 'back':
                outfit += f'The plain solid tie and plain solid trousers share the swatch base {shade}. '
            config['prompt'] = outfit + config['prompt']
            config['prompt'] += f' Match the swatch jacket midtone {shade} under diffuse white light.'
    config['prompt_version'] = f'blazer-business-catalog-{"ready" if ready else "swatch"}-v2-{shot.key}'
    return config


def business_profile(data):
    crop, _ = select_body_fabric_region(data)
    return measure_fabric_colours(data['fabric_image'], crop, palette_size=24, min_coverage=.005)


def business_base_colour(profile):
    target = profile_midtone(profile)
    if target is None and profile['colours']:
        return profile['colours'][0]['rgb']
    return target


def business_midtone(data):
    return profile_midtone(business_profile(data))


def finish_shot(data, shot, generation):
    if shot.key == 'lapel':
        return colour_lapel_tie(generation, REFERENCES / '04_lapel_tie_mask.png',
                               business_base_colour(business_profile(data)))
    if shot.operation != 'template_edit':
        return generation
    profile = business_profile(data)
    generation = align_portrait_colour(generation, shot.key, profile_midtone(profile),
                                       soft_edges=True, local_exposure=True)
    target = business_base_colour(profile)
    generation = align_portrait_colour(generation, 'trousers', target,
                                       region=TROUSER_REGIONS[shot.key], soft_edges=True, local_exposure=True)
    generation = clean_trouser_motifs(generation, shot.key, target)
    return colour_portrait_tie(generation, shot.key, target)


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
         swatch_body_only=True, natural_swatch_shading=True,
         composite_relief=REFERENCES / f'{index:02}_{key}_relief.png')
    for index, (key, description, _, _) in enumerate(DETAILS, 4)
)
READY_SHOTS = tuple(
    Shot(key, description, 'crop', f'{key}_detail', dependencies=(source,), source_crop=crop)
    for key, description, source, crop in DETAILS
)
DEFINITION = CatalogDefinition('blazer', 'business-v1', PORTRAITS + SWATCH_SHOTS, build_config,
                               layout, validate_request=validate_request, finish_shot=finish_shot,
                               swatch_colour=business_midtone)
READY_PORTRAITS = (PORTRAITS[0],) + tuple(
    replace(shot, dependencies=('front',), identity_from='front') for shot in PORTRAITS[1:]
)
READY_MADE_DEFINITION = replace(DEFINITION, shots=READY_PORTRAITS + READY_SHOTS, finish_shot=None,
                                swatch_colour=None)
