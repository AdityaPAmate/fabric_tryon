"""Wedding Blazer catalog using the six wedding pose and close-up references."""
from dataclasses import replace

from PIL import Image

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.blazer.catalog.colour import align_portrait_colour, jacket_midtone, profile_midtone
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
from fabricapp.ai.scene.catalog_backgrounds import CATALOG_SCENERY
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot


REFERENCES = CATALOG_REFERENCE_DIR / 'blazer' / 'wedding'
DETAIL_FRAMING = {
    'lapel': 'Keep the mouth and chin at the top edge, the collared shirt inside the opening, and the '
             'notch lapel, breast pocket and upper chest in frame. Keep the eyes, hands and waist '
             'outside the crop. Keep any pocket square and chain separate from the jacket cloth.',
    'cuff': 'Keep exactly one diagonal sleeve, its four cuff buttons and the small wrist at the left edge. '
            'The sleeve crosses a plain studio backdrop. Keep the torso, other sleeve, shirt front, '
            'lapels and accessories out of the frame. Preserve the real cuff fold and soft contact shadow.',
    'pocket': 'Keep the exact tight crop at waist level, from below the lapel to above the jacket hem. '
              'The flap, its opening and the lower side seam are the only details in frame. '
              'Keep the breast pocket, gold chain, shirt opening and front buttons outside the crop.',
}
DETAIL_REGIONS = {
    'cuff': ((.58, .36, .77, .48), ((.29, .45), (.90, .09), (.99, .04), (1, .39), (.91, .64),
                                    (.30, .87), (.21, .65))),
    'pocket': ((.28, .62, .70, .82), ((.04, .04), (.89, .04), (.94, .96), (.02, .96))),
    'side': ((.54, .29, .68, .40), ((.48, .21), (.64, .19), (.76, .24), (.79, .37),
                                   (.72, .47), (.70, .53), (.58, .55), (.46, .56),
                                   (.36, .53), (.32, .47), (.34, .36), (.40, .32))),
    'lapel': ((.77, .45, .89, .56), ((.65, .28), (.87, .19), (.99, .35), (.99, .63), (.65, .58))),
}
TROUSER_REGIONS = {
    'front': ((.38, .56, .61, .64),
              ((.23, .52), (.77, .52), (.76, .68), (.74, .93), (.56, .94), (.50, .61),
               (.44, .93), (.23, .93), (.21, .68))),
    'side': ((.45, .58, .56, .67),
             ((.35, .54), (.67, .55), (.69, .68), (.72, .86), (.70, .935), (.56, .934),
              (.51, .90), (.43, .90), (.38, .77), (.34, .66))),
    'back': ((.39, .55, .62, .64),
             ((.23, .49), (.77, .49), (.83, .67), (.78, .94), (.55, .95), (.50, .69),
              (.45, .95), (.23, .94), (.17, .68))),
}


VIEWS = (
    ('front', 'full_body', 'full-length front view from head to dress shoes'),
    ('side', 'side_full_body', 'full-length three-quarter side view from head to dress shoes'),
    ('back', 'rear_full_body', 'full-length rear view from head to dress shoes with the face hidden'),
    ('lapel', 'lapel_detail', 'close-up of the wedding lapel, collared dress shirt and breast-pocket accessories'),
    ('cuff', 'cuff_detail', 'diagonal sleeve close-up with cuff buttons and a small bare wrist'),
    ('pocket', 'pocket_detail', 'tight lower jacket pocket close-up showing its flap, opening and stitching'),
)


PORTRAIT_VIEWS = {'front', 'side', 'back'}


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


def layout(_product):
    return Layout('blazer-wedding-six-panel-3x4-v2', (1800, 2400), (
        Panel('front', (0, 0, 780, 2400), 'cover'),
        Panel('side', (792, 0, 1158, 1194), 'cover'),
        Panel('back', (792, 1206, 1158, 2400), 'cover'),
        Panel('lapel', (1170, 0, 1800, 1006), 'cover'),
        Panel('cuff', (1170, 1018, 1800, 1574), 'cover'),
        Panel('pocket', (1170, 1586, 1800, 2400), 'cover'),
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


def _build_template_config(data, shot, seed, *, cut, outfit):
    ready = data.get('garment_image') is not None
    portrait = shot.key in PORTRAIT_VIEWS
    prompt = [
        f'Edit image 0 to make one Wedding Blazer catalog photograph: {shot.description}.',
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
        scene = CATALOG_SCENERY.get(data.get('background'))
        if scene:
            prompt.append(f'Use {scene} behind the wearer, with diffuse neutral white light on the outfit.')
        if data.get('additional_style_note'):
            prompt.append(f"Styling: {data['additional_style_note']}. Preserve the jacket, fabric and crop.")
    else:
        prompt.append(DETAIL_FRAMING[shot.key])
        prompt.append('Edit the jacket in place. Continue the source weave and print around folds and '
                      'under the seams. Keep natural depth and shading in one continuous photograph.')
    if shot.key == 'back':
        prompt.append('Keep the face completely hidden and the jacket back continuously visible. '
                      'Show the rear seam and any actual rear vent. Front lapels, pockets, buttons '
                      'and buttonholes stay on the front of the jacket.')
    prompt.append('Use diffuse neutral white light, consistent jacket midtones and natural seam and fold '
                  'shadows. Preserve the actual pattern scale and motif colours. Plain fabric stays plain.')

    config = {
        'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': output_dimensions(data, shot), 'fabric_source_format': 'PNG',
        'classified_recovery': True, 'safety_retry_count': 0,
    }
    if not ready:
        config = apply_fabric_conditioning(config, data, 'blazer', 'wedding',
                                           match_pattern_colours=True, lead_with_edit=True)
        target = profile_midtone(config['fabric_colour_reference']) if 'fabric_colour_reference' in config else None
        if target is not None:
            shade = '#%02X%02X%02X' % tuple(round(float(channel)) for channel in target)
            config['prompt'] += f' Match the common swatch jacket midtone {shade}.'
    config['prompt_version'] = f'blazer-wedding-catalog-{"ready" if ready else "swatch"}-v1-{shot.key}'
    return config


def build_config(data, shot, seed):
    ready = data.get('garment_image') is not None
    outfit = (
        'Use the matching trousers when supplied with the finished jacket. Keep the white collared '
        'dress shirt and formal shoes as separate items. Follow the supplied garment for accessories.'
        if ready else
        'Use matching trousers in the same swatch cloth. Preserve the white collared dress shirt directly '
        'under the jacket opening and the formal shoes. Leave the waist free of a vest or cummerbund. '
        'Keep the burgundy pocket square and gold chain where visible in image 0, with their own colours and materials.'
    )
    cut = 'Preserve the wedding jacket tailoring from image 0.'
    if shot.key == 'lapel':
        cut += ' Keep the pocket square and gold chain exactly where they appear in image 0.'
    config = _build_template_config(data, shot, seed, outfit=outfit, cut=cut)
    if shot.key in PORTRAIT_VIEWS:
        config['prompt'] += (' Keep any gold chain pinned to the breast pocket only. '
                             'Show the shirt collar and neck free of jewellery.')
    if not ready and shot.key in PORTRAIT_VIEWS:
        config['prompt'] += (
            ' The jacket and trousers are cut from one bolt of image 1 fabric. Match their base colour '
            'and texture from shoulders to ankles. The white shirt is visible only inside the jacket '
            'opening and at the wrists. Match the closure and accessories in image 0 exactly.'
        )
        if shot.identity_from == 'front':
            angle = ('three-quarter side angle with the near shoulder forward and one hand in a trouser pocket'
                     if shot.key == 'side' else 'straight rear angle with both shoulders visible and the face hidden')
            config['prompt'] = (
                f'Camera priority: keep image 0’s exact {angle}, outline and head-to-shoes crop. '
                'Image 2 is a tight cloth crop from the already photographed suit in this catalog. '
                'Use it for the established fabric appearance only. Use image 1 for the exact material, '
                'colour and pattern across both garments. Keep the pose and head orientation from image 0. '
                'Keep both garments uniformly in the same source shade, with soft natural fold shadows. '
                + config['prompt']
            )
    if not ready:
        config['prompt_version'] = f'blazer-wedding-catalog-swatch-v2-{shot.key}'
    return config


def finish_shot(data, shot, generation):
    if shot.operation == 'swatch_composite':
        return generation
    target = jacket_midtone(data)
    generation = align_portrait_colour(generation, shot.key, target,
                                       region=DETAIL_REGIONS.get(shot.key), soft_edges=True, local_exposure=True)
    if shot.key in TROUSER_REGIONS:
        generation = align_portrait_colour(generation, 'trousers', target,
                                           region=TROUSER_REGIONS[shot.key], soft_edges=True, local_exposure=True)
    return generation


SWATCH_SHOTS = tuple(
    replace(shot, operation='swatch_composite',
            reference_mask=shot.reference.with_stem(f'{shot.reference.stem}_mask'),
            composite_relief=shot.reference.with_stem(f'{shot.reference.stem}_relief'),
            swatch_original_orientation=True, natural_swatch_shading=True)
    if shot.key in ('cuff', 'pocket') else
    replace(shot, dependencies=('front',), identity_from='front', identity_crop=(.24, .25, .40, .36))
    if shot.key in ('side', 'back') else shot
    for shot in SHOTS
)
DEFINITION = CatalogDefinition('blazer', 'wedding-v1', SWATCH_SHOTS, build_config, layout,
                               validate_request=validate_request, finish_shot=finish_shot,
                               swatch_colour=jacket_midtone)
READY_MADE_DEFINITION = replace(DEFINITION, finish_shot=None, swatch_colour=None, shots=(
    *SHOTS[:3],
    *(replace(shot, dependencies=(anchor,), garment_from=anchor, source_crop=crop)
      for shot in SHOTS[3:] for anchor, crop in (READY_DETAIL_SOURCES[shot.key],)),
))
