"""Sherwani catalog with dedicated framing and cloth instructions for each view."""
from dataclasses import replace

from fabricapp.ai.fabric.body_region import select_body_fabric_region
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.kurta.catalog import plain
from fabricapp.ai.garments.kurta.details import DUPATTA_REMOVE, KURTA_DUPATTA_ADD
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel

REFERENCES = plain.REFERENCES.parent / 'sherwani'
SHOTS = tuple(replace(shot, reference=REFERENCES / shot.reference.name) for shot in plain.SHOTS)

FRAMING = {
    'front': 'Show the full-length front pose, including head, hands and shoes. Keep the long fitted coat and centred closure.',
    'side': 'Show the full-length side pose and the side seam at the same angle as image 0. Keep both feet in frame.',
    'back': (
        'Show the full-length rear pose with the face turned away. Show one continuous closed rear panel and the complete hem. '
        'Keep the back and rear collar free of buttons, buttonholes, plackets, fasteners and ornament. '
        'Any front closures remain out of view.'
    ),
    'collar': (
        'Keep the chin at the top edge, the stand collar and the upper closure with two visible buttons. '
        'The chest fabric extends through the left, right and bottom edges. Frame only the neck and upper chest.'
    ),
    'cuff': (
        'Keep the single diagonal sleeve from upper right to lower left, its cuff edge, and the bare wrist at lower left. '
        'Keep the region behind the sleeve smooth light grey. Frame only one sleeve and its wrist.'
    ),
    'side_slit': (
        'Frame only the lower side seam, hem and vent at thigh level. The two hem edges frame the narrow side opening, '
        'with plain trouser cloth behind it. Keep the front closure, hands and upper body outside the frame.'
    ),
}

SWATCH_DETAILS = {
    'collar': 'Replace the cloth on the collar, placket and chest. Preserve the two reference buttons and their positions.',
    'cuff': 'Replace the cloth on the sleeve and cuff up to the wrist edge. Preserve the three reference cuff buttons.',
    'side_slit': 'Replace cloth on both sides of the vent and both hem folds. Keep the side vent free of buttons and fasteners.',
}

READY_CROPS = {
    'collar': ('front', (.27, .15, .73, .34)),
    'cuff': ('side', (.22, .36, .73, .52)),
    'side_slit': ('side', (.44, .49, .80, .72)),
}

SCENERY = {
    'white_marble_terrace': 'a carved white marble terrace overlooking a lake and distant hills',
    'festive_street': 'an Indian heritage street with carved balconies, marigolds and decorative lanterns',
    'royal_courtyard': 'a palace courtyard with carved arches, columns and a central fountain',
    'riverside_ghat': 'a riverside ghat with stone steps and distant temple spires',
}

WHITE_LIGHT = (
    ' FINAL LIGHTING: Illuminate the subject and setting only with broad, diffused neutral white light '
    'and neutral camera white balance. No direct sunlight, warm light, golden-hour glow or coloured reflections. '
    'Match the source fabric hue, saturation, midtone brightness and motif contrast. '
    'Keep natural soft fold shadows and the selected fabric finish. No saturation boost or orange colour cast.'
)


def layout(_product):
    return Layout('sherwani-six-panel-3x4-v1', (1800, 2400), (
        Panel('front', (0, 0, 800, 2400), 'cover'),
        Panel('side', (812, 0, 1236, 1194), 'cover'),
        Panel('back', (812, 1206, 1236, 2400), 'cover'),
        Panel('collar', (1248, 0, 1800, 912), 'cover'),
        Panel('cuff', (1248, 924, 1800, 1476), 'cover'),
        Panel('side_slit', (1248, 1488, 1800, 2400), 'cover'),
    ))


def build_config(data, shot, seed):
    ready = data.get('garment_image') is not None
    portrait = shot.key in plain.PORTRAITS
    prompt = ['Edit image 0 in place for this Sherwani catalog view. Keep its camera angle, zoom and frame boundaries.',
              FRAMING[shot.key]]
    if ready:
        if portrait:
            prompt.append('Image 1 supplies only the finished Sherwani. Preserve its cut, length, colour, '
                          'weave, motifs, trim and visible closures. Exclude its mannequin, original wearer and surroundings. '
                          'Complete the outfit with plain coordinating trousers and shoes when these are absent from the upload.')
        else:
            prompt.append('Image 1 is a tight crop of the Sherwani as worn in this catalog. Use its cloth, '
                          'finish and visible construction. Keep the crop and camera distance of image 0.')
            if shot.key in ('collar', 'cuff'):
                prompt.append('Copy the actual visible closure and buttons from image 1. Leave a button-free cuff plain.')
            else:
                prompt.append('Show a vent only if visible in image 1. Keep the side seam and hem free of added fasteners.')
    else:
        prompt.append('Image 0 is a guide to pose, cut and framing only. Completely replace its embroidered cloth '
                      'with the cloth in image 1. The swatch alone supplies colour, weave and any actual motifs. '
                      'A solid swatch stays solid in every panel: preserve its weave and sheen without borrowing '
                      'embroidery, diamonds, jacquard, stripes or borders from image 0. Keep fabric off skin and background.')
        if portrait:
            if shot.key != 'back':
                prompt.append('Keep the reference front closure and its visible fasteners.')
            prompt.append('Keep the separate trousers plain ivory. Place any distinct decorative swatch border at the lower hem only.')
            prompt.append(KURTA_DUPATTA_ADD if 'with_dupatta' in data.get('garment_details', ()) else DUPATTA_REMOVE)
        else:
            prompt.append(SWATCH_DETAILS[shot.key])
            if shot.key == 'side_slit':
                prompt.append('Keep any distinct decorative swatch border at the lower hem only.')

    if portrait:
        if shot.key in plain.IDENTITY_VIEWS and data.get('person_image'):
            prompt.append('Image 2 supplies the same human face, hairstyle, facial hair and body build in every view. '
                          'Match those features and skin tone exactly. Use image 0 for the pose and camera framing.')
        elif data.get('gender'):
            prompt.append('Subject: ' + _person_description(data['gender'], data.get('body_type')) + '.')
            if shot.key in plain.IDENTITY_VIEWS and (data.get('face_choice') or data.get('face_image')):
                prompt.append('Image 2 supplies the face and hairstyle. Keep the requested body build.')
        background = SCENERY.get(data.get('background'))
        if background:
            prompt.append(f'Use {background} behind the subject.')
        if data.get('additional_style_note'):
            prompt.append(f"Styling direction: {data['additional_style_note']}. Preserve garment fidelity and framing.")

    prompt.append('Output one photograph.')
    config = {'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
              'output_dimensions': plain.reference_output_dimensions(data, shot),
              'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0}
    if not ready:
        crop, selection = select_body_fabric_region(data)
        context = {**data, 'options': {**data.get('options', {}), 'fabric_crop_box': crop}}
        if not portrait:
            context['garment_details'] = ()
        if shot.key in ('collar', 'cuff'):
            config.update(fabric_crop_box=crop, fabric_region='body', fabric_region_selection=selection)
            config['prompt'] += ' Use the body cloth here. The cloth runs continuously to the frame edges without a hem border.'
        else:
            config['prompt'] += (' A decorative hem border must come from a visible edge band in image 1. '
                                 'For a plain swatch, keep the hem plain with a simple stitch line.')
        conditioned = apply_fabric_conditioning(config, context, 'kurta', 'sherwani', lead_with_edit=True)
        if selection == 'detected_body_crop' or 'fabric_colour_reference' not in conditioned:
            conditioned = apply_fabric_conditioning(config, context, 'kurta', 'sherwani',
                                                    match_pattern_colours=True, lead_with_edit=True)
        config = conditioned
    config['prompt'] += WHITE_LIGHT
    if shot.key == 'cuff':
        config['prompt'] += ' Keep the cuff evenly exposed with no glare, white patches or clipped highlights.'
    source = 'ready' if ready else 'swatch'
    config['prompt_version'] = f'sherwani-catalog-{source}-v3-{shot.key}'
    return config


SWATCH_SHOTS = tuple(
    replace(shot, operation='swatch_composite', reference_mask=REFERENCES / '05_cuff_mask.png',
            swatch_body_only=True, composite_backdrop=REFERENCES / '05_cuff_neutral.png')
    if shot.key == 'cuff' else shot for shot in plain.swatch_shots(SHOTS)
)
DEFINITION = CatalogDefinition('kurta', 'sherwani-v1', SWATCH_SHOTS, build_config, layout)
READY_MADE_DEFINITION = replace(DEFINITION, shots=SHOTS[:3] + tuple(
    replace(shot, dependencies=(anchor,), garment_from=anchor, source_crop=crop)
    for shot in SHOTS[3:]
    for anchor, crop in (READY_CROPS[shot.key],)
))
