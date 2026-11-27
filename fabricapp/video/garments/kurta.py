from ..contracts import GarmentVideoDefinition, VideoStyle

# Kurta-specific commercial: full hem framing, independent of shirt prompts/crops.
PROMPT = (
    '0-2s neckline/buttons, slow slide left-right. 2-3.5s sleeve, gentle arm motion. '
    '3.5-5s kurta neck-to-hem. 5-8s slow front walk; slightly elevated camera tracks backward, hem in frame. '
    'Arms relaxed. Exact source person/fabric/colour/print/weave/embroidery/buttons/fit/background/light. No side view.'
)

DEFINITION = GarmentVideoDefinition(
    'kurta', 'Kurta', 'kurta_commercial',
    (
        VideoStyle('kurta_commercial', 'Kurta cinematic commercial', 'fabric-gimme-kurta-commercial-v1', PROMPT,
                   '8s: neckline slide, sleeve detail, neck-to-hem view, then slow front walk with a slightly elevated camera. One style for every kurta type.',
                   allow_cuts=True),
    ), 'Use an image showing the kurta neckline, sleeves and full hem.',
)
