"""Packaged close-up templates; swatch pixels always come from the request."""
from pathlib import Path

CATALOG_REFERENCE_DIR = Path(__file__).resolve().parent / 'assets' / 'catalog'


def get_catalog_reference_path(garment_type, view, edition=None):
    from fabricapp.catalog_engine.registry import get_definition
    try:
        definition = get_definition(garment_type, edition)
    except ValueError:
        return None
    return next((shot.reference for shot in definition.shots if shot.key == view), None)
