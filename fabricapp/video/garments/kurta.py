from ..contracts import GarmentVideoDefinition, VideoStyle

# Kurta-specific commercial: full hem framing, independent of shirt prompts/crops.
PROMPT = (
    'Clean cuts. 0-2s neckline close-up, slide L-R. 2-3.5s sleeve, minimal arm motion. '
    '3.5-5s full kurta neck-to-hem. 5-8s slow front walk; camera above chest tracks back in sync, hem visible. '
    'Front-facing, arms relaxed. Same person/garment/colour/print scale/placement/texture/details/background/light.'
)

DEFINITION = GarmentVideoDefinition(
    'kurta', 'Kurta', 'kurta_commercial',
    (
        VideoStyle('kurta_commercial', 'Kurta cinematic commercial', 'fabric-gimme-kurta-commercial-v2', PROMPT,
                   '8s: neckline close-up, sleeve detail, full neck-to-hem view, then front-facing slow walk; camera tracks back at walking speed.',
                   allow_cuts=True),
    ), 'Use a sharp, front-facing image showing the complete kurta neckline, sleeves and hem.',
)
