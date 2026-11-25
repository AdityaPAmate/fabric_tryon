"""One source-photo animation; preservation takes priority over motion."""
GARMENTS = ('shirt', 'saree', 'kurta', 'kurti_pant', 'pant', 'blazer')
PROMPT = (
    'Locked camera, continuous shot. Sharp focus at start. Right fingertips lightly touch fabric once, then rest at the side; '
    'left arm stays down. Slowly turn in place to show the back, then reverse to face front. '
    'Original background, lighting, face and fabric colour/pattern remain identical throughout.'
)
WALKING_PROMPT = (
    'Locked camera, continuous shot. Sharp focus at start. Take three slow natural catwalk steps toward the camera, '
    'arms relaxed with small natural swings, then stand still. Keep original framing. '
    'Original background, lighting, face and fabric colour, pattern and fit stay unchanged.'
)
MOTION_CHOICES = (('mirror_check', 'Current inspection'), ('walking', 'Walking / catwalk'))


def select_profile(data):
    if data.get('video_motion') == 'walking':
        return {'version': 'fabric-gimme-walking-v1', 'motion': 'walking',
                'seconds': 8, 'prompt': WALKING_PROMPT}
    return {'version': 'fabric-gimme-sharp-start-v8', 'motion': 'mirror_check',
            'seconds': 8, 'prompt': PROMPT}


PROFILES = {garment: select_profile({'garment_type': garment}) for garment in GARMENTS}
