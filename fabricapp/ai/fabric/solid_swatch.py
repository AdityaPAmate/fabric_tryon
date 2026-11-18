"""Measure the base RGB of a single-colour swatch."""
import numpy as np

from fabricapp.ai.fabric.fabric_colour import has_single_colour_family


def solid_swatch_rgb(profile):
    """Recognise solid hues with shading while leaving multicolour prints alone."""
    if not has_single_colour_family(profile):
        return None
    colours = profile['colours']
    if sum(c['coverage'] for c in colours) < .85:
        return None
    return np.average([c['rgb'] for c in colours], axis=0,
                      weights=[c['coverage'] for c in colours])
