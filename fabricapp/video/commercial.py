"""Gimmeclip storyboard for the extra shirt commercial option."""
PROMPT = (
    'Shirt ad: 0-1.5s collar macro slide; 1.5-3s cuff closeup; '
    '3-6s eye-level 3/4 walk, track back; 6-8s 40deg side track. '
    'Keep head-to-mid-thigh size. Same face, shirt colour/print/texture/fit. '
    'Soft light, neutral architecture. Shirt hero. No wide shots, shake, text or eye contact.'
)


def profile():
    return {'version': 'fabric-gimme-shirt-commercial-v1', 'motion': 'shirt_commercial',
            'seconds': 8, 'prompt': PROMPT, 'multi_shot': True}
