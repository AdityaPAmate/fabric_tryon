"""One source-photo animation; preservation takes priority over motion."""
GARMENTS = ('shirt', 'saree', 'kurta', 'kurti_pant', 'pant', 'blazer')
PROMPT = (
    'Animate this photo in one uncut take. Keep camera, background, light and exact cloth colour/print fixed. '
    'Person turns in place from front to back, then reverses the same turn to face front; no full spin. '
    'Arms still. Preserve face, texture and fit. No cuts, fades, zoom, scene changes or relighting.'
)


def select_profile(data):
    return {'version': 'fabric-gimme-half-turn-return-v4', 'motion': 'mirror_check',
            'seconds': 8, 'prompt': PROMPT}


PROFILES = {garment: select_profile({'garment_type': garment}) for garment in GARMENTS}
