from ..contracts import GarmentVideoDefinition, VideoStyle

# One continuous kurta showcase, independent of shirt prompts and local crops.
PROMPT = (
    'Single take. 0-2s chest fabric close-up; 2-4s pull back, turn only 30deg, front visible; '
    '4-6s two slow forward steps, camera backs in sync; 6-8s hold front pose. Full kurta/hem after reveal. '
    'Arms relaxed. Exact source fabric/colour/print scale/texture/details/person/background/light. No back view.'
)

DEFINITION = GarmentVideoDefinition(
    'kurta', 'Kurta', 'kurta_commercial',
    (
        VideoStyle('kurta_commercial', 'Kurta cinematic commercial', 'fabric-gimme-kurta-commercial-v3', PROMPT,
                   '8s continuous take: chest fabric detail, slight 30-degree turn with front visible, two slow steps, then a steady front pose. Full kurta and hem after reveal.',
                   camera_motion='zoom_out'),
    ), 'Use a sharp, front-facing image showing the complete kurta neckline, sleeves and hem.',
)
