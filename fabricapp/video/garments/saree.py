from ..contracts import GarmentVideoDefinition, VideoStyle

DEFINITION = GarmentVideoDefinition(
    'saree', 'Saree', 'walking',
    (
        VideoStyle('mirror_check', 'Saree presentation', 'fabric-gimme-saree-presentation-v1',
                   'One continuous front shot, locked camera, sharp start. Stand naturally with a gentle weight shift; arms relaxed. Show the full saree, pallu and border. No turn or pulling. Keep the exact source person, drape, fabric colour, print, border, background and light. No cuts, zoom or redesign.',
                   '8s front presentation; gentle movement with the pallu and border visible.'),
        VideoStyle('walking', 'Saree catwalk - zoom out & turn', 'fabric-gimme-saree-catwalk-v3',
                   'Uncut. 0-4s: slowly zoom out from saree close-up AS she takes ONLY TWO slow short steps. 4-8s: stop, feet planted; slowly pivot right 15 degrees MAX, REVERSE to front. No spin/back view/pulling. Preserve exact source person, saree colour/print/border/pleats/drape, background/light. Relaxed hands.',
                   '8s: zoom out with only 2 slow short steps, then a gentle 15-degree pivot and reverse to front. No spin or back view.',
                   camera_motion='zoom_out'),
    ), 'Use a sharp full-length front image with the entire saree, pallu and hem visible. Send the complete image, not a fabric-only crop.',
)
