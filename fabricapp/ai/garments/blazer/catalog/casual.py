"""Casual Blazer catalog with one model reference per photograph."""
from dataclasses import replace

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours
from fabricapp.ai.garments.blazer.catalog.business import (
    REFERENCES as BUSINESS_REFERENCES, has_uniform_swatch, layout as blazer_layout, output_dimensions, validate_request,
)
from fabricapp.ai.garments.blazer.catalog.colour import align_portrait_colour, jacket_midtone, profile_midtone
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
from fabricapp.ai.garments.kurta.catalog.sherwani import SCENERY
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot


REFERENCES = CATALOG_REFERENCE_DIR / 'blazer' / 'casual'
VIEWS = (
    ('front', 'full_body', 'full-length front view from head to sneakers'),
    ('side', 'side_full_body', 'full-length three-quarter side view from head to sneakers'),
    ('back', 'rear_full_body', 'full-length rear view from head to sneakers with the face hidden'),
    ('lapel', 'lapel_detail', 'close-up of the notch lapel, jacket chest and separate crew-neck shirt'),
    ('cuff', 'cuff_detail', 'diagonal sleeve close-up with cuff buttons and a small bare wrist'),
    ('pocket', 'pocket_detail', 'tight lower jacket pocket close-up showing its flap, opening and stitching'),
)
PORTRAIT_VIEWS = {'front', 'side', 'back'}
DETAIL_FRAMING = {
    'lapel': 'Keep the chin and neck at the top edge, the notch lapel and chest in frame, '
             'and the dark crew-neck shirt visible inside the opening. The eyes, hands and waist are outside the frame.',
    'cuff': 'Keep one diagonal sleeve, the row of cuff buttons and a small bare wrist at the left edge. '
            'Preserve the plain studio backdrop and soft contact shadow. The face, torso and other sleeve are outside the frame.',
    'pocket': 'Frame only the lower jacket cloth, side seam and flap pocket. Keep the flap shape, '
              'opening and shadow underneath at the same scale. The face, hands, shirt and trousers are outside the frame.',
}
DETAIL_REGIONS = {
    'lapel': ((.69, .50, .88, .68), ((.48, .34), (.64, .13), (.93, .24), (1, .98), (.38, .98))),
    'cuff': ((.58, .36, .77, .48), ((.29, .45), (.90, .09), (.99, .04), (1, .39), (.91, .64),
                                    (.30, .87), (.21, .65))),
    'pocket': ((.28, .62, .70, .82), ((.04, .04), (.89, .04), (.94, .96), (.02, .96))),
}
READY_DETAIL_SOURCES = {
    'lapel': ('front', (.44, .215, .83, .38)),
    'cuff': ('side', (.52, .36, .79, .48)),
    'pocket': ('side', (.37, .34, .62, .46)),
}
SHOTS = tuple(
    Shot(key, description, 'template_edit', framing, reference=REFERENCES / f'{index:02}_{key}.png',
         identity_from='request' if key in PORTRAIT_VIEWS else None,
         scenario='pose_reference' if key in PORTRAIT_VIEWS else 'person_photo')
    for index, (key, framing, description) in enumerate(VIEWS, 1)
)


def layout(product):
    return replace(blazer_layout(product), version='blazer-casual-six-panel-3x4-v1')


def build_config(data, shot, seed, *, style='casual', detail_framing=DETAIL_FRAMING,
                 cut='Keep the soft, unstructured notch-lapel cut and the open front wherever visible.',
                 outfit='Keep the casual crew-neck shirt, dark trousers and clean white sneakers as separate garments.'):
    ready = data.get('garment_image') is not None
    portrait = shot.key in PORTRAIT_VIEWS
    prompt = [
        f'Edit image 0 to make one {style.title()} Blazer catalog photograph: {shot.description}.',
        'Preserve its camera angle, crop, pose and subject scale. Fill the frame with the photograph.',
    ]
    if ready and portrait:
        prompt.append(
            'Image 1 is the finished garment. Use its actual cut, lapels, pockets, fastenings, '
            'stitching, pattern, fabric and colour. Continue the observed material over unseen areas. '
            'The display wearer, hanger or mannequin from image 1 stays out of the photograph.'
        )
    elif ready:
        prompt.append('Image 1 is a tight crop of the finished jacket as worn in this catalog. Copy its '
                      'actual cloth, colour and construction. Preserve buttons and pocket or cuff details '
                      'that exist on the garment. Keep image 0 for camera position and crop.')
    else:
        prompt.append(
            'Image 1 is the swatch. Apply its exact colour, weave and pattern only to the blazer cloth, '
            'including visible lapel, sleeve and pocket flap. Preserve seams, buttons, skin and backdrop. '
            + cut
        )
    if portrait:
        prompt.append(outfit)
        if data.get('gender'):
            prompt.append('Subject: ' + _person_description(data['gender'], data.get('body_type')) + '.')
        if shot.identity_from == 'request' and shot.key == 'back' and (
            data.get('person_image') or data.get('face_image') or data.get('face_choice')
        ):
            prompt.append('Use image 2 for visible hair and skin tone. Keep the person facing away.')
            if data.get('person_image'):
                prompt.append('Use the body build of the wearer in image 2.')
        elif shot.identity_from == 'request' and data.get('person_image'):
            prompt.append('Use image 2 for the wearer’s identity and build in the pose from image 0.')
        elif shot.identity_from == 'request' and (data.get('face_image') or data.get('face_choice')):
            prompt.append('Use image 2 for the wearer’s facial features, hair and skin tone.')
        scene = SCENERY.get(data.get('background'))
        if scene:
            prompt.append(f'Use {scene} behind the wearer, with diffuse neutral white light on the outfit.')
        if data.get('additional_style_note'):
            prompt.append(f"Styling: {data['additional_style_note']}. Preserve the jacket, fabric and crop.")
    else:
        prompt.append(detail_framing[shot.key])
        prompt.append('Edit the jacket in place. Continue the source weave and print around folds and '
                      'under the seams. Keep natural depth and shading in one continuous photograph.')
    if shot.key == 'back':
        prompt.append('Keep the face completely hidden and the jacket back continuously visible. '
                      'Show the rear seam and any actual rear vent. Front lapels, pockets, buttons '
                      'and buttonholes stay on the front of the jacket.')
    if style == 'casual' and shot.key == 'side':
        prompt.append('Use a broad neutral fill over the whole jacket, including the far shoulder, front panel '
                      'and both sleeves. Keep only soft shadows at folds and seams. Avoid hard dark bands, '
                      'coloured reflections and isolated bright spots across the cloth.')
    prompt.append('Use diffuse neutral white light, consistent jacket midtones and natural seam and fold '
                  'shadows. Preserve the actual pattern scale and motif colours. Plain fabric stays plain.')

    config = {
        'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': output_dimensions(data, shot), 'fabric_source_format': 'PNG',
        'classified_recovery': True, 'safety_retry_count': 0,
    }
    if not ready:
        config = apply_fabric_conditioning(config, data, 'blazer', style,
                                           match_pattern_colours=True, lead_with_edit=True)
        target = profile_midtone(config['fabric_colour_reference']) if 'fabric_colour_reference' in config else None
        if target is not None:
            shade = '#%02X%02X%02X' % tuple(round(float(channel)) for channel in target)
            config['prompt'] += f' Match the common swatch jacket midtone {shade}.'
    version = 'v3' if style == 'casual' else 'v1'
    config['prompt_version'] = f'blazer-{style}-catalog-{"ready" if ready else "swatch"}-{version}-{shot.key}'
    return config


def finish_shot(data, shot, generation):
    if shot.operation == 'swatch_composite':
        return generation
    crop = data.get('options', {}).get('fabric_crop_box')
    profile = measure_fabric_colours(data['fabric_image'], crop, palette_size=24, min_coverage=.005)
    return align_portrait_colour(generation, shot.key, profile_midtone(profile),
                                 region=DETAIL_REGIONS.get(shot.key), soft_edges=True,
                                 local_exposure=shot.key == 'side',
                                 even_exposure=shot.key == 'side' and has_uniform_swatch(profile))


# The pocket photograph is byte-identical to the Business pocket reference.
DETAIL_ASSETS = {'lapel': REFERENCES, 'pocket': BUSINESS_REFERENCES}
SWATCH_SHOTS = tuple(
    replace(shot, operation='swatch_composite', swatch_original_orientation=True,
            natural_swatch_shading=True,
            reference_mask=DETAIL_ASSETS[shot.key] / f'{shot.reference.stem}_mask.png',
            composite_relief=DETAIL_ASSETS[shot.key] / f'{shot.reference.stem}_relief.png')
    if shot.key in DETAIL_ASSETS else shot
    for shot in SHOTS
)
DEFINITION = CatalogDefinition('blazer', 'casual-v1', SWATCH_SHOTS, build_config, layout,
                               validate_request=validate_request, finish_shot=finish_shot,
                               swatch_colour=jacket_midtone)
READY_MADE_DEFINITION = replace(DEFINITION, finish_shot=None, swatch_colour=None, shots=(
    *SHOTS[:3],
    *(replace(shot, dependencies=(anchor,), garment_from=anchor, source_crop=crop)
      for shot in SHOTS[3:] for anchor, crop in (READY_DETAIL_SOURCES[shot.key],)),
))
