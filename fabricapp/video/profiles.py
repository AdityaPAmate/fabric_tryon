"""One source-photo animation; preservation takes priority over motion."""
GARMENTS = ('shirt', 'saree', 'kurta', 'kurti_pant', 'pant', 'blazer')
PROMPT = (
    'Mirror POV, fixed camera. Person checks outfit front, turns sideways and away to show back, '
    'then reverses to face front. Hands relaxed, clothes intact. Keep same face, fabric colour, '
    'pattern, background and lighting. Natural continuous motion. No full spin, cuts, fades, zoom, text or scene changes.'
)


def select_profile(data):
    return {'version': 'fabric-gimme-lab-mirror-v5', 'motion': 'mirror_check',
            'seconds': 8, 'prompt': PROMPT}


PROFILES = {garment: select_profile({'garment_type': garment}) for garment in GARMENTS}
