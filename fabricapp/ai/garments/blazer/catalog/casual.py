"""Casual Blazer catalog with one model reference per photograph."""
from dataclasses import replace

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.blazer.catalog.business import layout as blazer_layout, output_dimensions, validate_request
from fabricapp.ai.garments.blazer.catalog.colour import align_portrait_colour, jacket_midtone, profile_midtone
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
from fabricapp.ai.scene.backgrounds import BACKGROUND_DESCRIPTIONS
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
SHOTS = tuple(
    Shot(key, description, 'template_edit', framing, reference=REFERENCES / f'{index:02}_{key}.png',
         dependencies=() if key in PORTRAIT_VIEWS else ('front',),
         identity_from='request' if key in PORTRAIT_VIEWS else 'front', scenario='pose_reference')
    for index, (key, framing, description) in enumerate(VIEWS, 1)
)


def layout(product):
    return replace(blazer_layout(product), version='blazer-casual-six-panel-3x4-v1')


def build_config(data, shot, seed):
    ready = data.get('garment_image') is not None
    portrait = shot.key in PORTRAIT_VIEWS
    prompt = [
        f'Edit image 0 to make one Casual Blazer catalog photograph: {shot.description}.',
        'Preserve its camera angle, crop, pose and subject scale. Fill the frame with the photograph.',
    ]
    if ready:
        prompt.append(
            'Image 1 is the finished garment. Use its actual cut, lapels, pockets, fastenings, '
            'stitching, pattern, fabric and colour. Continue the observed material over unseen areas. '
            'The display wearer, hanger or mannequin from image 1 stays out of the photograph.'
        )
    else:
        prompt.append(
            'Image 1 is the swatch. Apply its exact colour, weave and pattern only to the blazer cloth, '
            'including visible lapel, sleeve and pocket flap. Preserve seams, buttons, skin and backdrop. '
            'Keep the soft, unstructured notch-lapel cut and the open front wherever visible.'
        )
    if portrait:
        prompt.append('Keep the casual crew-neck shirt, dark trousers and clean white sneakers as separate garments.')
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
        if data.get('background'):
            prompt.append(f"Background: {BACKGROUND_DESCRIPTIONS[data['background']]}")
        if data.get('additional_style_note'):
            prompt.append(f"Styling: {data['additional_style_note']}. Preserve the jacket, fabric and crop.")
    else:
        prompt.append('Keep the close-up from image 0 tight. Image 2 supplies the established jacket midtone and fabric appearance.')
    if portrait and shot.identity_from == 'front':
        prompt.append('Match the wearer, outfit and jacket midtone established in image 2 while keeping the pose from image 0.')
    if shot.key == 'back':
        prompt.append('Keep the face completely hidden and the jacket back continuously visible.')
    prompt.append('Use soft neutral light and consistent jacket midtones with natural seam and fold shadows.')

    config = {
        'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': output_dimensions(data, shot), 'fabric_source_format': 'PNG',
        'classified_recovery': True, 'safety_retry_count': 0,
    }
    if not ready:
        config = apply_fabric_conditioning(config, data, 'blazer', 'casual',
                                           match_pattern_colours=True, lead_with_edit=True)
        target = profile_midtone(config['fabric_colour_reference'])
        if target is not None:
            shade = '#%02X%02X%02X' % tuple(round(float(channel)) for channel in target)
            config['prompt'] += f' Match the common swatch jacket midtone {shade}.'
    config['prompt_version'] = f'blazer-casual-catalog-{"ready" if ready else "swatch"}-v1-{shot.key}'
    return config


def finish_shot(data, shot, generation):
    if shot.key in PORTRAIT_VIEWS:
        return align_portrait_colour(generation, shot.key, jacket_midtone(data))
    return generation


DEFINITION = CatalogDefinition('blazer', 'casual-v1', SHOTS, build_config, layout,
                               validate_request=validate_request, finish_shot=finish_shot)
READY_MADE_DEFINITION = replace(DEFINITION, finish_shot=None, shots=(
    SHOTS[0], *(replace(shot, dependencies=('front',), identity_from='front') for shot in SHOTS[1:]),
))
