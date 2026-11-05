"""Shared illumination policy for the supported non-saree garment paths."""

TARGETS = {
    'shirt': 'shirt',
    'blazer': 'blazer',
    'kurta': 'kurta or sherwani',
    'kurti_pant': 'kurti and matching pants',
    'pant': 'trousers',
}
BALANCED_LIGHTING = (
    "FINAL GARMENT LIGHTING: use a broad, soft, colour-neutral frontal key light "
    "and gentle fill from the opposite side. Balance illumination across the {target}. "
    "Keep smooth transitions from the chest or central panels to the sides. "
    "Use gentle contact shadows beneath collars, lapels, overlaps and seams, "
    "and soften deep shadows at elbows, knees and existing folds. "
    "Retain subtle highlights, visible weave and natural three-dimensional fabric depth. "
    "Keep diffuse fabric midtones faithful to image 1 in hue, saturation and lightness. "
    "Do not brighten dark fabric into a pale shade, grey out saturated fabric, "
    "clip light fabric to pure white, or tint the cloth with background colours. "
    "Keep printed motifs distinct with their original colour contrast. "
    "Keep scene lighting coherent while using neutral fill to protect garment colour. "
    "Preserve the selected material's matte, glossy or plush surface response. "
)


def apply_garment_lighting(config, garment_type):
    if garment_type not in TARGETS:
        return config
    result = dict(config)
    lighting = BALANCED_LIGHTING.format(target=TARGETS[garment_type])
    original_primary = config.get('prompt', '')
    original_fallback = config.get('safety_fallback_prompt', '')
    appended_retry = bool(original_primary and original_fallback.startswith(original_primary))
    for key in ('prompt', 'safety_fallback_prompt'):
        if result.get(key):
            original = result[key]
            # Some shared scene prompts disallow all dark shading. Soften that
            # restriction to retain depth under the new final lighting policy.
            original = original.replace('no dark shadow', 'no harsh dark shadow')
            original = original.replace('NO dark shadow', 'NO harsh dark shadow')
            result[key] = original + lighting
    if appended_retry:
        result['safety_fallback_prompt'] = result['prompt'] + original_fallback[len(original_primary):]
    result['prompt_version'] = result.get('prompt_version', 'garment') + '-lighting-v1'
    return result
