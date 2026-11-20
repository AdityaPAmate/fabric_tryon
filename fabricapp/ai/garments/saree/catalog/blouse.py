"""Saree-catalog-only blouse styling, shared by its three wearer views."""

PLAIN_BLOUSE_RULE = (
    'FINAL BLOUSE REQUIREMENT for all front, side and rear catalog views: '
    'the blouse is a separate, fully opaque garment in ONE uniform plain solid colour. '
    'Choose the main BASE colour of the saree BODY in image 1, ignoring the border, '
    'pallu artwork, small motifs, background and skin. Use that SAME blouse colour '
    'in all three views. Never choose skin-coloured or skin-like nude, flesh, beige, '
    'tan or peach shades, and never copy skin colour from the wearer or an identity reference. '
    'If the saree base itself is skin-like, choose a clearly non-skin coordinating '
    'colour actually present in the saree; if none is present, use plain black. '
    'No transferred saree prints, motifs, flowers, dots, stripes, zari, embroidery, '
    'contrasting piping, decorative borders or other designs anywhere on the blouse '
    'or its sleeves, neckline and back. Preserve the requested blouse coverage and '
    'construction; do not recolour the wearer skin or change the saree fabric. '
    'This blouse rule takes priority over conflicting template styling or style notes. '
)


def apply_blouse_policy(config):
    return {**config, 'prompt': config['prompt'] + ' ' + PLAIN_BLOUSE_RULE,
            'prompt_version': config['prompt_version'] + '-plain-blouse-v1'}
