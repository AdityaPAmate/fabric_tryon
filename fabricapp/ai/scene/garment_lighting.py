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

SHIRT_LIGHTING = (
    "FINAL GARMENT LIGHTING: photograph the shirt in open shade with soft, "
    "colour-neutral ambient daylight, evenly reaching both shoulders, both sleeves, "
    "collar, chest and hem. Keep the same diffuse fabric midtones across both sides. "
    "Use low-contrast illumination with gentle contact shadows under collar points, "
    "cuff overlaps, seams and the turned hem. Keep smooth, shallow transitions that "
    "show the existing fabric volume, weave and original colour contrast naturally. "
    "Image 1 is the fabric colour reference: preserve its hue, saturation and midtone "
    "lightness, including every printed colour separately. Keep white fabric white, "
    "cream fabric cream and dark fabric dark. No direct sunlight on the shirt, "
    "dramatic key light, bright patches, yellow cast, background colour spill or "
    "artificial brightening of the cloth. Preserve the material's natural matte, "
    "silk or velvet surface response without glaring highlights. "
)



def apply_garment_lighting(config, garment_type, *, reference_detail=False):
    if garment_type not in TARGETS:
        return config
    result = dict(config)
    lighting = (SHIRT_LIGHTING if garment_type == 'shirt'
                else BALANCED_LIGHTING.format(target=TARGETS[garment_type]))
    if garment_type == 'shirt' and reference_detail:
        # Detail references already fix the crop. Naming full-body regions here
        # can encourage the model to reconstruct a wider view of the person.
        lighting = lighting.replace(
            'evenly reaching both shoulders, both sleeves, collar, chest and hem. '
            'Keep the same diffuse fabric midtones across both sides. ',
            'evenly reaching only the visible cloth within the existing crop. '
            'Preserve the reference composition. ',
        ).replace(
            'under collar points, cuff overlaps, seams and the turned hem',
            'at the existing seams, folds and fabric overlaps',
        )
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
    result['prompt_version'] = result.get('prompt_version', 'garment') + ('-lighting-v3-open-shade' if garment_type == 'shirt' else '-lighting-v1')
    return result
