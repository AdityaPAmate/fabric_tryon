from ..contracts import GarmentVideoDefinition, VideoStyle

DEFINITION = GarmentVideoDefinition(
    'saree', 'Saree', 'walking',
    (
        VideoStyle('mirror_check', 'Saree presentation', 'fabric-gimme-saree-presentation-v1',
                   'One continuous front shot, locked camera, sharp start. Stand naturally with a gentle weight shift; arms relaxed. Show the full saree, pallu and border. No turn or pulling. Keep the exact source person, drape, fabric colour, print, border, background and light. No cuts, zoom or redesign.',
                   '8s front presentation; gentle movement with the pallu and border visible.'),
        VideoStyle('walking', 'Saree catwalk - zoom out & turn', 'fabric-gimme-saree-catwalk-v2',
                   'Uncut. 0-4s: start close on saree; smoothly zoom out to full length AS she walks slowly forward. 4-5s: stop. 5-7s: turn 30 degrees. 7-8s: face front again. Relaxed hands; no pulling. Preserve exact source person, saree colour, print, border, pleats, drape, background and light. No cuts or flicker.',
                   '8s: closer saree view > zoom out while walking > stop > slight turn > face front. Hands relaxed; no pallu pulling.',
                   camera_motion='zoom_out'),
    ), 'Use a sharp full-length front image with the entire saree, pallu and hem visible. Send the complete image, not a fabric-only crop.',
)
