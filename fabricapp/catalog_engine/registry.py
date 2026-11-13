"""Explicit allowlist: request data never becomes an import path."""
from importlib import import_module
from fabricapp.catalog_engine.legacy import make_definition

CUSTOM = {
    ('shirt', 'classic-v1'): 'fabricapp.ai.garments.shirt.catalog.definition',
    ('saree', 'editorial-v1'): 'fabricapp.ai.garments.saree.catalog.definition',
    ('kurti_pant', 'editorial-v1'): 'fabricapp.ai.garments.kurti_pant.catalog.definition',
    ('kurta', 'plain-v1'): 'fabricapp.ai.garments.kurta.catalog.plain',
    ('kurta', 'sherwani-v1'): 'fabricapp.ai.garments.kurta.catalog.sherwani',
    ('ready_made', 'ready-made-v1'): 'fabricapp.catalog_engine.ready_made',
}
DEFAULTS = {'shirt': 'classic-v1', 'saree': 'editorial-v1',
            'blazer': 'classic-v1', 'kurta': 'classic-v1',
            'kurti_pant': 'editorial-v1', 'pant': 'classic-v1'}
STYLE_EDITIONS = {('kurta', 'plain'): 'plain-v1', ('kurta', 'sherwani'): 'sherwani-v1'}


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
    garment = data.get('garment_type')
    style = data.get('garment_style')
    if data.get('garment_image') is not None and garment is None:
        return get_definition('ready_made', edition or 'ready-made-v1')

    style_edition = STYLE_EDITIONS.get((garment, style))
    if data.get('garment_image') is not None and (not style_edition or edition not in (None, style_edition)):
        raise ValueError('This ready-made garment type and style do not have a catalog edition.')
    if edition in STYLE_EDITIONS.values() and edition != style_edition:
        raise ValueError(f"Catalog edition '{edition}' requires its matching garment type and style.")
    definition = get_definition(garment, edition or style_edition)
    if data.get('garment_image') is not None:
        module = import_module(CUSTOM[(garment, definition.edition)])
        return getattr(module, 'READY_MADE_DEFINITION', definition)
    return definition
