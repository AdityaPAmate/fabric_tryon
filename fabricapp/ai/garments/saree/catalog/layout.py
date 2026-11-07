"""Six photographs, three columns, no typography; exact 3:4 export."""
from fabricapp.catalog_engine.contracts import Layout, Panel

SIZE = (1800, 2400)
GUTTER = 12
PANELS = {
    'front': (0, 0, 704, 2400),
    'side_portrait': (716, 0, 1256, 1164),
    'back_pallu': (716, 1176, 1256, 2400),
    'fabric_texture': (1268, 0, 1800, 820),
    'border': (1268, 832, 1800, 1536),
    'pleats': (1268, 1548, 1800, 2400),
}


def _generation_size(box):
    # Provider images are capped at 1920px; retain each narrow panel's aspect.
    width, height = box[2] - box[0], box[3] - box[1]
    scale = min(1, 1920 / max(width, height))
    return tuple(max(256, round(value * scale / 32) * 32) for value in (width, height))


OUTPUT_SIZES = {key: _generation_size(box) for key, box in PANELS.items()}


def get_layout(product=None):
    # Legacy product metadata is accepted by the API but deliberately never drawn.
    return Layout('saree-six-panel-3x4-v4', SIZE,
                  tuple(Panel(key, box, 'cover') for key, box in PANELS.items()),
                  background='white')
