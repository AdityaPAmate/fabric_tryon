"""Catalog copies are independent of the single-image pose reference assets."""
from fabricapp.ai.references.catalog_reference import CATALOG_REFERENCE_DIR

REFERENCES = {
    'front': CATALOG_REFERENCE_DIR / 'saree' / 'saree_royal_front_stand.png',
    'side_portrait': CATALOG_REFERENCE_DIR / 'saree' / 'saree_side_view.png',
    'back_pallu': CATALOG_REFERENCE_DIR / 'saree' / 'back_showing_pallu.jpg',
    'neckline': CATALOG_REFERENCE_DIR / 'saree' / 'saree_neckline.png',
    'pallu': CATALOG_REFERENCE_DIR / 'saree' / 'saree_pallu.png',
    'border': CATALOG_REFERENCE_DIR / 'saree' / 'saree_border.png',
    'pleats': CATALOG_REFERENCE_DIR / 'saree' / 'saree_pleats.png',
}
