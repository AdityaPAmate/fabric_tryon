# Shirt catalog navy-trouser reference edits

The three editorial portrait references now use plain dark navy trousers,
matching the separate trousers already present in `hem.png`. The Shirt catalog
preserves this trouser colour independently of the uploaded shirt fabric.

Generator: built-in `image_gen` image editing, one edit per photograph.
The generated PNGs were visually reviewed and copied into the existing asset
paths. No manual recolouring or resizing was applied afterwards.

| Project asset | Saved size | Colour reference |
|---|---|---|
| `fabricapp/ai/references/assets/catalog/shirt/01_front.png` | 724 × 2172 | `hem.png` |
| `fabricapp/ai/references/assets/catalog/shirt/02_side.png` | 1024 × 1536 | `hem.png` |
| `fabricapp/ai/references/assets/catalog/shirt/03_back.png` | 1023 × 1538 | `hem.png` |

The original rear photograph was 1022 × 1538; the editor returned one extra
column. Its portrait framing remains visually the same, and output dimensions
remain on the existing model size grid. The original white-trouser references
are retained in Git history before this change.

## Final generation prompt set

For each edit, input 1 was the corresponding original portrait and input 2 was
the unchanged `hem.png` photograph, used only as a trouser-colour reference.

### Front

Use case: precise-object-edit. Create ONE edited version of the FIRST input image, the narrow full-length FRONT shirt catalog reference. The SECOND input image (a waist-level shirt-hem close-up) is only the trousers COLOUR reference, not a pose or composition reference. Change ONLY the white trousers in image 1 to the SAME solid very dark navy blue fabric colour as the trousers below the white shirt hem in image 2 (approximate diffuse midtone #202637, with natural darker creases). Make both complete trouser legs plain, uniformly navy, no patterns, no stripes, no added trim. Preserve the original trouser cut, knee creases, hems and natural 3D folds. Keep EVERYTHING else in the first image unchanged: the person's exact face and hair, skin, hands, pose, white shirt including full sleeves and untucked curved hem, watch, polished black shoes, grey studio backdrop, lighting, original narrow 1:3 aspect ratio, full head-to-both-shoes crop and margins. Keep the shirt completely white and untucked over the trousers; no navy on shirt, skin or backdrop. No new objects, no text, no collage, no added borders or padding. Output only the first image edited with navy trousers, maintaining its original narrow full-length framing.

### Side

Use case: precise-object-edit. Edit ONLY the FIRST input image, the three-quarter SIDE portrait of a man in a white untucked shirt. The SECOND input is a shirt-hem close-up; use it only to match the colour of the dark navy trousers below the white shirt. Recolour ONLY the visible white trouser fabric at the bottom of the first image to the same plain very dark navy blue as the trousers in the second image, approximate midtone #202637, with natural fold shading. Keep the shirt completely white. Preserve the first image's exact face, hairstyle, skin, hand and finger positions, watch, side-facing body pose, long sleeves, buttoned cuffs, shirt pocket/buttons/untucked curved hem, grey studio background, lighting, original 2:3 aspect ratio and head-to-upper-thigh framing. Do not turn the person toward the camera, change the pose, extend the frame or add legs/shoes. No changes outside the existing trouser area. No fabric print on the trousers, no new belt, no text, no collage, no border or padding. Output ONE edited side-view photograph with only the trousers recoloured.

### Back

Use case: precise-object-edit. Edit ONLY the FIRST image, the rear-view shirt catalog reference. The SECOND image is a shirt-hem close-up; use only the very dark navy trouser fabric below its white hem as a COLOUR reference. Change ONLY the small visible area of white trousers below the man's untucked shirt in the FIRST image to the same plain very dark navy blue as those trousers in the SECOND image, approximate diffuse midtone #202637, with soft realistic fold shading. Preserve all original image geometry, the rear-facing head and hair, neck, back, white shirt and rear yoke, full long sleeves, cuffs, hands and fingers, watch, grey studio background, neutral lighting, original portrait aspect ratio and head-to-upper-thigh crop. The entire shirt stays completely white. Do not add front buttons or pockets on the back, do not reveal the face, do not add a belt, extend the crop or introduce pattern on the trousers. No navy colour on shirt, hands or background. No new objects, no text, no collage, no border or padding. Return ONE rear-view photograph with only the trousers recoloured.

## Runtime prompt rule

The editorial portrait prompt ends with this constraint, after fabric colour
conditioning and the reference-framing instructions:

> Keep image 0’s plain dark navy blue trousers (midtone #202637) separate from the shirt. Their colour and unpatterned surface stay unchanged, regardless of the shirt swatch’s colour or print. Apply image 1 only to shirt cloth.

Portrait diagnostics use `shirt-editorial-swatch-v6-*`. The three detail
references retain their existing prompts and assets. This change introduces
no additional generation calls or post-processing stages.
