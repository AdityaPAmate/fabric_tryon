"""One source-photo animation; preservation takes priority over motion."""
GARMENTS = ('shirt', 'saree', 'kurta', 'kurti_pant', 'pant', 'blazer')
PROMPT = (
    'Locked camera, continuous shot. Sharp focus at start. Right fingertips lightly touch fabric once, then rest at the side; '
    'left arm stays down. Slowly turn in place to show the back, then reverse to face front. '
    'Original background, lighting, face and fabric colour/pattern remain identical throughout.'
)


def select_profile(data):
    return {'version': 'fabric-gimme-sharp-start-v8', 'motion': 'mirror_check',
            'seconds': 8, 'prompt': PROMPT}


PROFILES = {garment: select_profile({'garment_type': garment}) for garment in GARMENTS}
