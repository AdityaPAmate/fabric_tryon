"""One source-photo animation; preservation takes priority over motion."""
GARMENTS = ('shirt', 'saree', 'kurta', 'kurti_pant', 'pant', 'blazer')
PROMPT = (
    'Animate this photo in one fluid shot. Lock camera, background, light, exposure, white balance. '
    'Keep exact face, cloth colour, print, texture and fit. Look down, gently swivel torso a little '
    'and return; arms still. No walking, spins, cuts, fades, freezes, zoom, text, relighting or scene changes.'
)


def select_profile(data):
    return {'version': 'fabric-gimme-preserve-scene-v3', 'motion': 'mirror_check',
            'seconds': 8, 'prompt': PROMPT}


PROFILES = {garment: select_profile({'garment_type': garment}) for garment in GARMENTS}
