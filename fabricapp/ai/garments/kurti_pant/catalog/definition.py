"""Six reference views for the Kurti + Pant editorial catalog."""
from fabricapp.ai.garments.kurti_pant.catalog.prompts import build_config
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR
from fabricapp.catalog_engine.contracts import CatalogDefinition, Layout, Panel, Shot


REFERENCE_DIR = CATALOG_REFERENCE_DIR / 'kurti_pant'
IDENTITY_VIEWS = {'front', 'side'}
PANELS = (
    Panel('front', (0, 0, 894, 2400), 'cover'),
    Panel('side', (906, 0, 1320, 1194), 'cover'),
    Panel('back', (906, 1206, 1320, 2400), 'cover'),
    Panel('neckline', (1332, 0, 1800, 756), 'cover'),
    Panel('sleeve', (1332, 768, 1800, 1572), 'cover'),
    Panel('pant', (1332, 1584, 1800, 2400), 'cover'),
)
SHOTS = tuple(
    Shot(key, description, 'reference' if key == 'pant' else 'template_edit', framing,
         reference=REFERENCE_DIR / filename,
         reference_mask=REFERENCE_DIR / 'kurti_pant_6_mask.png' if key == 'pant' else None,
         identity_from='request' if key in IDENTITY_VIEWS else None,
         scenario='pose_reference' if key in IDENTITY_VIEWS else 'person_photo')
    for key, filename, framing, description in (
        ('front', 'kurti_front_1.png', 'full_body',
         'front full-length view of the complete kurti and pants, from head to feet'),
        ('side', 'kurti_side_2.png', 'side_full_body',
         'full-length side view at the exact reference angle, with both garments visible'),
        ('back', 'kurti_back_3.png', 'rear_full_body',
         'full-length rear view with the head and torso facing away, showing the entire back and pant hems'),
        ('neckline', 'kurti_closeup_4.png', 'neckline_detail',
         'tight neckline and upper-chest detail showing the kurti fabric and neckline construction'),
        ('sleeve', 'kurti_sleves_5.png', 'sleeve_detail',
         'close-up of the kurti sleeve fabric and finished cuff, with the folded cloth geometry in image 0'),
        ('pant', 'kurti_pant_6.png', 'pant_detail',
         'close-up of the separate pants, showing the waistband and front leg folds'),
    )
)


def get_layout(product=None):
    return Layout('kurti-pant-six-panel-3x4-v2', (1800, 2400), PANELS)


def validate_request(data):
    if data.get('gender') in ('men', 'boy'):
        return {'gender': 'This Kurti + Pant edition supports women or girls.'}
    return {}


DEFINITION = CatalogDefinition('kurti_pant', 'editorial-v1', SHOTS, build_config,
                               get_layout, validate_request=validate_request)
