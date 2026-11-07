"""Catalog copies are independent of the single-image pose reference assets."""
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR

REFERENCES = {
    'front': CATALOG_REFERENCE_DIR / 'saree' / '01_front_pallu.png',
    'side_portrait': CATALOG_REFERENCE_DIR / 'saree' / '02_three_quarter.png',
    'back_pallu': CATALOG_REFERENCE_DIR / 'saree' / '03_back_view.png',
    'fabric_texture': CATALOG_REFERENCE_DIR / 'saree' / '04_fabric_texture.png',
    'border': CATALOG_REFERENCE_DIR / 'saree' / '05_border_closeup.png',
    'pleats': CATALOG_REFERENCE_DIR / 'saree' / '06_pleats_hem.png',
}
