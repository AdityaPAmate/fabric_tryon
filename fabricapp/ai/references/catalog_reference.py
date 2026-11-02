"""Packaged close-up templates; swatch pixels always come from the request."""
from pathlib import Path

CATALOG_REFERENCE_DIR = Path(__file__).resolve().parent / 'assets' / 'catalog'
SHIRT_TEMPLATES = {'collar': 'shirt_collar.png', 'cuff': 'sleeve.png'}


def get_catalog_reference_path(garment_type, view):
    filename = SHIRT_TEMPLATES.get(view) if garment_type == 'shirt' else None
    return CATALOG_REFERENCE_DIR / 'shirt' / filename if filename else None
