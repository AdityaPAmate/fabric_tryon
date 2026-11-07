"""Existing shirt panel geometry, retained at native front resolution."""
from fabricapp.catalog_engine.contracts import Layout, Panel, Text

SIZE = (1184, 2304)
PANELS = {
    'front': (0, 0, 576, 1920),
    'close_up': (592, 0, 880, 496),
    'back': (896, 0, 1184, 496),
    'collar': (592, 512, 1184, 992),
    'cuff': (592, 1008, 1184, 1456),
    'hem': (592, 1472, 1184, 1920),
}
OUTPUT_SIZES = {key: ((box[2] - box[0]) * (1 if key == 'front' else 2),
                      (box[3] - box[1]) * (1 if key == 'front' else 2))
                for key, box in PANELS.items()}


def get_layout(product=None):
    return Layout('portrait-catalog-v4', SIZE,
                  tuple(Panel(key, box) for key, box in PANELS.items()),
                  (24, 1936, 1160, 2232),
                  (Text('FABRIC SWATCH', (592, 2268), 30, 1100, fill='black', anchor='mm'),))
