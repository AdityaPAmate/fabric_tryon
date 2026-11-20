"""Six reference-driven shots for the supplied image-only three-column collage."""
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot
from fabricapp.ai.garments.saree.catalog.references import REFERENCES
from fabricapp.ai.garments.saree.catalog.layout import get_layout
from fabricapp.ai.garments.saree.catalog.prompts import build_config
from fabricapp.ai.garments.saree.catalog.product_details import render_product
from fabricapp.ai.garments.saree.catalog.front_crop import resolve_front_crop

SHOTS = tuple(
    Shot(key, description, 'crop' if key == 'pleats' else 'product_source' if key == 'fabric_texture' else 'template_edit', framing,
         reference=None if key == 'pleats' else REFERENCES[key], identity_from=identity,
         dependencies=('front',) if key == 'pleats' else (),
         source_crop=(.06,.50,.99,.94) if key == 'pleats' else None,
         allows_identity_reference=key != 'back_pallu',
         scenario='pose_reference' if identity or key == 'back_pallu' else 'person_photo')
    for key, description, framing, identity in (
        ('front', 'very tall full-length front portrait matching image 0, complete head and saree hem, pallu hanging down the front', 'full_body', 'request'),
        ('side_portrait', 'full-length side-facing portrait matching image 0, natural adult proportions, complete head, lower skirt and floor-level hem inside the frame', 'side_full_body', 'request'),
        ('back_pallu', 'one full-length rear-facing wearer matching image 0, floor-length pallu covering the rear skirt with one continuous floor-touching hem', 'rear_full_body', None),
        ('fabric_texture', 'complete overhead flat-lay of the supplied saree showing body, both side borders and the complete pallu end together', 'full_fabric_layout', None),
        ('border', 'tight hand-held saree drape detail matching the two hands, bangles and hanging cloth folds in image 0; replace only the saree textile', 'hand_drape_detail', None),
        ('pleats', 'lower saree and hanging pallu cropped from the generated front, preserving its exact fabric, folds and lighting', 'front_lower_detail', None),
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
    render_product=render_product,
    resolve_crop=resolve_front_crop,
)
