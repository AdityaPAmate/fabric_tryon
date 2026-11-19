# Shirt catalog completion record — 19 November 2026

The requested Shirt catalog update is implemented, pushed and live-verified.
This replaces the earlier paused-work handoff in this file.

## Code and deployment

- Branch: `perf/catalog-speed-optimization`
- Live-verified code commit: `21068f0078b5bf013addc68d50a4909fcd434298`
- Render service: `srv-db337krbc2fs73cfdt1g`
- Workspace: `tea-d0oqv0uuk2gs738vsulg` (My Workspace)
- Verified deployment: `dep-dbvch5jl550s739cu3o0`, status `live`
- Application: https://fabric-tryon.onrender.com

## Implemented behavior

Shirt defaults to `editorial-v1`, with an image-only 1800x2400 (3:4) collage,
no outer padding, no header/footer and no swatch inset. Internal separators
are 12px. Front occupies the left column, side/rear the middle column, and
collar/cuff/hem the final column. The public side-view key remains `close_up`
for client compatibility. Explicit `classic-v1` callers retain their old edition.

The downloaded `1_shirt_front.png`, `2_shirt_side.png`, `3_shirt_back.png`
were copied exactly to `fabricapp/ai/references/assets/catalog/shirt/` as
`01_front.png`, `02_side.png`, `03_back.png`. The existing collar, sleeve and
hem reference photographs remain the detail templates.
In the subsequent navy-trouser update, those three portrait files were edited
and replaced so their trousers match `hem.png`. Their runtime prompts now
preserve plain navy trousers independently of the shirt fabric. The original
white-trouser files remain in Git history; edit provenance and prompts are in
`SHIRT_NAVY_REFERENCE_EDITS.md`. The live timing below predates this asset update.

Shirt-owned prompts describe only the visible region of each close-up.
Folded-sleeve and tucked-hem selections replace the default treatment rather
than adding conflicting instructions. Default portraits retain full wrist
cuffs and an untucked hem. The final hem instruction applies the source cloth
from the photograph's top edge through the entire visible shirt to its hem.

All six shots use template edits. The rear shot now depends on the completed
front: image 0 retains the rear pose, image 1 is the original swatch, and image 2
is the generated front cropped to retain the head and finished shirt. This
replaces the face-only rear appearance reference after two brown-fabric reports
retained a white rear shirt. The final rear prompt explicitly replaces all
visible rear cloth. Other five shot prompts stay identical to those reports.
The existing sequential runner still makes six calls, with no extra reposing
stage. If the front fails, the rear is explicitly skipped instead of generating
an unconditioned result. Front output uses a 1536px longest side;
other outputs use 1024px, or 768px in draft mode. Portrait subject references
opt into 768px so cuffs and the hem remain readable; other callers keep the
provider's 511px default. Swatch and identity input limits are unchanged.
There is no added colour post-processing, mask compositing or dependent reposing.

Measured cropped source pixels anchor the palette. Pale monochrome dyed cloth
gets a tint-preservation instruction; neutral white/grey and multicolour prints
do not get a global tint. Actual swatch pixels retain the pattern information.

## Verification

- Full suite: 170 tests passed in `tmp/shirt_final_full_tests.log`.
- Final hem-only prompt correction: all 7 Shirt editorial tests passed in
  `tmp/shirt_hem_scope_tests.log`.
- Green front, collar and cuff were generated, uploaded and visually reviewed.
  Their final prompts were checked against the saved successful live configs.
- Final pale-lilac catalog ran through the public deployed endpoint:
  **72.858 seconds**, six images, no failed views, no collage error, 3:4 output.
- Every final shot's diagnostics confirms code revision `21068f0` and one
  provider attempt. Portraits have three input images; details have two and
  receive no identity image.
- All six final panels and the raw hem were visually reviewed. The earlier
  retained-white hem region was absent, full sleeves and the untucked hem
  were preserved, and the cuff remained an isolated wrist-level close-up.

Local final evidence (ignored by Git):
`outputs/shirt_live_21068f0_20261119/lilac/`
contains `source.jpg`, the six photos, `catalog.png`, `events.json`, `summary.json`.
Focused green evidence is in `outputs/shirt_focused_v4/`; the focused corrected
lilac hem is in `outputs/shirt_focused_v5/`.

The prior `2189e0e` run finished in 69.153s but failed visual review because
its hem retained white cloth. It is historical evidence, not the final result.
The final newly approved eight-generation allowance used seven generations:
one successful focused hem check and one six-image deployed catalog. One was
unused. No further paid run is needed for this implementation.

These checks cover the recorded fabrics and requests, not a guarantee that
all future generative outputs will be identical. Other garment implementations
were unchanged; the provider subject-size option preserves its old default.
