"""Seven explicit reference-driven shots; no changes to the single-image builder."""
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot
from fabricapp.ai.garments.saree.catalog.references import REFERENCES
from fabricapp.ai.garments.saree.catalog.layout import get_layout
from fabricapp.ai.garments.saree.catalog.prompts import build_config

SHOTS = tuple(
    Shot(key, description, 'template_edit', framing,
         dependencies=('front',) if identity == 'front' else (),
         reference=REFERENCES[key], identity_from=identity,
         scenario='pose_reference' if identity else 'person_photo')
    for key, description, framing, identity in (
        ('front', 'full-length front standing pose, complete head to saree hem, pallu spread visibly', 'full_body', 'request'),
        ('side_portrait', 'side/three-quarter portrait from head to hips, pallu draped over shoulder', 'side_portrait', 'front'),
        ('back_pallu', 'full-length rear view showing the spread pallu, complete head and saree hem', 'rear_full_body', 'front'),
        ('neckline', 'tight neckline, opaque blouse and shoulder drape detail; crop above the nose', 'neckline_detail', 'front'),
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
