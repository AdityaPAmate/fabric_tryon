from ..contracts import GarmentVideoDefinition, VideoStyle

DEFINITION = GarmentVideoDefinition(
    'saree', 'Saree', 'walking',
    (
        VideoStyle('mirror_check', 'Saree presentation', 'fabric-gimme-saree-presentation-v1',
                   'One continuous front shot, locked camera, sharp start. Stand naturally with a gentle weight shift; arms relaxed. Show the full saree, pallu and border. No turn or pulling. Keep the exact source person, drape, fabric colour, print, border, background and light. No cuts, zoom or redesign.',
                   '8s front presentation; gentle movement with the pallu and border visible.'),
        VideoStyle('walking', 'Saree catwalk - zoom out & turn', 'fabric-gimme-saree-catwalk-v5',
                   'Uncut. 0-3s: zoom out from saree close-up AS she takes TWO slow short steps. 3-5s: slowly turn RIGHT to full BACK. 5-6s: hold. 6-8s: slowly turn LEFT to front. No spin/dance/anklets/bells/new jewellery/pulling. Keep exact source person, saree colour/print/border/hem/drape, scene/light and footwear.',
                   '8s: zoom out with 2 slow steps > show the full back > pause > reverse direction to face front. No dance, added ankle jewellery or bells; keep original footwear and saree length.',
                   camera_motion='zoom_out'),
    ), 'Use a sharp full-length front image with the entire saree, pallu and hem visible. Send the complete image, not a fabric-only crop.',
)
