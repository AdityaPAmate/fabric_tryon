from ..contracts import GarmentVideoDefinition, VideoStyle

# One continuous kurta showcase, independent of shirt prompts and local crops.
PROMPT = (
    'One frontal take. 0-2s chest fabric close-up; 2-4s widen to full kurta/hem. '
    '4-6s TWO slow steps TOWARD LENS; 6-8s stop facing lens. Camera stays IN FRONT, tracking away. '
    'Chest/shoulders face lens always; arms relaxed. Exact source fabric colour/print scale/texture/details, person, background/light.'
)

DEFINITION = GarmentVideoDefinition(
    'kurta', 'Kurta', 'kurta_commercial',
    (
        VideoStyle('kurta_commercial', 'Kurta cinematic commercial', 'fabric-gimme-kurta-commercial-v4', PROMPT,
                   '8s frontal take: chest fabric detail, widen to the full kurta and hem, two slow steps toward the camera, then stop facing it. Chest and shoulders face the camera throughout.',
                   camera_motion='zoom_out'),
    ), 'Use a sharp, front-facing image showing the complete kurta neckline, sleeves and hem.',
)
