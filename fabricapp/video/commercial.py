"""Compatibility entry point; the shirt module owns its storyboard."""
from .garments.shirt import COMMERCIAL_PROMPT as PROMPT, DEFINITION


def profile():
    return DEFINITION.resolve('shirt_commercial').profile('shirt')
