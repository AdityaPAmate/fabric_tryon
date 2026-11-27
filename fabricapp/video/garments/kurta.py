from ..contracts import GarmentVideoDefinition, VideoStyle

# AI supplies motion; kurta_details fixes sleeve/neckline/widening shot framing.
PROMPT = (
    '0-2s stand facing lens; left fingers lightly straighten right sleeve edge once. 2-3.5s hands rest. '
    '3.5-8s take TWO slow small steps TOWARD lens. Chest faces lens throughout. '
    'Keep framing steady, full kurta/hem visible. Exact source fabric colour/print scale/texture/details, person, background/light.'
)

DEFINITION = GarmentVideoDefinition(
    'kurta', 'Kurta', 'kurta_commercial',
    (
        VideoStyle('kurta_commercial', 'Kurta cinematic commercial', 'fabric-gimme-kurta-commercial-v5', PROMPT,
                   '8s: sleeve adjustment close-up (0-2s), neckline detail (2-3.5s), then a widening front walk showing the full kurta and hem. Faces the camera throughout.',
                   renderer='kurta_details', allow_cuts=True, camera_motion='zoom_out'),
    ), 'Use a sharp, front-facing image showing the complete kurta neckline, sleeves and hem.',
)
