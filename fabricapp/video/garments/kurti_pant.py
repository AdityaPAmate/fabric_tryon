from ..contracts import GarmentVideoDefinition, VideoStyle

DEFINITION = GarmentVideoDefinition(
    'kurti_pant', 'Kurti + Pant', 'mirror_check',
    (
        VideoStyle('mirror_check', 'Kurti + pant presentation', 'fabric-gimme-kurti-pant-presentation-v1',
                   'One continuous front shot, locked camera, sharp start. Stand naturally, arms relaxed, with a gentle weight shift. Show the full kurti and pants. No turn or pulling. Keep BOTH garments exactly as source: colours, prints, fit, neckline and hems. Same person, background and light. No cuts or zoom.',
                   '8s front presentation showing both pieces of the outfit.'),
        VideoStyle('walking', 'Kurti + pant walking', 'fabric-gimme-kurti-pant-walking-v1',
                   'One continuous front shot, locked camera, sharp start. Take two slow small steps forward, arms relaxed. Keep the full kurti and pants in frame. No turn or pulling. Preserve BOTH source garments: colours, prints, fit, neckline and hems. Same person, background and light. No cuts, zoom or redesign.',
                   '8s slow forward walk with both the kurti and pants visible.'),
    ), 'Use a front image showing the whole kurti and pants, including both hems.',
)
