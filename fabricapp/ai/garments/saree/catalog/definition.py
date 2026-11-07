"""Seven reference-driven shots, sharing the normal saree back-pallu rules."""
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot
from fabricapp.ai.garments.saree.catalog.references import REFERENCES
from fabricapp.ai.garments.saree.catalog.layout import get_layout
from fabricapp.ai.garments.saree.catalog.prompts import build_config

SHOTS = tuple(
    Shot(key, description, 'anchor_edit' if key == 'side_portrait' else 'template_edit', framing,
         dependencies=('front',) if identity == 'front' else (),
         reference=REFERENCES[key], identity_from=identity,
         identity_crop=(0.15, 0, 0.85, 0.45) if key in ('side_portrait', 'neckline') else None,
         reference_role='composition' if key == 'side_portrait' else 'template',
         composition_crop=(0, 0.32, 1, 1) if key == 'side_portrait' else None,
         scenario='person_pose' if key == 'side_portrait' else 'pose_reference' if identity or key == 'back_pallu' else 'person_photo')
    for key, description, framing, identity in (
        ('front', 'full-length front standing pose, complete head to saree hem, pallu spread visibly', 'full_body', 'request'),
        ('side_portrait', 'side/three-quarter portrait from head to hips, pallu draped over shoulder', 'side_portrait', 'front'),
        ('back_pallu', 'rear-facing full-length reference pose, both hands holding the broad diagonal pallu open, complete head and entire pallu edge visible', 'rear_full_body', None),
        ('neckline', 'extreme close-up from the bottom of the lips to just below the bust; neckline and shoulder drape fill the frame; exclude waist, hands and forearms', 'neckline_detail', 'front'),
        ('pallu', 'fabric-only flowing pallu edge laid in soft waves, showing its complete lower edge', 'fabric_detail', None),
        ('border', 'close-up of the saree long SIDE EDGE: a narrow continuous border or finished selvedge beside the main body cloth, with the outer edge and background clearly visible', 'side_border_detail', None),
        ('pleats', 'fabric-only vertical pleats and lower saree hem, no head or upper torso', 'pleats_detail', None),
    )
)
def validate_request(data):
    if data.get('gender') in ('men', 'boy'):
        return {'gender': 'This saree edition supports women or girls.'}
    return {}


DEFINITION = CatalogDefinition(
    'saree', 'editorial-v1', SHOTS, build_config, get_layout,
    product_fields=('title', 'collection', 'subtitle', 'badge', 'product_name', 'product_code',
                    'fabric_description', 'saree_length', 'blouse_length'),
    validate_request=validate_request,
)
