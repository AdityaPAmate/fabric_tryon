"""Reference-based 3:4 Shirt catalog with independent pose and detail shots."""
from PIL import Image

from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.garments.shirt.details import get_shirt_detail_prompt, SLEEVES_FOLDED, SHIRT_TUCKED
from fabricapp.ai.pipeline.scenario_composer import _person_description
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot


REFERENCES = CATALOG_REFERENCE_DIR / 'shirt'
PORTRAITS = {'front', 'close_up', 'back'}
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


def build_config(data, shot, seed):
    portrait = shot.key in PORTRAITS
    details = data.get('garment_details') or ()
    prompt = [
        f'Edit image 0 in place to make one Shirt catalog photograph: {shot.description}.',
        'Image 0 fixes the exact pose, camera angle, crop, shirt outline, seams and button positions.',
        'Image 1 supplies only the fabric. Replace every visible shirt panel, collar, sleeve, cuff, '
        'placket and hem with its actual colour, weave and pattern at the original scale. '
        'Keep plain cloth plain. Preserve all buttons, skin, accessories and separate trousers.',
    ]
    if portrait:
        prompt.append(get_shirt_detail_prompt(details))
        prompt.append('Keep the reference shirt length and the trousers separate and plain white.')
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
        detail = {
            'collar': 'Keep the chin, neck and existing collar opening. Keep the collar points and top buttons in place.',
            'cuff': 'Keep one vertical sleeve, its broad cuff, pointed sleeve placket and single cuff button. '
                    'Keep the wrist bare and the studio background plain grey.',
            'hem': 'Keep the curved untucked hem, its stitching, small front opening and existing button. '
                   'Keep the trousers and grey backdrop unchanged.',
        }
        prompt.append(detail[shot.key])
        if shot.key == 'cuff' and 'folded_sleeves' in details:
            prompt.append(SLEEVES_FOLDED.format(noun='shirt') + ' Preserve this sleeve-detail camera angle.')
        if shot.key == 'hem' and 'tucked' in details:
            prompt.append(SHIRT_TUCKED + ' Show the selected tucked waist treatment at this close-up scale.')
        prompt.append('Keep this exact close-up. The face, full torso and full outfit are outside the crop.')
    prompt.append('Use even neutral white light with natural seam and fold shadows. Preserve the source '
                  'midtone and every printed colour. Keep sunlight, warm casts and bright patches off the cloth. '
                  'Output one photograph with no text or collage.')
    config = {
        'prompt': ' '.join(prompt), 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': output_dimensions(data, shot), 'output_size_multiple': 32,
        'fabric_source_format': 'PNG', 'classified_recovery': True, 'safety_retry_count': 0,
    }
    config = apply_fabric_conditioning(config, data, 'shirt', match_pattern_colours=True, lead_with_edit=True)
    config['prompt_version'] = f'shirt-editorial-swatch-v1-{shot.key}'
    return config


DEFINITION = CatalogDefinition('shirt', 'editorial-v1', SHOTS, build_config, layout)
