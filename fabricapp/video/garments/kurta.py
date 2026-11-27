from ..contracts import GarmentVideoDefinition, VideoStyle

# Exact snapshot of the current shirt inspection prompt (sharp-start-v8).
# Keep this local so later shirt edits do not silently change kurta videos.
PROMPT = (
    'Locked camera, continuous shot. Sharp focus at start. Right fingertips lightly touch fabric once, then rest at the side; '
    'left arm stays down. Slowly turn in place to show the back, then reverse to face front. '
    'Original background, lighting, face and fabric colour/pattern remain identical throughout.'
)

DEFINITION = GarmentVideoDefinition(
    'kurta', 'Kurta', 'mirror_check',
    (
        VideoStyle('mirror_check', 'Kurta inspection', 'fabric-gimme-kurta-shirt-inspection-v2', PROMPT,
                   '8s shirt-style inspection: light fabric touch, slow back turn and return to front. Same style for every kurta type.'),
    ), 'Use an image showing the kurta neckline, sleeves and full hem.',
)
