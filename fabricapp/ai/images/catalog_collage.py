"""Compatibility facade; new code renders an explicit catalog Layout."""
from fabricapp.catalog_engine.renderer import render_catalog
from fabricapp.catalog_engine.contracts import Layout, Panel, Text
from fabricapp.catalog_engine.legacy import BOXES
from fabricapp.ai.garments.shirt.catalog.layout import (
    PANELS as SHIRT_PANELS, OUTPUT_SIZES as SHIRT_OUTPUT_SIZES, SIZE as SHIRT_SIZE,
)
from fabricapp.ai.garments.shirt.catalog.layout import get_layout as shirt_layout

LAYOUT = 'portrait-catalog-v4'
SIZE = (1800, 3200)
SHIRT_FRONT_SIZE = (576, 1920)


def catalog_layout(views):
    return LAYOUT if tuple(views) == tuple(SHIRT_PANELS) else 'portrait-catalog-v2'


def compose_catalog(shots, swatch, views):
    if len(views) != 6 or any(view not in shots for view in views):
        raise ValueError('All six catalog views are required')
    if tuple(views) == tuple(SHIRT_PANELS):
        layout = shirt_layout()
    else:
        layout = Layout('portrait-catalog-v2', SIZE,
                        tuple(Panel(view, box, 'contain' if view in ('close_up', 'cuff', 'sleeve', 'hem') else 'cover')
                              for view, box in zip(views, BOXES)),
                        (36, 2544, 1764, 3072),
                        (Text('FABRIC SWATCH', (900, 3132), 40, 1700, fill='black', anchor='mm'),))
    return render_catalog(shots, swatch, layout)
