from ..contracts import GarmentVideoDefinition, VideoStyle

DEFINITION = GarmentVideoDefinition(
    'pant', 'Pant', 'mirror_check',
    (
        VideoStyle('mirror_check', 'Pant presentation', 'fabric-gimme-pant-presentation-v1',
                   'One continuous front shot, locked camera, sharp start. Keep pants visible from waistband to ankles. Stand naturally with a slight weight shift; hands stay away from fabric. No turn or pulling. Preserve exact source colour, print, weave, seams, pockets, fit, background and light. No cuts or zoom.',
                   '8s pants-focused presentation; a face is not required.'),
        VideoStyle('walking', 'Pant walking', 'fabric-gimme-pant-walking-v1',
                   'One continuous front shot, locked camera, sharp start. Take two slow small steps forward. Keep pants visible from waistband to ankles; hands stay away from fabric. No turn or pulling. Preserve exact source colour, print, weave, seams, pockets, fit, background and light. No cuts, zoom or redesign.',
                   '8s small forward steps with the waistband and ankles in frame.'),
    ), 'Use an image showing the waistband, both legs and ankles. A face is not required.',
)
