from ..contracts import GarmentVideoDefinition, VideoStyle

DEFINITION = GarmentVideoDefinition(
    'saree', 'Saree', 'mirror_check',
    (
        VideoStyle('mirror_check', 'Saree presentation', 'fabric-gimme-saree-presentation-v1',
                   'One continuous front shot, locked camera, sharp start. Stand naturally with a gentle weight shift; arms relaxed. Show the full saree, pallu and border. No turn or pulling. Keep the exact source person, drape, fabric colour, print, border, background and light. No cuts, zoom or redesign.',
                   '8s front presentation; gentle movement with the pallu and border visible.'),
        VideoStyle('walking', 'Saree walking', 'fabric-gimme-saree-walking-v1',
                   'One continuous front shot, locked camera, sharp start. Take two small slow steps forward, arms relaxed. Keep the full saree, pallu and border in frame. No turn or pulling. Preserve the source person, drape, fabric colour, print, border, background and lighting. No cuts, zoom or redesign.',
                   '8s restrained forward walk with the full saree visible.'),
    ), 'Use a front image showing the full saree, pallu and border.',
)
