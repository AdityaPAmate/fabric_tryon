"""Six photographs, three columns, no typography; exact 9:16 export."""
from fabricapp.catalog_engine.contracts import Layout, Panel

SIZE = (1800, 3200)
GUTTER = 12
PANELS = {
    'front': (0, 0, 736, 3200),
    'side_portrait': (748, 0, 1272, 1456),
    'back_pallu': (748, 1468, 1272, 3200),
    'fabric_texture': (1284, 0, 1800, 1024),
    'border': (1284, 1036, 1800, 1920),
    'pleats': (1284, 1932, 1800, 3200),
}


def _generation_size(box):
    # Provider images are capped at 1920px; retain each narrow panel's aspect.
    width, height = box[2] - box[0], box[3] - box[1]
    scale = min(1, 1920 / max(width, height))
    return tuple(max(256, round(value * scale / 32) * 32) for value in (width, height))


OUTPUT_SIZES = {key: _generation_size(box) for key, box in PANELS.items()}


def get_layout(product=None):
    # Legacy product metadata is accepted by the API but deliberately never drawn.
    return Layout('saree-six-panel-9x16-v3', SIZE,
                  tuple(Panel(key, box, 'cover') for key, box in PANELS.items()),
                  background='white')
