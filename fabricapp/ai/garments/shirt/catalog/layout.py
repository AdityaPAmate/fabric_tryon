"""Existing shirt panel geometry, retained at native front resolution."""
from fabricapp.catalog_engine.contracts import Layout, Panel, Text

SIZE = (1296, 2304)  # Exact 9:16; native photographs retain their dimensions.
PANELS = {
    'front': (0, 0, 576, 1920),
    'close_up': (592, 0, 880, 496),
    'back': (896, 0, 1184, 496),
    'collar': (592, 512, 1184, 992),
    'cuff': (592, 1008, 1184, 1456),
    'hem': (592, 1472, 1184, 1920),
}
PANELS = {key: (box[0] + 56, box[1], box[2] + 56, box[3]) for key, box in PANELS.items()}
OUTPUT_SIZES = {key: ((box[2] - box[0]) * (1 if key == 'front' else 2),
                      (box[3] - box[1]) * (1 if key == 'front' else 2))
                for key, box in PANELS.items()}


def get_layout(product=None):
    return Layout('portrait-catalog-9x16-v5', SIZE,
                  tuple(Panel(key, box) for key, box in PANELS.items()),
                  (80, 1936, 1216, 2232),
                  (Text('FABRIC SWATCH', (648, 2268), 30, 1100, fill='black', anchor='mm'),))
