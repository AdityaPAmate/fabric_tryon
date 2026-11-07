"""Seven explicit reference-driven shots; no changes to the single-image builder."""
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot
from fabricapp.ai.garments.saree.catalog.references import REFERENCES
from fabricapp.ai.garments.saree.catalog.layout import get_layout
from fabricapp.ai.garments.saree.catalog.prompts import build_config

SHOTS = tuple(
    Shot(key, description, 'anchor_edit' if key == 'side_portrait' else 'crop' if key == 'border' else 'template_edit', framing,
         dependencies=('front',) if identity == 'front' else ('pallu',) if key == 'border' else (),
         reference=REFERENCES[key], identity_from=identity,
         identity_crop=(0.15, 0, 0.85, 0.45) if key in ('side_portrait', 'neckline') else None,
         reference_role='composition' if key == 'side_portrait' else 'layout' if key == 'border' else 'template',
         composition_crop=(0, 0.32, 1, 1) if key == 'side_portrait' else None,
         source_crop=(0.2, 0.5, 1, 0.9) if key == 'border' else None,
         scenario='person_pose' if key == 'side_portrait' else 'pose_reference' if identity else 'person_photo')
    for key, description, framing, identity in (
        ('front', 'full-length front standing pose, complete head to saree hem, pallu spread visibly', 'full_body', 'request'),
        ('side_portrait', 'side/three-quarter portrait from head to hips, pallu draped over shoulder', 'side_portrait', 'front'),
        ('back_pallu', 'full-length rear view showing the spread pallu, complete head and saree hem', 'rear_full_body', 'front'),
        ('neckline', 'extreme close-up from the bottom of the lips to just below the bust; neckline and shoulder drape fill the frame; exclude waist, hands and forearms', 'neckline_detail', 'front'),
        ('pallu', 'fabric-only flowing pallu edge laid in soft waves, showing its complete lower edge', 'fabric_detail', None),
        ('border', 'fabric-only macro of the saree edge and weave in one gentle curved fold', 'border_macro', None),
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
