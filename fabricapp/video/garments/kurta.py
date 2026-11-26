from ..contracts import GarmentVideoDefinition, VideoStyle

DEFINITION = GarmentVideoDefinition(
    'kurta', 'Kurta', 'mirror_check',
    (
        VideoStyle('mirror_check', 'Kurta presentation', 'fabric-gimme-kurta-presentation-v1',
                   'One continuous front shot, locked camera, sharp start. Stand naturally with a gentle weight shift and relaxed arms. Keep the kurta visible from neck to hem. No turn or pulling. Preserve exact source fabric colour, print, embroidery, buttons, fit, person, background and light. No cuts or zoom.',
                   '8s front presentation; keep the entire kurta visible.'),
        VideoStyle('walking', 'Kurta walking', 'fabric-gimme-kurta-walking-v1',
                   'One continuous front shot, locked camera, sharp start. Take two slow small steps forward with relaxed arms. Keep the entire kurta from neck to hem in frame. No turn or pulling. Preserve exact source fabric colour, print, embroidery, buttons, fit, person, background and light. No cuts or zoom.',
                   '8s slow forward walk with the neckline, sleeves and hem visible.'),
    ), 'Use an image showing the kurta neckline, sleeves and full hem.',
)
