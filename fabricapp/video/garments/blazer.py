from ..contracts import GarmentVideoDefinition, VideoStyle

DEFINITION = GarmentVideoDefinition(
    'blazer', 'Blazer', 'mirror_check',
    (
        VideoStyle('mirror_check', 'Blazer presentation', 'fabric-gimme-blazer-presentation-v1',
                   'Continuous front shot, locked camera, sharp start. Frame head to mid-thigh; full blazer visible. Stand naturally, arms relaxed, gentle weight shift. No turn or pulling. Preserve source fabric colour, print, lapels, buttons, pockets, fit, person, background and light. No cuts or zoom.',
                   '8s front presentation showing the lapels, buttons and blazer hem.'),
        VideoStyle('walking', 'Blazer walking', 'fabric-gimme-blazer-walking-v1',
                   'Continuous front shot, locked camera, sharp start. Take two small slow steps forward, arms relaxed. Frame head to mid-thigh; show the full blazer. No turn or pulling. Preserve source fabric colour, print, lapels, buttons, pockets, fit, person, background and light. No cuts, zoom or redesign.',
                   '8s restrained forward walk with the full blazer in frame.'),
    ), 'Use a front image showing the lapels, sleeves, pockets and blazer hem.',
)
