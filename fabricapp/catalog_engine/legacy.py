"""Six-shot compatibility edition for garments not yet given a custom catalog."""
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot, Panel, Layout, Text
from fabricapp.ai.fabric.fabric_conditioning import apply_fabric_conditioning
from fabricapp.ai.scene.backgrounds import get_background_description
from fabricapp.ai.scene.garment_lighting import apply_garment_lighting

DETAILS = {
    'blazer': [('lapel', 'lapel and collar'), ('cuff', 'sleeve cuff'), ('hem', 'lower jacket hem')],
    'kurta': [('neckline', 'neckline'), ('cuff', 'sleeve end'), ('hem', 'lower garment hem')],
    'kurti_pant': [('neckline', 'kurti neckline'), ('sleeve', 'kurti sleeve end'), ('hem', 'lower kurti hem')],
    'pant': [('waistband', 'trouser waistband'), ('pocket', 'trouser side pocket'), ('hem', 'trouser ankle hem')],
    'saree': [('pallu', 'pallu'), ('border', 'saree border'), ('pleats', 'saree pleats')],
}
BOXES = ((0, 0, 760, 2520), (772, 0, 1280, 894), (1292, 0, 1800, 894),
         (772, 906, 1800, 1572), (772, 1584, 1800, 2052), (772, 2064, 1800, 2520))


def build_config(data, shot, seed):
    prompt = (f'Create exactly ONE NEW photograph: {shot.description}. '
              + ('Image 0 is a blank canvas. Image 2 is the approved front image. '
                 if shot.scenario == 'person_pose' else 'Image 0 is the approved front image. ')
              + 'Keep the SAME person, body build, finished outfit, separate clothing, '
              'construction, colours and fabric pattern scale. Image 1 supplies the original fabric. '
              'Change only the requested camera and framing. No collage, text or watermark. ')
    background = get_background_description(data.get('background'), garment_type=data['garment_type'])
    prompt += 'BACKGROUND: ' + (background or 'retain the same setting as the front image') + '. '
    config = {'prompt': prompt, 'seed': seed, 'guidance': data.get('guidance', 7),
              'prompt_version': 'catalog-classic-v3', 'safety_retry_count': 0}
    config = apply_fabric_conditioning(config, data, data['garment_type'], data.get('garment_style'))
    config['prompt'] += ' FINAL CAMERA REQUIREMENT: ' + shot.description + '. '
    return apply_garment_lighting(config, data['garment_type'])


def make_definition(garment):
    rear = ('rear waistband, seat and both trouser legs to their hems, excluding upper torso and shoes'
            if garment == 'pant' else 'back of garment from shoulders to its hem, excluding face, legs and shoes')
    shots = [Shot('front', 'front full-body view', 'pipeline', 'full_body', camera_view='front'),
             Shot('three_quarter', 'FRONT THREE-QUARTER close-up: camera 45 degrees around the person; show front and side from head to garment hem',
                  'anchor_edit', 'three_quarter_close_up', ('front',), scenario='person_pose'),
             Shot('back', 'REAR CLOSE-UP product photograph: ' + rear, 'anchor_edit', 'rear_close_up', ('front',))]
    shots += [Shot(key, 'tight product detail photograph of the ' + part + ' only', 'anchor_edit',
                   'detail_close_up', ('front',)) for key, part in DETAILS[garment]]
    shots = tuple(shots)
    def layout(product):
        return Layout('portrait-catalog-v2', (1800, 3200),
                      tuple(Panel(shot.key, box, 'contain' if shot.key in ('cuff', 'sleeve', 'hem') else 'cover')
                            for shot, box in zip(shots, BOXES)),
                      (36, 2544, 1764, 3072), (Text('FABRIC SWATCH', (900, 3132), 40, 1700, anchor='mm'),))
    return CatalogDefinition(garment, 'classic-v1', shots, build_config, layout)
