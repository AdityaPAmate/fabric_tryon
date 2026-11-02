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


def measure_fabric_colours(source, crop_box=None):
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
        quantized = image.quantize(colors=5, method=Image.Quantize.MEDIANCUT,
                                   dither=Image.Dither.NONE)
        palette = quantized.getpalette()
        total = image.width * image.height
        colours = []
        for count, index in sorted(quantized.getcolors(), reverse=True):
            if count / total < .03:
                continue
            rgb = palette[index * 3:index * 3 + 3]
            colours.append({'rgb': rgb, 'hex': '#' + ''.join(f'{v:02X}' for v in rgb),
                            'name': colour_name(rgb), 'coverage': round(count / total, 4)})
        return {'sample_size': list(image.size), 'crop_box': crop_box,
                'method': 'original RGB, nearest sampling, median-cut palette',
                'colours': colours}
    finally:
        source.seek(position)


def colour_reference_prompt(profile, target="jacket"):
    if not profile or not profile['colours']:
        return ''
    if has_single_colour_family(profile):
        total = sum(c['coverage'] for c in profile['colours'])
        rgb = [round(sum(c['rgb'][channel] * c['coverage'] for c in profile['colours']) / total)
               for channel in range(3)]
        colour_hex = '#' + ''.join(f'{v:02X}' for v in rgb)
        return (
            'COLOUR REFERENCE: the ' + target + ' fabric is ' + colour_name(rgb) + ' (' + colour_hex + '). '
            'This measured swatch colour defines the ' + target
            + (', including its lapels and sleeves. ' if target == 'jacket' else ', across its fabric panels. ')
            + 'Keep this colour family visibly present in the fabric midtones throughout the ' + target + ', '
            'with its original saturation and lightness. Image 1 supplies the fabric details; '
            'fold shading varies around this colour. '
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
