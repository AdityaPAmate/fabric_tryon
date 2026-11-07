"""Six reference-driven shots for the supplied image-only three-column collage."""
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot
from fabricapp.ai.garments.saree.catalog.references import REFERENCES
from fabricapp.ai.garments.saree.catalog.layout import get_layout
from fabricapp.ai.garments.saree.catalog.prompts import build_config

SHOTS = tuple(
    Shot(key, description, 'template_edit', framing,
         reference=REFERENCES[key], identity_from=identity,
         scenario='pose_reference' if identity or key == 'back_pallu' else 'person_photo')
    for key, description, framing, identity in (
        ('front', 'very tall full-length front portrait matching image 0, complete head and saree hem, pallu hanging down the front', 'full_body', 'request'),
        ('side_portrait', 'tall three-quarter portrait matching image 0 torso angle, hand placement and hanging pallu extent, with the complete head included', 'side_portrait', 'request'),
        ('back_pallu', 'rear-facing full-length reference pose, both hands holding the broad diagonal pallu open, complete head and entire pallu edge visible', 'rear_full_body', None),
        ('fabric_texture', 'extreme close-up of the original fabric surface and weave over soft shallow folds; fill the frame with cloth only, without any border or hem', 'fabric_texture_detail', None),
        ('border', 'close-up of the saree long SIDE EDGE: a narrow continuous border or finished selvedge beside the main body cloth, with the outer edge and background clearly visible', 'side_border_detail', None),
        ('pleats', 'fabric-only waist-to-hem front pleats with the hanging pallu edge beside them, no head or hands', 'pleats_detail', None),
    )
)
def validate_request(data):
    if data.get('gender') in ('men', 'boy'):
        return {'gender': 'This saree edition supports women or girls.'}
    return {}


DEFINITION = CatalogDefinition(
    'saree', 'editorial-v1', SHOTS, build_config, get_layout,
    # Accepted for older clients; the image-only layout ignores all product text.
    product_fields=('title', 'collection', 'subtitle', 'badge', 'product_name', 'product_code',
                    'fabric_description', 'saree_length', 'blouse_length'),
    validate_request=validate_request,
)
