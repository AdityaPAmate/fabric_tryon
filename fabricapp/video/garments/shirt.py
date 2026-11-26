"""Existing shirt prompts, versions and output behavior are preserved."""
from ..contracts import GarmentVideoDefinition, VideoStyle
from .shirt_prompts import PROMPT, WALKING_PROMPT, COMMERCIAL_PROMPT


DEFINITION = GarmentVideoDefinition(
    'shirt', 'Shirt', 'mirror_check',
    (
        VideoStyle('mirror_check', 'Current inspection', 'fabric-gimme-sharp-start-v8', PROMPT,
                   '8s continuous shirt inspection; original background and fabric.'),
        VideoStyle('walking', 'Walking / catwalk', 'fabric-gimme-walking-v1', WALKING_PROMPT,
                   '8s continuous shot with three slow forward steps.'),
    ), 'Use a clear shirt image. Commercial needs one visible face, collar and upper chest.',
    compatibility_styles=(VideoStyle(
        'shirt_commercial', 'Cinematic shirt commercial', 'fabric-gimme-shirt-commercial-v7',
        COMMERCIAL_PROMPT,
        '8s: original-image collar slide (2s), then Gimmeclip sleeve, waist-up and front walking; slightly elevated camera.',
        renderer='shirt_collar', allow_cuts=True),),
)
