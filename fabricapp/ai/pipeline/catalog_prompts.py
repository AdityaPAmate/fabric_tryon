"""Compatibility helpers. Catalog behavior is owned by each registered edition."""
from fabricapp.catalog_engine.registry import get_definition


def catalog_plan(garment, edition=None):
    return [(shot.key, shot.description) for shot in get_definition(garment, edition).shots]


def edit_config(data, shot, anchor_seed, *, reference_template=None, view=None):
    if data['garment_type'] == 'shirt' and view is None:
        from fabricapp.ai.garments.shirt.catalog.prompts import edit_config as shirt_config
        return shirt_config(data, shot, anchor_seed, reference_template=reference_template, view=view)
    definition = get_definition(data['garment_type'], data.get('catalog_edition'))
    selected = next(item for item in definition.shots if item.key == view or
                    (view is None and item.description == shot))
    return definition.build_config(data, selected, anchor_seed)
