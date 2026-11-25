"""Separate PixVerse V6 storyboard; the two existing Gimmeclip prompts stay intact."""
PROMPT = (
    'Create an 8-second ultra-realistic premium cinematic fashion commercial from the reference image. '
    'The shirt is the product and visual hero, not trousers, shoes or the model. '
    '0-1.5s Collar Reveal: extreme close-up of collar, upper chest and buttons; slow smooth horizontal '
    'camera slide showing original weave, texture and stitching, with soft directional cinematic light. '
    '1.5-3s Sleeve Detail: clean cinematic cut to sleeve and cuff close-up, subtle natural arm movement, '
    'sharp fabric, stitching and cuff detail. '
    '3-6s Elegant Walking: medium tracking shot, head to mid-thigh, entire shirt visible collar to hem. '
    'Eye-level three-quarter front view; camera smoothly tracks backward at the same speed as the model. '
    'Confident sophisticated royal attitude, upright posture, relaxed shoulders and natural arms. '
    'Look slightly sideways away from the camera. '
    '6-8s Shirt Hero: continue walking; smoothly shift toward a 35-45-degree front-side angle. '
    'Eye-level or slightly elevated camera, gentle downward angle, tracking alongside. '
    'Keep the SAME head-to-mid-thigh framing and subject size; reveal front, side, sleeve structure, '
    'natural drape and fabric movement. End on a sophisticated shirt-focused composition while walking. '
    'Keep the exact same person, shirt design, colour, texture, pattern scale, buttons, collar, sleeves '
    'and original tucked/untucked fit across every shot. Realistic garment physics, soft consistent '
    'cinematic lighting and a premium neutral architectural background throughout.'
)
NEGATIVE_PROMPT = (
    'Sudden zoom-out, abrupt framing changes, low-angle shots, full-body wide shots, emphasis on '
    'trousers or shoes, direct eye contact, exaggerated walking, excessive fabric wrinkles, fabric '
    'distortion, pattern shifting, garment transformation, camera shaking, flickering, unnatural body movements.'
)


def profile():
    return {'version': 'fabric-pixverse-shirt-commercial-v1', 'motion': 'shirt_commercial',
            'provider': 'cloudflare_pixverse', 'seconds': 8, 'quality': '540p',
            'aspect_ratio': '9:16', 'prompt': PROMPT, 'negative_prompt': NEGATIVE_PROMPT,
            'multi_shot': True}
