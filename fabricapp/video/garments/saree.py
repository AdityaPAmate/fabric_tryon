from ..contracts import GarmentVideoDefinition, VideoStyle

DEFINITION = GarmentVideoDefinition(
    'saree', 'Saree', 'walking',
    (
        VideoStyle('mirror_check', 'Saree presentation', 'fabric-gimme-saree-presentation-v1',
                   'One continuous front shot, locked camera, sharp start. Stand naturally with a gentle weight shift; arms relaxed. Show the full saree, pallu and border. No turn or pulling. Keep the exact source person, drape, fabric colour, print, border, background and light. No cuts, zoom or redesign.',
                   '8s front presentation; gentle movement with the pallu and border visible.'),
        VideoStyle('walking', 'Saree photoshoot - walk & turn', 'fabric-gimme-saree-fitting-v7',
                   'Uncut fitting demo. TWO slow steps, gentle zoom-out. Arms hang at sides, fingers loose. Slowly turn RIGHT to show full BACK, pause, reverse LEFT to front. Keep source hem length and ankle coverage throughout. Keep original feet/accessories, person, fabric colour/print/border/drape and scene/light.',
                   '8s: 2 slow steps > full back > pause > reverse to front. Arms relaxed at sides; keep the original saree length, ankle coverage and accessories.',
                   camera_motion='zoom_out'),
    ), 'Use a sharp full-length front image with the entire saree, pallu and hem visible. Send the complete image, not a fabric-only crop.',
)
