"""Keep image choices; select motion appropriate to the starting photo."""
GARMENTS = {'shirt': 'shirt', 'saree': 'saree', 'kurta': 'kurta',
            'kurti_pant': 'kurti and trousers', 'pant': 'trousers', 'blazer': 'blazer'}


def select_profile(data):
    motion = data.get('motion', 'auto')
    if motion == 'auto':
        if data.get('camera_view') == 'close_up':
            motion = 'detail'
        elif data.get('pose') or data.get('person_image') or data.get('_has_person_image') or data.get('camera_view') == 'side':
            motion = 'subtle'
        else:
            motion = 'turn'
    garment = GARMENTS.get(data.get('garment_type'), 'outfit')
    if motion == 'turn':
        prompt = (f'Fixed camera. Person pauses in the starting pose, slowly turns sideways, pauses, '
                  f'then shows the back of the {garment} and holds. Hands stay relaxed and still; '
                  'no touching clothes or gestures. Keep same identity, fabric colour, pattern and background. '
                  'Natural motion. No text, cuts or zoom.')
    elif motion == 'detail':
        prompt = ('Fixed close-up camera. Preserve the original crop, fabric colour, pattern, texture '
                  'and garment details. Only gentle natural fabric movement. Keep the body and hands '
                  'still. No turning, gestures, text, cuts, zoom or background changes.')
    else:
        prompt = (f'Fixed camera. Preserve the exact starting pose and {garment}. Only gentle breathing '
                  'and tiny natural weight shifts. Hands remain still in their original position. '
                  'Keep same identity, fabric colour, pattern and background. No walking, turning, '
                  'gestures, text, cuts or zoom.')
    return {'version': f'fabric-gimme-{motion}-v1', 'motion': motion, 'seconds': 8, 'prompt': prompt}


PROFILES = {garment: select_profile({'garment_type': garment}) for garment in GARMENTS}
