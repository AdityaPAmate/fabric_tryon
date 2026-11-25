"""Gimmeclip storyboard for the extra shirt commercial option."""
PROMPT = (
    'Shirt ad. Start tight collar close-up; cut to cuff close-up. '
    'Then model walks TOWARD camera, head-to-mid-thigh crop, feet NEVER visible. '
    'Camera tracks BACKWARD then alongside at eye level. '
    'Keep exact person, shirt fabric/colour/fit, background and light. '
    'Arms relaxed. No back view or shirt touching.'
)


def profile():
    return {'version': 'fabric-gimme-shirt-commercial-v3', 'motion': 'shirt_commercial',
            'seconds': 8, 'prompt': PROMPT, 'multi_shot': True}
