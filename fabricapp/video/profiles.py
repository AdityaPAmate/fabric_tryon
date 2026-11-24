"""One source-photo animation; preservation takes priority over motion."""
GARMENTS = ('shirt', 'saree', 'kurta', 'kurti_pant', 'pant', 'blazer')
PROMPT = (
    'Mirror POV, fixed camera. Check outfit front, lightly touch fabric once without gripping, pulling or lifting. '
    'Turn sideways to show back, reverse to front. Hands relaxed. Keep face, fabric colour/pattern, '
    'background and light unchanged. Fluid motion. No full spin, cuts, fades, zoom or text.'
)


def select_profile(data):
    return {'version': 'fabric-gimme-light-touch-v6', 'motion': 'mirror_check',
            'seconds': 8, 'prompt': PROMPT}


PROFILES = {garment: select_profile({'garment_type': garment}) for garment in GARMENTS}
