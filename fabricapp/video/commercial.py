"""Gimmeclip storyboard for the extra shirt commercial option."""
PROMPT = (
    '0-2s COLLAR, neck, top buttons macro slide. Cut 2-3s cuff close-up. '
    'Cut 3-6s front 3/4 walk TOWARD camera; camera tracks BACKWARD. '
    '6-8s camera tracks alongside. Head-to-mid-thigh. '
    'EXACT source colour/print/scale/weave/fit in ALL shots. No redesign/recolour. '
    'Same face/background/light. Arms relaxed.'
)


def profile():
    return {'version': 'fabric-gimme-shirt-commercial-v5', 'motion': 'shirt_commercial',
            'seconds': 8, 'prompt': PROMPT, 'multi_shot': True}
