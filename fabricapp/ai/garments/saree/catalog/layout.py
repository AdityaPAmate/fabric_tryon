"""Seven panels matching the supplied editorial arrangement; facts are request data."""
from fabricapp.catalog_engine.contracts import Layout, Panel, Text

SIZE = (1800, 3200)  # Exact 9:16, including header and footer.
PANELS = {
    'front': (40, 180, 880, 1700),
    'side_portrait': (896, 180, 1320, 820),
    'back_pallu': (1336, 180, 1760, 820),
    'neckline': (896, 836, 1760, 1436),
    'pallu': (40, 1716, 880, 2500),
    'border': (40, 2516, 880, 2960),
    'pleats': (896, 1452, 1760, 2960),
}
# Provider dimensions are bounded and aligned to 32 pixels. Composition never stretches.
OUTPUT_SIZES = {key: (max(256, min(1536, round((box[2]-box[0])/32)*32)),
                      max(256, min(1536, round((box[3]-box[1])/32)*32)))
                for key, box in PANELS.items()}


def get_layout(product=None):
    product = product or {}
    texts = [
        Text(product.get('title', 'SAREE'), (40, 24), 90, 330, font='serif'),
        Text(product.get('collection', 'PREMIUM SAREE COLLECTION'), (400, 40), 25, 840),
        Text(product.get('subtitle', 'CLASSIC  ·  ELEGANT  ·  TIMELESS'), (400, 90), 20, 850),
        Text(product.get('badge', 'PRODUCT CATALOGUE'), (1390, 62), 21, 360, fill='#7d2436'),
        Text(product.get('product_name', 'Saree'), (40, 2990), 46, 520, font='serif'),
        Text('PRODUCT CODE: ' + product['product_code'] if product.get('product_code') else '',
             (40, 3060), 20, 520),
        Text('07 VIEWS', (1740, 3160), 20, 180, anchor='rt'),
    ]
    for x, label, field in ((640, 'FABRIC', 'fabric_description'),
                            (1040, 'SAREE LENGTH', 'saree_length'),
                            (1420, 'BLOUSE (UNSTITCHED)', 'blouse_length')):
        if product.get(field):
            texts.extend((Text(label, (x, 3020), 20, 320),
                          Text(product[field], (x, 3065), 30, 320, font='serif')))
    return Layout('saree-editorial-9x16-v2', SIZE,
                  tuple(Panel(key, box, 'contain' if key in ('front', 'back_pallu', 'border') else 'cover')
                        for key, box in PANELS.items()),
                  texts=tuple(texts), lines=((40, 146, 1760, 146), (40, 2976, 1760, 2976)),
                  background='#faf8f5')
