"""One continuous mirror-check motion, with the source garment preserved."""
GARMENTS = {'shirt': 'shirt', 'saree': 'saree', 'kurta': 'kurta',
            'kurti_pant': 'kurti and trousers', 'pant': 'trousers', 'blazer': 'blazer'}


def select_profile(data):
    garment = GARMENTS.get(data.get('garment_type'), 'outfit')
    prompt = (f'Keep face and exact {garment} colour, pattern, texture and fit. Mirror POV: '
              'person glances down, smoothly turns slightly sideways to show a little back, '
              'then eases front. Arms stay still. Fixed camera and background. Continuous '
              'natural motion and breathing; no freezes, pauses, cuts or text.')
    return {'version': 'fabric-gimme-mirror-check-v2', 'motion': 'mirror_check',
            'seconds': 8, 'prompt': prompt}


PROFILES = {garment: select_profile({'garment_type': garment}) for garment in GARMENTS}
