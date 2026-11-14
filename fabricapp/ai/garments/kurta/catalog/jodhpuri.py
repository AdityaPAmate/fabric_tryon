"""Jodhpuri bandhgala catalog with separate collar, cuff and pocket photographs."""
from dataclasses import replace

from fabricapp.ai.fabric.body_region import select_body_fabric_region
from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.kurta.catalog import plain
from fabricapp.ai.garments.kurta.catalog.jodhpuri_colour import align_jacket_colour
from fabricapp.ai.garments.kurta.catalog.sherwani import SCENERY, WHITE_LIGHT
from fabricapp.ai.garments.kurta.catalog.sherwani_colour import solid_swatch_rgb
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot

REFERENCES = plain.REFERENCES.parent / 'jodhpuri'
FRAMING = {
    'front': 'Keep the head-to-shoes front view and the fitted, hip-length bandhgala jacket.',
    'side': 'Keep the head-to-shoes side angle and show the short tailored jacket hem above the trousers.',
    'back': 'Keep the head-to-shoes rear view. Show the uninterrupted jacket back and rear collar with the face out of view.',
    'collar': 'Show the chin at the top edge and the upright bandhgala collar and upper closure below. Keep the chest extending past the lower edge.',
    'cuff': 'Keep one sleeve running diagonally from upper right to lower left. Show the existing cuff edge and the small bare wrist at lower left.',
    'pocket': 'Keep a tight crop of the breast welt pocket and its welt stitching, with jacket cloth filling the frame and the sleeve at the right edge.',
}
READY_CROPS = {
    'collar': ('front', (.26, .15, .74, .31)),
    'cuff': ('side', (.20, .31, .73, .47)),
    'pocket': ('front', (.48, .22, .84, .39)),
}
SWATCH_DETAILS = {
    'collar': 'Cover the collar, placket and visible chest with source cloth. Preserve the visible reference buttons and stand collar shape.',
    'cuff': 'Cover the sleeve and cuff with source cloth up to the stitched edge. Preserve the three metal buttons, bare wrist and soft contact shadow.',
    'pocket': 'Apply source cloth to the jacket and pocket welt. Keep the separate folded pocket square, welt opening and stitching visible.',
}

SHOTS = tuple(
    Shot(key, description, 'template_edit', framing, reference=REFERENCES / f'{index:02}_{key}.png',
         identity_from='request' if key in plain.IDENTITY_VIEWS else None,
         scenario='pose_reference' if key in plain.IDENTITY_VIEWS else 'person_photo')
    for index, (key, framing, description) in enumerate((
        ('front', 'full_body', 'full-length front view'),
        ('side', 'side_full_body', 'full-length side view'),
        ('back', 'rear_full_body', 'full-length rear view'),
        ('collar', 'collar_detail', 'bandhgala collar and upper closure'),
        ('cuff', 'cuff_detail', 'diagonal sleeve and cuff'),
        ('pocket', 'pocket_detail', 'breast welt pocket'),
    ), start=1)
)


def layout(_product):
    return Layout('jodhpuri-six-panel-3x4-v1', (1800, 2400), (
        Panel('front', (0, 0, 800, 2400), 'cover'),
        Panel('side', (812, 0, 1252, 1194), 'cover'),
        Panel('back', (812, 1206, 1252, 2400), 'cover'),
        Panel('collar', (1264, 0, 1800, 916), 'cover'),
        Panel('cuff', (1264, 928, 1800, 1464), 'cover'),
        Panel('pocket', (1264, 1476, 1800, 2400), 'cover'),
    ))


def build_config(data, shot, seed):
    ready = data.get('garment_image') is not None
    portrait = shot.key in plain.PORTRAITS
    prompt = ['Edit image 0 in place. Keep its exact camera angle, framing and subject scale.', FRAMING[shot.key]]
    if ready and portrait:
        prompt.append('Image 1 supplies the finished Jodhpuri jacket and its actual cut, cloth, fasteners and trim. '
                      'Dress the person in that garment. Use any matching trousers supplied with it, or plain coordinating '
                      'trousers and shoes. The mannequin, hanger and original wearer are display context only.')
    elif ready:
        prompt.append('Image 1 is a crop of the jacket as worn in this catalog. Copy its cloth, colour and visible '
                      'construction. Keep the close-up and lighting from image 0. Preserve buttons, a pocket opening '
                      'or a pocket square only where supported by the garment image.')
    else:
        prompt.append('Image 1 is the swatch and the only authority for jacket colour, weave, pattern and embroidery. '
                      'Replace the template textile completely. Continue the supplied pattern across folds at its original '
                      'scale. A plain swatch stays plain. Cloth ends at the garment edge, leaving skin and scenery clear.')
        if portrait:
            prompt.append('Keep the reference jacket ending at the hips with the separate plain trousers as shown in image 0. '
                          'Keep the trouser fabric free of jacket motifs. Keep the stand collar, tailored shoulders and clean hem.')
            if shot.key != 'back':
                prompt.append('Keep the visible reference front buttons and separate pocket square.')
            if 'with_dupatta' in (data.get('garment_details') or ()):
                prompt.append('Include the selected lightweight matching stole, draped clear of the collar and breast pocket.')
        else:
            prompt.append(SWATCH_DETAILS[shot.key])

    if shot.key == 'back':
        prompt.append('The rear jacket and rear collar are continuous cloth without buttons, buttonholes or a front placket.')
        if not ready:
            prompt.append('Carry the same base shade and motif density across the back and both sleeves. '
                          'Keep the supplied print visible in shadows and along both shoulders. Preserve genuine '
                          'light motifs from the swatch and avoid pale patches from glare or scene lighting.')
    if shot.key == 'cuff':
        prompt.append('The diagonal sleeve and wrist fill the frame. Keep the uncovered studio area light grey, '
                      'the cloth edge natural and softly shadowed, and the sleeve evenly exposed without white glare.')
    elif shot.key == 'pocket':
        prompt.append('The frame shows only the jacket chest and welt detail. Keep the face, hands, trousers and lower hem outside the crop.')

    if portrait:
        if shot.key in plain.IDENTITY_VIEWS and data.get('person_image'):
            prompt.append('Image 2 supplies the wearer’s face, hairstyle, facial hair, skin tone and build. Keep the pose from image 0.')
        elif data.get('gender'):
            prompt.append('Subject: ' + _person_description(data['gender'], data.get('body_type')) + '.')
            if shot.key in plain.IDENTITY_VIEWS and (data.get('face_image') or data.get('face_choice')):
                prompt.append('Copy the face and hairstyle from image 2 while keeping the requested body build.')
        scene = SCENERY.get(data.get('background'))
        if scene:
            prompt.append(f'Use {scene} behind the subject.')
        if data.get('additional_style_note'):
            prompt.append(f"Styling direction: {data['additional_style_note']}. Preserve the garment and camera framing.")

    config = {'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
              'output_dimensions': plain.reference_output_dimensions(data, shot),
              'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0}
    if not ready:
        crop, selection = select_body_fabric_region(data)
        options = data.get('options', {})
        context = {**data, 'options': {**options, 'fabric_crop_box': crop}, 'garment_details': ()}
        if not portrait:
            config.update(fabric_crop_box=crop, fabric_region='body', fabric_region_selection=selection)
        config = apply_fabric_conditioning(config, context, 'kurta', 'jodhpuri',
                                           match_pattern_colours=True, lead_with_edit=True)
        target = swatch_colour(data)
        if target is not None:
            shade = '#%02X%02X%02X' % tuple(round(float(component)) for component in target)
            config['prompt'] += f' Match the common jacket midtone {shade} across views.'
    config['prompt'] += WHITE_LIGHT + ' Output one photograph.'
    version = 'ready-v1' if ready else ('swatch-v3' if shot.key == 'back' else 'swatch-v2')
    config['prompt_version'] = f'jodhpuri-catalog-{version}-{shot.key}'
    return config


def swatch_colour(data):
    crop, _ = select_body_fabric_region(data)
    return solid_swatch_rgb(measure_fabric_colours(data['fabric_image'], crop, palette_size=16, min_coverage=.015))


def finish_shot(data, shot, generation):
    if shot.operation == 'swatch_composite':
        return generation
    return align_jacket_colour(generation, shot.key, swatch_colour(data))


SWATCH_SHOTS = SHOTS[:-1] + (
    replace(SHOTS[-1], operation='swatch_composite', reference_mask=REFERENCES / '06_pocket_mask.png',
            swatch_body_only=True, natural_swatch_shading=True,
            composite_relief=REFERENCES / '06_pocket_relief.png'),
)
DEFINITION = CatalogDefinition('kurta', 'jodhpuri-v1', SWATCH_SHOTS, build_config, layout,
                               finish_shot=finish_shot, swatch_colour=swatch_colour)
READY_MADE_DEFINITION = replace(DEFINITION, shots=SHOTS[:3] + tuple(
    replace(shot, dependencies=(anchor,), garment_from=anchor, source_crop=crop)
    for shot in SHOTS[3:]
    for anchor, crop in (READY_CROPS[shot.key],)
), finish_shot=None, swatch_colour=None)
