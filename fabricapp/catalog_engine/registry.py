"""Explicit allowlist: request data never becomes an import path."""
from importlib import import_module
from fabricapp.catalog_engine.legacy import make_definition

CUSTOM = {
    ('shirt', 'classic-v1'): 'fabricapp.ai.garments.shirt.catalog.definition',
    ('saree', 'editorial-v1'): 'fabricapp.ai.garments.saree.catalog.definition',
    ('kurti_pant', 'editorial-v1'): 'fabricapp.ai.garments.kurti_pant.catalog.definition',
    ('ready_made', 'ready-made-v1'): 'fabricapp.catalog_engine.ready_made',
}
DEFAULTS = {'shirt': 'classic-v1', 'saree': 'editorial-v1',
            'blazer': 'classic-v1', 'kurta': 'classic-v1',
            'kurti_pant': 'editorial-v1', 'pant': 'classic-v1'}


def get_definition(garment, edition=None):
    edition = edition or DEFAULTS.get(garment)
    module = CUSTOM.get((garment, edition))
    if module:
        return import_module(module).DEFINITION
    if garment in DEFAULTS and garment != 'shirt' and edition == 'classic-v1':
        return make_definition(garment)
    raise ValueError(f"Unsupported catalog edition '{edition}' for '{garment}'")


def get_request_definition(data):
    edition = data.get('catalog_edition')
    if data.get('garment_image') is not None:
        return get_definition('ready_made', edition or 'ready-made-v1')
    return get_definition(data['garment_type'], edition)
