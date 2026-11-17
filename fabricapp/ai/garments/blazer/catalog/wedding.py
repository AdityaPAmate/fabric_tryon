"""Wedding Blazer catalog using the six wedding pose and close-up references."""
from dataclasses import replace

from fabricapp.ai.garments.blazer.catalog import casual
from fabricapp.ai.garments.blazer.catalog.colour import align_portrait_colour, jacket_midtone
from fabricapp.catalog_engine.contracts import Panel


REFERENCES = casual.REFERENCES.parent / 'wedding'
DESCRIPTIONS = {
    'front': 'full-length front view from head to dress shoes',
    'side': 'full-length three-quarter side view from head to dress shoes',
    'back': 'full-length rear view from head to dress shoes with the face hidden',
    'lapel': 'close-up of the wedding lapel, collared dress shirt and breast-pocket accessories',
    'cuff': 'diagonal sleeve close-up with cuff buttons and a small bare wrist',
    'pocket': 'tight lower jacket pocket close-up showing its flap, opening and stitching',
}
DETAIL_FRAMING = {
    **casual.DETAIL_FRAMING,
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
    **casual.DETAIL_REGIONS,
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


def layout(product):
    return replace(casual.layout(product), version='blazer-wedding-six-panel-3x4-v2', panels=(
        Panel('front', (0, 0, 780, 2400), 'cover'),
        Panel('side', (792, 0, 1158, 1194), 'cover'),
        Panel('back', (792, 1206, 1158, 2400), 'cover'),
        Panel('lapel', (1170, 0, 1800, 1006), 'cover'),
        Panel('cuff', (1170, 1018, 1800, 1574), 'cover'),
        Panel('pocket', (1170, 1586, 1800, 2400), 'cover'),
    ))


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
    config = casual.build_config(
        data, shot, seed, style='wedding', detail_framing=DETAIL_FRAMING, outfit=outfit,
        cut=cut,
    )
    if not ready and shot.key in casual.PORTRAIT_VIEWS:
        config['prompt'] += (
            ' The jacket and trousers are cut from one bolt of image 1 fabric. Match their base colour '
            'and texture from shoulders to ankles. The white shirt is visible only inside the jacket '
            'opening and at the wrists. Match the closure and accessories in image 0 exactly.'
        )
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


def wedding_shots(shots):
    return tuple(replace(shot, reference=REFERENCES / shot.reference.name,
                         description=DESCRIPTIONS[shot.key]) for shot in shots)


SWATCH_SHOTS = tuple(
    replace(shot, operation='swatch_composite',
            reference_mask=shot.reference.with_stem(f'{shot.reference.stem}_mask'),
            composite_relief=shot.reference.with_stem(f'{shot.reference.stem}_relief'),
            swatch_original_orientation=True, natural_swatch_shading=True)
    if shot.key in ('cuff', 'pocket') else shot
    for shot in wedding_shots(casual.SHOTS)
)
DEFINITION = replace(casual.DEFINITION, edition='wedding-v1', shots=SWATCH_SHOTS,
                     build_config=build_config, layout=layout, finish_shot=finish_shot,
                     swatch_colour=jacket_midtone)
READY_MADE_DEFINITION = replace(DEFINITION, finish_shot=None,
                                shots=wedding_shots(casual.READY_MADE_DEFINITION.shots), swatch_colour=None)
