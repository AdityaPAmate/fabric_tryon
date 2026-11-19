"""Reference-based 3:4 Shirt catalog with independent pose and detail shots."""
from PIL import Image

from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours
from fabricapp.ai.fabric.fabric_material import validate_fabric_type
from fabricapp.ai.pipeline.router import PromptRoutingError
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot


REFERENCES = CATALOG_REFERENCE_DIR / 'shirt'
PORTRAITS = {'front', 'close_up', 'back'}
MATERIAL = {
    'unspecified': 'Retain the actual textile surface of image 1.',
    'cotton': 'Use a fine cotton weave with a matte surface and soft diffuse highlights.',
    'silk': 'Use a fine silk surface with restrained lustre, retaining the source colour.',
    'velvet': 'Use a short velvet pile with soft diffuse nap, retaining the source colour.',
}
DETAIL_EDITS = {
    'collar': (
        'Retexture only the existing collar, collar stand and visible upper-chest cloth in image 0 '
        'with the fabric in image 1. Keep the two pointed collar leaves, their opening, both white '
        'buttons, the neck and lower chin exactly where they are. '
        'The photograph ends at the upper chest; preserve this close camera distance.'
    ),
    'cuff': (
        'Retexture only the single vertical sleeve, pointed sleeve placket and broad horizontal '
        'buttoned cuff in image 0 with the fabric in image 1. Keep the single white cuff button, '
        'stitched cuff edges and bare wrist below it at their exact positions. The grey area on '
        'either side is background. Keep this isolated wrist-level close-up, with the sleeve '
        'entering the top edge and the wrist leaving the bottom edge.'
    ),
    'hem': (
        'Retexture only the existing lower shirt panels, front placket and curved stitched hem '
        'in image 0 with the fabric in image 1. Keep the white button, small opening between '
        'the front panels, dark trousers beneath the hem and grey background unchanged. '
        'Preserve this tight waist-level crop, with shirt cloth entering the top edge.'
    ),
}
SHOTS = tuple(
    Shot(key, description, 'template_edit', framing, reference=REFERENCES / filename,
         identity_from='request' if key in PORTRAITS else None,
         scenario='pose_reference' if key in PORTRAITS else 'person_photo')
    for key, filename, framing, description in (
        ('front', '01_front.png', 'full_body', 'the complete front view, from head to shoes'),
        ('close_up', '02_side.png', 'side_portrait', 'the three-quarter side view from head to upper thighs'),
        ('back', '03_back.png', 'rear_portrait', 'the rear view from hair to below the shirt hem'),
        ('collar', 'shirt_collar.png', 'collar_detail', 'the existing collar and upper-chest close-up'),
        ('cuff', 'sleeve.png', 'cuff_detail', 'the existing vertical sleeve, cuff and wrist close-up'),
        ('hem', 'hem.png', 'hem_detail', 'the existing shirt hem and lower placket close-up'),
    )
)


def layout(_product=None):
    return Layout('shirt-six-panel-3x4-v1', (1800, 2400), (
        Panel('front', (0, 0, 740, 2400), 'cover'),
        Panel('close_up', (752, 0, 1300, 1364), 'cover'),
        Panel('back', (752, 1376, 1300, 2400), 'cover'),
        Panel('collar', (1312, 0, 1800, 792), 'cover'),
        Panel('cuff', (1312, 804, 1800, 1596), 'cover'),
        Panel('hem', (1312, 1608, 1800, 2400), 'cover'),
    ))


def output_dimensions(data, shot):
    # The large front keeps 1536px. Smaller side, rear and detail panels use
    # 1024px, with no dependent reposing or pixel-level correction passes.
    limit = 1536 if shot.key == 'front' else 1024
    if data.get('options', {}).get('draft_mode'):
        limit = 768
    with Image.open(shot.reference) as reference:
        width, height = reference.size
    scale = limit / max(width, height)
    return tuple(max(256, round(side * scale / 32) * 32) for side in (width, height))


def condition_fabric(config, data):
    """A compact Shirt-edition contract; numerical sampling remains shared."""
    fabric_type = data.get('fabric_type', 'unspecified')
    error = validate_fabric_type(fabric_type, 'shirt')
    if error:
        raise PromptRoutingError(error)
    profile = measure_fabric_colours(data['fabric_image'],
                                    data.get('options', {}).get('fabric_crop_box'),
                                    palette_size=24, min_coverage=.005)
    colours = profile['colours']
    # One stable measured sample across shots. Names such as "yellow" can
    # reinterpret an olive/green source; the uploaded pixels define its hue.
    colour = (f"The largest sampled cloth colour is {colours[0]['hex']}. " if colours else '')
    distinct = []
    for sample in colours:
        if all(sum((a - b) ** 2 for a, b in zip(sample['rgb'], other['rgb'])) > 24 ** 2
               for other in distinct):
            distinct.append(sample)
        if len(distinct) == 6:
            break
    if len(distinct) > 1:
        colour += 'Keep the sampled colours in their original pattern: ' + ', '.join(
            sample['hex'] for sample in distinct) + '. '
    config = {**config, 'fabric_type': fabric_type, 'fabric_colour_reference': profile}
    config['prompt'] += (' ' + colour + 'Image 1 defines every actual cloth colour, pattern and '
                         'weave. Keep the same diffuse cloth midtone across all views. Copy its '
                         'printed pattern faithfully, keeping photographic glare off the cloth. '
                         'If a reference garment looks faded, use the original swatch colours instead. '
                         + MATERIAL[fabric_type])
    return config


def portrait_treatment(details):
    sleeves = ('Change only the sleeve treatment to evenly rolled fabric folds just below the elbows.'
               if 'folded_sleeves' in details else
               'Keep the reference’s full-length sleeves and flat buttoned wrist cuffs. '
               'The sleeve fabric covers both forearms continuously down to the wrists.')
    hem = ('Tuck the shirt fully into the trousers, with both sides of its hem hidden inside the waistband.'
           if 'tucked' in details else
           'Keep the reference’s continuous untucked hem hanging outside and over the trouser waistband.')
    return sleeves + ' ' + hem


def build_config(data, shot, seed):
    portrait = shot.key in PORTRAITS
    details = data.get('garment_details') or ()
    detail_edit = DETAIL_EDITS.get(shot.key)
    if shot.key == 'cuff' and 'folded_sleeves' in details:
        detail_edit = (
            'Keep the isolated vertical sleeve and wrist-level camera angle of image 0. '
            'Apply image 1’s fabric only to this sleeve and its rolled fabric cuff, with '
            'the selected fold just below the elbow. Keep the exposed forearm and grey '
            'background unchanged. Preserve visible stitching and natural overlapping folds.'
        )
    if shot.key == 'hem' and 'tucked' in details:
        detail_edit = (
            'Keep the waist-level close camera distance of image 0. Apply image 1’s '
            'fabric only to the shirt cloth above the trouser waistband. Show both shirt '
            'fronts entering the waistband evenly, with the bottom hem concealed. '
            'Keep the separate trousers and grey background unchanged.'
        )
    prompt = []
    if portrait:
        prompt.extend([
            f'Edit the reference photograph in image 0: {shot.description}.',
            'Keep its exact pose, crop and shirt construction. Replace only the shirt cloth '
            'with the actual colour, weave and print from image 1, including the collar, '
            'sleeves, cuffs and hem. Preserve buttons, skin and separate clothing.',
        ])
        prompt.append('Keep the reference shirt length and the existing separate white trousers unchanged.')
        if data.get('gender'):
            prompt.append('Subject: ' + _person_description(data['gender'], data.get('body_type')) + '.')
        if shot.key == 'back':
            prompt.append('Keep the head and torso facing away. Preserve the rear yoke, collar and hem. '
                          'Front pockets, front buttons and the front placket stay out of this rear view.')
            if data.get('person_image') or data.get('face_image') or data.get('face_choice'):
                prompt.append('Use image 2 only for visible hair, skin tone and body build. Keep the face hidden.')
        else:
            if data.get('person_image'):
                prompt.append('Image 2 supplies the wearer’s identity, hair, skin tone and body build.')
            elif data.get('face_image') or data.get('face_choice'):
                prompt.append('Image 2 supplies the wearer’s face, hairstyle and skin tone.')
        background = get_background_description(data.get('background'), garment_type='shirt')
        if background:
            prompt.append('Use this scene behind the wearer: ' + background + '.')
        if data.get('additional_style_note'):
            prompt.append(f"Styling: {data['additional_style_note']}. Preserve the reference pose and crop.")
    else:
        prompt.append(detail_edit)
    prompt.append('Keep plain fabric plain. Use soft, even neutral white light, with shallow '
                  'natural seam and fold shadows. Output one photograph.')
    config = {
        'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': output_dimensions(data, shot), 'output_size_multiple': 32,
        'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0,
        **({'subject_input_max_side': 768} if portrait else {}),
    }
    config = condition_fabric(config, data)
    # Colour/material helpers must not have the last word over this shot's camera
    # and construction. A detail edit never describes invisible garment parts.
    if portrait:
        config['prompt'] += (' FINAL REFERENCE LOCK: keep image 0’s camera view and body pose. '
                             + portrait_treatment(details))
        if shot.key == 'back':
            config['prompt'] += ' Keep the face hidden and the back free of front buttons and pockets.'
    else:
        config['prompt'] += (' FINAL REFERENCE LOCK: preserve image 0’s exact close-up geometry. '
                             + detail_edit)
    config['prompt_version'] = f'shirt-editorial-swatch-v4-{shot.key}'
    return config


DEFINITION = CatalogDefinition('shirt', 'editorial-v1', SHOTS, build_config, layout)
