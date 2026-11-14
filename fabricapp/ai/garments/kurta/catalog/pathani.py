"""Six-panel Pathani catalog for fabric swatches and finished garments."""
from dataclasses import replace

from fabricapp.ai.fabric.body_region import select_body_fabric_region
from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.kurta.catalog import plain
from fabricapp.ai.garments.kurta.catalog.pathani_colour import match_cloth_exposure
from fabricapp.ai.garments.kurta.catalog.sherwani import SCENERY, WHITE_LIGHT
from fabricapp.ai.garments.kurta.catalog.sherwani_colour import solid_swatch_rgb
from fabricapp.ai.garments.kurta.details import SLEEVES_FOLDED
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot

REFERENCES = plain.REFERENCES.parent / 'pathani'
FRAMING = {
    'front': 'Keep the full-length front pose, from head to shoes, and show the chest and the knee-length hem.',
    'side': 'Keep the full-length side pose, including both shoes. Keep the side seam and hem visible.',
    'back': 'Keep the full-length straight rear pose with the face out of view. Keep the full hem visible. '
            'The rear panel stays continuous and free of front closures, chest pockets and buttons.',
    'collar': 'Keep only the lower chin and neck at the top edge. The collar, shoulders, upper placket and chest '
              'fill the frame. Keep the eyes, nose and rest of the face outside the frame.',
    'cuff': 'Keep one diagonal sleeve from upper right to lower left, its stitched cuff and the bare wrist '
            'at lower left. Use a smooth light-grey studio background outside the sleeve and wrist. '
            'Keep the sleeve edge softly shadowed and the cuff evenly exposed.',
    'pocket': 'Show one chest pocket in close-up at the same scale and position as image 0. Keep the chest '
              'cloth and sleeve edge in frame, with face, hands and trousers outside the crop.',
}
SWATCH_CONSTRUCTION = {
    'front': 'Keep the pointed shirt collar, short front placket, buttoned shoulder tabs and two button-flap chest pockets.',
    'side': 'Keep the stitched side vent near the lower hem and the shirt collar at the reference angle.',
    'back': 'Keep the reference yoke and carry the source cloth continuously across the back and both shoulders.',
    'collar': 'Keep the pointed collar, short placket, shoulder tabs and their reference fasteners.',
    'cuff': 'Keep the stitched cuff band, sleeve placket and their reference fasteners. Continue the source '
            'pattern across the natural folds and seams. Keep the wrist and backdrop free of cloth pattern.',
    'pocket': 'Keep the fabric flap, single button, centre stitching and angled pocket bottom from image 0. '
              'Apply the source cloth to the pocket, flap and adjacent chest at the same scale. '
              'Keep a soft contact shadow under the flap and at the stitched edges.',
}
READY_CROPS = {
    'collar': ('front', (.19, .16, .81, .33)),
    'cuff': ('side', (.14, .34, .78, .49)),
    'pocket': ('front', (.53, .24, .83, .36)),
}
SHOTS = tuple(
    Shot(key, description, 'template_edit', framing, reference=REFERENCES / f'{index:02}_{key}.png',
         identity_from='request' if key in plain.IDENTITY_VIEWS else None,
         scenario='pose_reference' if key in plain.IDENTITY_VIEWS else 'person_photo')
    for index, (key, framing, description) in enumerate((
        ('front', 'full_body', 'full-length front view'),
        ('side', 'side_full_body', 'full-length side view'),
        ('back', 'rear_full_body', 'full-length rear view'),
        ('collar', 'collar_detail', 'pointed collar and upper placket'),
        ('cuff', 'cuff_detail', 'diagonal sleeve and cuff'),
        ('pocket', 'pocket_detail', 'chest flap pocket'),
    ), start=1)
)


def layout(_product):
    return Layout('pathani-six-panel-3x4-v1', (1800, 2400), (
        Panel('front', (0, 0, 800, 2400), 'cover'),
        Panel('side', (812, 0, 1212, 1194), 'cover'),
        Panel('back', (812, 1206, 1212, 2400), 'cover'),
        Panel('collar', (1224, 0, 1800, 820), 'cover'),
        Panel('cuff', (1224, 832, 1800, 1392), 'cover'),
        Panel('pocket', (1224, 1404, 1800, 2400), 'cover'),
    ))


def build_config(data, shot, seed):
    ready = data.get('garment_image') is not None
    portrait = shot.key in plain.PORTRAITS
    details = data.get('garment_details') or ()
    prompt = ['Edit image 0 in place. Keep its camera angle, perspective and subject scale.', FRAMING[shot.key]]
    if ready and portrait:
        prompt.append('Image 1 supplies the finished Pathani. Use its actual length, collar, sleeves, pockets, '
                      'closures, stitching, fabric and trim. Include its matching trousers if supplied, '
                      'or use plain coordinating trousers. Use the source photo for clothing only.')
    elif ready:
        prompt.append('Image 1 is a crop of the Pathani as worn in this catalog. Copy its cloth, weave, pattern '
                      'scale and visible construction. Use image 0 for framing only. Include a flap, tab or button '
                      'only when present on the source garment. Keep visible details integrated into the cloth.')
        if shot.key == 'pocket':
            prompt.append('If the source has no pocket, show the actual chest cloth and seams in that crop.')
    else:
        prompt.append('Image 1 is the fabric swatch. Replace all Pathani cloth visible in this view with its '
                      'actual colour, weave and pattern at the original scale and spacing. Keep the same base '
                      'shade and motif contrast across seams and folds. A plain swatch stays plain. Keep template '
                      'colour and texture out of the garment. Keep skin, hardware and backdrop clean.')
        prompt.append(SWATCH_CONSTRUCTION[shot.key])
        if portrait:
            prompt.append('Use separate plain coordinating straight trousers. Keep any genuine decorative border '
                          'at the lower kurta hem and keep the body fabric continuous above it.')
        if 'folded_sleeves' in details and (portrait or shot.key == 'cuff'):
            prompt.append(SLEEVES_FOLDED.format(noun='Pathani') if portrait else
                          'Show the selected rolled cuff at the same diagonal angle, with a bare forearm.')

    if portrait:
        if shot.identity_from and data.get('person_image'):
            prompt.append('Use image 2 for the wearer’s face, hairstyle and body build. Keep the pose of image 0.')
        else:
            if data.get('gender'):
                prompt.append('Subject: ' + _person_description(data['gender'], data.get('body_type')) + '.')
            if shot.identity_from and (data.get('face_image') or data.get('face_choice')):
                prompt.append('Use image 2 for the wearer’s face and hairstyle.')
        if 'with_dupatta' in details:
            prompt.append('Drape the requested lightweight matching stole clear of the collar and chest pockets.')
        elif 'no_dupatta' in details or not ready:
            prompt.append('Keep the shoulders and chest free of a stole or scarf.')
        scene = SCENERY.get(data.get('background'))
        if scene:
            prompt.append(f'Use {scene} behind the subject.')
        if data.get('additional_style_note'):
            prompt.append(f"Styling direction: {data['additional_style_note']}. Preserve source cloth and framing.")

    config = {'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
              'output_dimensions': plain.reference_output_dimensions(data, shot),
              'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0}
    if not ready:
        crop, selection = select_body_fabric_region(data)
        context = {**data, 'options': {**data.get('options', {}), 'fabric_crop_box': crop}}
        if not portrait:
            config.update(fabric_crop_box=crop, fabric_region='body', fabric_region_selection=selection)
            context['garment_details'] = ()
            config['prompt'] += ' Use the body cloth and keep decorative hem borders outside this close-up.'
        config = apply_fabric_conditioning(config, context, 'kurta', 'pathani',
                                           match_pattern_colours=True, lead_with_edit=True)
    config['prompt'] += WHITE_LIGHT + ' Output one photograph without text or watermark.'
    config['prompt'] += (
        ' Use broad soft fill from both sides and above so the shoulders, sleeves and lower body '
        'share the same cloth exposure. Keep neutral studio fill on the garment in outdoor scenes. '
        'Keep narrow, soft shadows at folds and seams. Keep hard shadow bands, sun patches, rim '
        'lights and bright shoulder highlights off the cloth. Preserve skin, fasteners and trousers.'
    )
    config['prompt_version'] = f"pathani-catalog-{'ready' if ready else 'swatch'}-v2-{shot.key}"
    return config


def finish_shot(data, shot, generation):
    crop, _ = select_body_fabric_region(data)
    profile = measure_fabric_colours(data['fabric_image'], crop, palette_size=16, min_coverage=.015)
    return match_cloth_exposure(generation, shot.key, solid_swatch_rgb(profile))


DEFINITION = CatalogDefinition('kurta', 'pathani-v1', SHOTS, build_config, layout, finish_shot=finish_shot)
READY_MADE_DEFINITION = replace(DEFINITION, shots=SHOTS[:3] + tuple(
    replace(shot, dependencies=(anchor,), garment_from=anchor, source_crop=crop)
    for shot in SHOTS[3:]
    for anchor, crop in (READY_CROPS[shot.key],)
), finish_shot=None)
