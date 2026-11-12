"""Describe sampled swatch colours without recolouring the provider inputs."""
import colorsys
from PIL import Image


def colour_name(rgb):
    h, lightness, saturation = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    hue = h * 360
    if max(rgb) - min(rgb) < 9:
        return 'white' if lightness > .92 else 'light grey' if lightness > .7 else 'grey' if lightness > .25 else 'near-black'
    if lightness > .84 and 30 <= hue <= 70:
        return 'warm ivory-cream'
    if hue < 15 or hue >= 345:
        family = 'red'
    elif hue < 45:
        family = 'orange-brown'
    elif hue < 70:
        family = 'yellow'
    elif hue < 160:
        family = 'green'
    elif hue < 200:
        family = 'teal blue-green'
    elif hue < 255:
        family = 'blue'
    elif hue < 305:
        family = 'lavender-purple'
    else:
        family = 'pink-magenta'
    tone = 'light ' if lightness > .7 else 'deep ' if lightness < .3 else ''
    if saturation < .2:
        tone += 'muted '
    return tone + family


def measure_fabric_colours(source, crop_box=None, *, palette_size=5, min_coverage=.03):
    """Sample original RGB pixels; restore the caller's stream even on failure.

    Nearest-neighbour sampling avoids averaging tiny print colours together.
    These are uncalibrated image RGB values, not physical fabric measurements.
    Palette order is coverage, not a claim about which colour is base/print.
    """
    position = source.tell()
    try:
        source.seek(0)
        with Image.open(source) as opened:
            image = opened.convert('RGB')
        if crop_box is not None:
            image = image.crop(crop_box)
        image.thumbnail((256, 256), Image.Resampling.NEAREST)
        quantized = image.quantize(colors=palette_size, method=Image.Quantize.MEDIANCUT,
                                   dither=Image.Dither.NONE)
        palette = quantized.getpalette()
        total = image.width * image.height
        colours = []
        for count, index in sorted(quantized.getcolors(), reverse=True):
            if count / total < min_coverage:
                continue
            rgb = palette[index * 3:index * 3 + 3]
            colours.append({'rgb': rgb, 'hex': '#' + ''.join(f'{v:02X}' for v in rgb),
                            'name': colour_name(rgb), 'coverage': round(count / total, 4)})
        return {'sample_size': list(image.size), 'crop_box': crop_box,
                'method': 'original RGB, nearest sampling, median-cut palette',
                'colours': colours}
    finally:
        source.seek(position)


def _lit_neutral_cloth(colours):
    """Find a broad lit shade on low-chroma cloth photographed with fold shadows."""
    neutral = sorted((c for c in colours if max(c['rgb']) - min(c['rgb']) <= 18),
                     key=lambda c: sum(c['rgb']))
    share = sum(c['coverage'] for c in neutral)
    if share < .65:
        return None

    def shade_at(fraction):
        cumulative = 0
        for colour in neutral:
            cumulative += colour['coverage']
            if cumulative >= share * fraction:
                return colour
        return neutral[-1]

    middle = shade_at(.50)
    lit = shade_at(.92)
    middle_level, lit_level = sum(middle['rgb']) / 3, sum(lit['rgb']) / 3
    # A narrow tonal range or a dark lit shade is insufficient evidence to lift the base.
    if lit_level < 198 or lit_level - middle_level < 18:
        return None
    # A two-tone design can have the same endpoints without a gradient between them.
    between = sum(c['coverage'] for c in neutral if middle_level + 5 < sum(c['rgb']) / 3 < lit_level - 5)
    if between < share * .10:
        return None
    return lit


def patterned_fabric_colour_prompt(profile, target):
    """Anchor a clear majority colour while leaving motif placement to the swatch."""
    colours = profile['colours']
    if not colours:
        return ''

    def nearby(first, second):
        return sum((a - b) ** 2 for a, b in zip(first['rgb'], second['rgb'])) <= 24 ** 2

    def coverage(group):
        return sum(colour['coverage'] for colour in group)

    groups = [[colour for colour in colours if nearby(colour, anchor)] for anchor in colours]
    majority = max(groups, key=coverage)
    share = coverage(majority)
    prompt = f'COLOUR REFERENCE: use image 1 as the colour authority for the {target}. '
    lit = _lit_neutral_cloth(colours)
    if lit:
        prompt += (f'Use the well-lit cloth sample ({lit["hex"]}) for the base under neutral studio light. '
                   'The darker neutral tones in the swatch are fold shading. Match the lit base across '
                   'broad visible areas and keep natural shadows local to the new folds. Preserve the '
                   'source tint and keep each printed motif visible at its original size. ')
        remaining = [c for c in colours if max(c['rgb']) - min(c['rgb']) > 18]
    elif share >= .60:
        rgb = [round(sum(colour['rgb'][i] * colour['coverage'] for colour in majority) / share)
               for i in range(3)]
        hex_value = '#' + ''.join(f'{value:02X}' for value in rgb)
        prompt += f'Anchor the dominant cloth midtone to {colour_name(rgb)} ({hex_value}). '
        remaining = [colour for colour in colours if colour not in majority]
    else:
        prompt += 'Keep all the fabric colours distinct, with their original proportions. '
        remaining = colours

    # List a few distinct samples without filling the prompt with shades of one colour.
    samples = []
    for colour in remaining:
        if all(not nearby(colour, sample) for sample in samples):
            samples.append(colour)
            if len(samples) == 4:
                break
    if samples:
        prompt += 'Sampled colours from image 1: ' + ', '.join(c['hex'] for c in samples) + '. '
    prompt += 'Use the swatch pixels to keep each colour in its original motifs, checks, stripes or borders. '
    if not lit:
        prompt += 'Match the swatch lightness and saturation in diffuse midtones across the garment. '
    return prompt + 'Keep natural fold shadows and highlights while avoiding a colour cast from the scene. '


def colour_reference_prompt(profile, target="jacket", *, preserve_palette=False):
    if not profile or not profile['colours']:
        return ''
    if has_single_colour_family(profile) and not preserve_palette:
        total = sum(c['coverage'] for c in profile['colours'])
        rgb = [round(sum(c['rgb'][channel] * c['coverage'] for c in profile['colours']) / total)
               for channel in range(3)]
        colour_hex = '#' + ''.join(f'{v:02X}' for v in rgb)
        name = colour_name(rgb)
        if name == 'deep orange-brown':
            name = 'dark chocolate brown'
        return (
            'COLOUR REFERENCE: the ' + target + ' fabric is ' + name + ' (' + colour_hex + '). '
            'This measured swatch colour defines the ' + target
            + (', including its lapels and sleeves. ' if target == 'jacket' else ', across its fabric panels. ')
            + 'Keep this colour family visibly present in the fabric midtones throughout the ' + target + ', '
            'with its original saturation and lightness. Image 1 supplies the fabric details; '
            'fold shading varies around this colour. '
            + ('COLOUR PRIORITY: copy the actual swatch pixels, not a lighter interpretation of the colour name. '
            'Do not auto-brighten a dark swatch, desaturate it to grey, or add an orange/red colour grade. '
            'Use neutral diffuse light on the fabric; keep scene colour casts off the garment. '
            'The original swatch overrides the colour of the person/reference garment. '
            'Preserve dark fabric midtones while keeping seams and folds visible. '
               if name == 'dark chocolate brown' else '')
        )
    entries = '; '.join(f"{c['name']} {c['hex']} (about {round(c['coverage'] * 100)}%)"
                        for c in profile['colours'])
    return (
        'COLOUR REFERENCE: measured colours from the original ' + target + ' fabric swatch: '
        + entries + ('. These are fabric colours, not a conventional business-suit palette. '
                     if target == 'jacket' else '. These values describe the supplied fabric. ')
        + "Keep these hues and their saturation in the " + target + "'s diffuse midtones. "
        'Image 1 determines where each colour belongs in the pattern; the palette '
        'does not replace the pattern with a blended or single colour. Retain '
        'natural fold shading around these midtones. '
    )


def has_single_colour_family(profile):
    """Conservative rollout gate, not a classifier of fabric construction."""
    def family(name):
        for prefix in ('light ', 'deep ', 'muted '):
            name = name.removeprefix(prefix)
        return name
    return bool(profile and profile['colours']) and len({family(c['name']) for c in profile['colours']}) == 1


SHIRT_COLOUR_PRIORITY = (
    'FINAL FABRIC COLOUR: Image 1 is the authority for the exact fabric colours. '
    'Match its base shade, lightness and saturation under neutral diffuse light. '
    'Preserve each printed colour separately and retain its contrast with the base cloth. '
    'Keep realistic local fold shadows, but do not apply a warm or cool cast, boost vibrance, '
    'wash out the print, or inherit the brightness or tint of the original reference cloth. '
    'If a reference garment looks faded, use the original swatch colours instead. '
    'Apply these instructions only to shirt fabric; preserve skin, buttons, trousers and background. '
)
