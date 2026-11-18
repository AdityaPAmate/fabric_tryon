"""Build the canvas used by the classic compatibility editions."""
from fabricapp.catalog_engine.contracts import Panel, Layout, Text

BOXES = ((0, 0, 760, 2520), (772, 0, 1280, 894), (1292, 0, 1800, 894),
         (772, 906, 1800, 1572), (772, 1584, 1800, 2052), (772, 2064, 1800, 2520))


def classic_layout(shots):
    panels = tuple(
        Panel(shot.key, box, 'contain' if shot.key in ('cuff', 'sleeve', 'hem') else 'cover')
        for shot, box in zip(shots, BOXES)
    )
    swatch_title = Text('FABRIC SWATCH', (900, 3132), 40, 1700, anchor='mm')
    return Layout('portrait-catalog-v2', (1800, 3200), panels,
                  (36, 2544, 1764, 3072), (swatch_title,))
