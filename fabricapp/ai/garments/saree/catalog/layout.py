"""Seven panels matching the supplied editorial arrangement; facts are request data."""
from fabricapp.catalog_engine.contracts import Layout, Panel, Text

PANELS = {
    'front': (40, 176, 1096, 1520),
    'side_portrait': (1112, 176, 1624, 944),
    'back_pallu': (1640, 176, 2152, 944),
    'neckline': (1112, 960, 2152, 1504),
    'pallu': (40, 1536, 1096, 2288),
    'border': (40, 2304, 1096, 2704),
    'pleats': (1112, 1520, 2152, 2704),
}
# Provider dimensions are bounded and aligned to 32 pixels. Composition never stretches.
OUTPUT_SIZES = {key: (max(256, min(1536, round((box[2]-box[0])/32)*32)),
                      max(256, min(1536, round((box[3]-box[1])/32)*32)))
                for key, box in PANELS.items()}


def get_layout(product=None):
    product = product or {}
    texts = [
        Text(product.get('title', 'SAREE'), (52, 22), 105, 400, font='serif'),
        Text(product.get('collection', 'PREMIUM SAREE COLLECTION'), (490, 38), 29, 1000),
        Text(product.get('subtitle', 'CLASSIC  ·  ELEGANT  ·  TIMELESS'), (490, 92), 22, 1000),
        Text(product.get('badge', 'PRODUCT CATALOGUE'), (1710, 60), 25, 420, fill='#7d2436'),
        Text(product.get('product_name', 'Saree'), (52, 2740), 55, 660, font='serif'),
        Text('PRODUCT CODE: ' + product['product_code'] if product.get('product_code') else '',
             (52, 2820), 23, 650),
        Text('07 VIEWS', (2090, 2860), 22, 200, anchor='rt'),
    ]
    for x, label, field in ((780, 'FABRIC', 'fabric_description'),
                            (1280, 'SAREE LENGTH', 'saree_length'),
                            (1740, 'BLOUSE (UNSTITCHED)', 'blouse_length')):
        if product.get(field):
            texts.extend((Text(label, (x, 2760), 23, 400),
                          Text(product[field], (x, 2810), 35, 400, font='serif')))
    return Layout('saree-editorial-v1', (2200, 2900),
                  tuple(Panel(key, box, 'cover') for key, box in PANELS.items()),
                  texts=tuple(texts), lines=((50, 142, 2152, 142), (50, 2724, 2152, 2724)),
                  background='#faf8f5')
