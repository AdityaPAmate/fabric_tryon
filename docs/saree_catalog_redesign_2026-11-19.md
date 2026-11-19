# Saree catalog redesign — 19 November 2026

Current contract: six independent template edits, 1800 × 2400 (3:4), edge-to-edge
panels without header/footer or external padding. Front configuration is identical
to the preceding commit. Historical 9:16 and shared diagonal-back descriptions in
older architecture notes do not describe this revision.

## Shot responsibilities

- Side: head-to-upper-thigh crop; long pallu continues below frame, terminal artwork excluded.
- Back: catalog-only straight hanging pallu, level lower end, lower skirt/hem visible.
  No identity inputs; normal single-image diagonal-back pose is unchanged.
- `fabric_texture`: compatibility key now means full overhead saree flat-lay,
  showing body, both long-side borders and complete pallu together. Always uses
  the full uploaded source, even when a body crop is supplied.
- Border: real long-side edge, not broad pallu end artwork.
- Pleats: waist-to-hem textile crop, no upper torso, wearer head or architectural scene.

`regions.py` owns Saree source selection. Explicit body/border boxes win. Otherwise
the existing numerical body selector can propose a body inset and an adjacent
long-side band. These are heuristics, not guaranteed semantic segmentation.
`full_source_unresolved` explicitly marks absence of a reliable selection. Optional
crop fields in both catalog UI and Desktop tester allow correction. A body-only
source cannot establish unseen decorative borders/pallu; prompts require plain
finished edges rather than invented ornament.

The provider accepts opt-in `fabric_reference_crops` from the same original fabric
upload. Side uses the additional real border in slot 3 when identity occupies slot
2; pleats uses slot 2. Back has only template and product images. No extra AI calls
are added. Invalid crop bounds and unavailable slots fail before requesting AI.
Other garments do not opt into this mechanism.

## Reference asset provenance

Edited with the built-in image generation tool; native generated PNGs copied into
`fabricapp/ai/references/assets/catalog/saree/`. Manifest records hashes and sizes.
All other reference assets remain unchanged.

- `03_back_view.png`: generated file `exec-be44373b-b7d0-43fc-89e0-fecb840989e0.png`.
- `04_fabric_texture.png`: generated file `exec-2320bd73-4dcd-4200-8aaa-19223286961c.png`.

### Back reference prompt

Use case: precise-object-edit. Edit this rear-view saree catalog pose reference.
Keep this same adult woman, rear-facing torso, bun hairstyle, head gently turned
right, white opaque modest blouse, white saree with simple thin black double-line
borders, neutral grey-beige studio background and full head-to-floor portrait crop.
Change the PALLU ARRANGEMENT: remove the broad diagonally spread triangular sheet.
The pallu now falls naturally STRAIGHT DOWN along the LEFT half of her back as a
long nearly vertical rectangle from the left shoulder, with its side edges hanging
downward and its lower end edge approximately HORIZONTAL at lower-calf height.
Let her left hand lightly hold its outer edge away from her left hip, without
stretching the cloth diagonally. Her right arm rests naturally beside her right
hip. The wrapped lower saree and its pleats remain clearly visible below and to
the right of the hanging pallu, including the complete bottom hem near the feet.
The pallu does not cover the whole lower skirt or run diagonally across both legs.
Preserve real continuous fabric, natural gravity, soft folds and three-dimensional
drape, not a rigid pasted rectangle. Keep generous enough portrait framing that
the entire lower hem and pallu end are inside the image. No new identity reference,
no added person, no props, no text, no collage, no added frame. Narrow portrait
approximately 327:739 aspect ratio, matching the original.

### Full flat-lay reference prompt

Use case: product-mockup. Create ONE photorealistic overhead flat-lay saree fabric
catalog reference, vertical portrait 2:3, NOT a person wearing a saree and NOT a
close-up. Show one COMPLETE continuous white cotton saree fabric panel spread
flat on a smooth light-grey studio surface. Its entire rectangular outline is
inside the photograph, with a slim natural background margin around ALL four
edges. The long body occupies the upper three quarters; narrow plain pale-grey
woven side borders run down both long sides; the full pallu end occupies the lower
quarter, gently distinguished by two very fine pale-grey woven horizontal lines
near its outer end. Show the whole body, BOTH complete side borders and the
COMPLETE pallu end together. Fabric has fine realistic cotton weave and only very
shallow natural settling folds, lying nearly flat with all corners visible, no
overlapping folds hiding any design area. Uniform soft neutral white studio light.
This is a geometry-only reference for later fabric replacement: keep the white
fabric simple and plain, no embroidery, decorative motifs, flowers, birds,
colourful designs or black bold stripes. Frame the fabric large while retaining
its complete outline within approximately 4 percent margins. No people,
mannequins, faces, hands, blouse, clothing on a body, props, text, labels, collage,
inset, graphic borders or watermark. The photograph must clearly read as a full
product flat-lay, not a macro textile detail.

## Verification

Full offline suite: 172 tests, one capitalization-only assertion failed after the
new back prompt. Corrected the assertion to compare case-insensitively; subsequent
35 catalog/region/reference tests passed. Front old/new config equality checked.
Tests exercise actual multipart crop pixels, face/border slot separation,
back identity exclusion, invalid crops, full-source flat-lay and layout coverage.
Offline tests establish request routing, not generated visual fidelity.

`scripts/verify_saree_catalog.py` performs one authorized deployed six-shot replay
and saves evidence under ignored `outputs/`. No automatic reruns. The selected
saved source is the cream/purple saree report `2026-11-19_110114_001`, not the red
bird-design screenshot. Live visual findings must be reported separately.

Desktop tester optional fields installed with `scripts/update_tester_saree_regions.py`;
original files backed up under ignored `tmp/tester_saree_region_backup/`. Refresh
the tester page to load them. Those external files are not part of this Git repo.
