"""Gimmeclip storyboard for the extra shirt commercial option."""
PROMPT = (
    '0-2s collar/button close-up, camera slides. Cut 2-3s cuff close-up. '
    'Cut 3-6s front 3/4 walk TOWARD camera; camera tracks BACKWARD. '
    '6-8s camera tracks alongside. Head-to-mid-thigh. '
    'Same face, shirt fabric/colour/fit, background/light. Arms relaxed. '
    'No back view, shirt touching, wide shot or zoom-out.'
)


def profile():
    return {'version': 'fabric-gimme-shirt-commercial-v2', 'motion': 'shirt_commercial',
            'seconds': 8, 'prompt': PROMPT, 'multi_shot': True}
