"""Gimmeclip storyboard for the extra shirt commercial option."""
PROMPT = (
    '0-3.5s sleeve/cuff close-up, arm moves gently. 3.5-5s head-to-waist shirt view. '
    '5-8s front waist-up walk TOWARD camera. Slightly elevated camera tracks BACKWARD only. No side view. '
    'EXACT source colour/print/scale/weave/fit in ALL shots. No redesign/recolour. '
    'Same face/background/light. Arms relaxed.'
)


def profile():
    return {'version': 'fabric-gimme-shirt-commercial-v7', 'motion': 'shirt_commercial',
            'seconds': 8, 'prompt': PROMPT, 'multi_shot': True, 'source_collar_opening': True}
