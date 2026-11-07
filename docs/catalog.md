# Catalog API: current six-panel saree edition

The saree catalog now matches the supplied **white_saree_catalog_final_corrected_3x4.png** arrangement: one full-height photograph at left, two middle photographs,
and three right-hand details. Output is exactly **1800 x 2400 (3:4)**, with 12px
white gutters and no header, footer, text, product labels or separate swatch inset.
The layout ID is `saree-six-panel-3x4-v4`; the existing `editorial-v1` edition ID
is retained so callers do not need to change their request.

## Request and response

`POST /api/generate-catalog/` accepts multipart fabric/person/model/material fields
from `/api/replace-fabric/`. Supply `fabric_image` and `garment_type`; garment-image
mode is unsupported. Omit `pose` and `camera_view`: the catalog owns its shots.
Existing style, material, model and garment-detail validation still applies.
`options.draft_mode=false` is the default. Explicit draft reduces ordinary shot
provider dimensions, while the final export canvas remains 1800 x 2400.

`catalog_edition` is optional. `catalog_product` is still accepted for older clients
with the same allowed fields, but **all metadata is ignored by this image-only
layout**. Changing product text cannot add any visible text. Product/header inputs
have been removed from both browser forms. Other garment layouts are unchanged.

The NDJSON protocol is unchanged: started, generating, heartbeat, image_ready,
image_failed, composing, collage_ready, complete. Read `started.total` and its views
rather than assuming seven images. The saree total is now **6**.

Ready images contain view, URL, size, seed, provider diagnostics, framing and
reference metadata. The collage includes `width=1800`, `height=2400`,
`aspect_ratio="3:4"`, `layout="saree-six-panel-3x4-v4"` and
`includes_original_swatch=false`. Individual image dimensions differ by panel.

## Six shots and the replacement references

1. `front`: `01_front_pallu.png`; full-height left column.
2. `side_portrait`: `02_three_quarter.png`; upper middle.
3. `back_pallu`: `03_back_view.png`; lower middle.
4. `fabric_texture`: `04_fabric_texture.png`; upper right.
5. `border`: `05_border_closeup.png`; middle right.
6. `pleats`: `06_pleats_hem.png`; lower right.

The old seven catalog reference images were removed from
`ai/references/assets/catalog/saree/`. Only these six numbered images and their
SHA-256 manifest remain. The six panels are now cropped from the supplied final 3:4 collage; the manifest records source hash and crop coordinates. Downloads originals and normal single-image pose assets
are preserved.

The former neckline and separate pallu-detail shots are no longer generated.
All six panels fill their declared rectangles proportionally, with small crops
matching the supplied cropped references. No photo is stretched, and there is no
letterboxing or unused heading/footer space. Provider sizes preserve panel aspect
and stay within the engine's 256..1920 bounds; the very tall front column therefore
uses a smaller generated photograph scaled proportionally into the export.

## Reference and identity roles

The front edits its numbered template, using an optional requested identity when
provided. The side edits its numbered template directly to retain the reference angle;
when a caller explicitly supplies a face/person identity it is used only as an
identity reference. No generated front image or blank-canvas reposing is used.

**Back-pallu sends only the new pose reference and fabric.** It never receives a
face upload, face choice, person photo or generated front identity. The shared
normal saree builder still supplies back-pallu pose/hand/fold rules, but the catalog
uses `03_back_view.png`, not the old normal pose photograph. The normal API,
coordinator and provider retain the no-identity restriction for this pose.
All six shots can run independently, including when front generation fails.

Texture, border and pleats are independent template edits using original fabric
pixels. Texture is a fabric-surface close-up, not a neckline or border image.
The side-border shot distinguishes the long finished edge from body print and the
pallu end. A body-only swatch does not establish a decorative product border;
particular zari/embroidery needs a source photograph that actually shows it.
Reference white cloth and black stripes are not automatically product facts.

Inputs use PNG fabric transport. Classified provider failures, strict requested
output-dimension checks and input hashes are retained. Corrupt/incorrectly sized
images are rejected before upload. These checks establish transport integrity,
not visual accuracy of fabric, pose or border design.

## Operation and evidence

Definitions/assets are validated before streaming. Invalid requests return 400,
configuration failures 503, and a busy process 429. One catalog slot per web
process, sequential generation, ten-second heartbeats and cancellation after an
in-flight provider call are retained. There is no durable queue or resume API.
Successful shots remain available if another shot fails; all six are required
for the final collage. Quota/auth failures stop additional provider calls.

Historical checks before the 3:4 revision: 109 Django tests, 4 stream tests and 5 report tests. They include
actual local HTTP multipart/storage stand-ins, six-shot totals, reference hashes,
independent failure behavior, identical swatch input hashes, no identity input for
back-pallu, exact panel placement and text-free rendering. Those paid outputs used the previous 9:16 layout, not this 3:4 revision.

A reference-only layout proof is saved separately from any generated-fabric result:

```powershell
venv\Scripts\python.exe tools/preview_catalog.py --references --output output/saree_six_panel_reference_layout.png
```

A real six-image fabric-transfer test is recorded under
`debug/saree_six_panel_live_20261107/`. Live results and any focused corrections are
documented separately; a reference-only collage is never fabric-transfer evidence.
Historical live evidence for previous layouts remains in the earlier JSON reports.

See [catalog_architecture.md](catalog_architecture.md) for shared execution and
extension points. Pushing source does not itself verify a hosting deployment.

## Main body and side-border source regions (3:4 revision)

The upper-right body texture and middle-right border use separate prompt builders.
`options.fabric_body_crop_box` and `options.fabric_border_crop_box` accept optional
`[left, upper, right, lower]` integer coordinates in the ORIGINAL uploaded fabric
image. These are catalog-only saree options. Invalid or out-of-bounds regions return
400 before generation. Both browser forms expose these optional region inputs.

Body uses its explicit crop, otherwise `fabric_crop_box`, otherwise full source.
Border uses its explicit crop, otherwise the full original source, even when the
global crop excludes the edge. Each selected region is physically cropped BEFORE
resizing/PNG encoding for input_image_1, and colour conditioning uses the same
region. Config records `fabric_region`, `fabric_region_selection`, and the crop.
These values describe input selection, not verified visual extraction success.

For accurate decorative border reproduction, upload a photograph showing the real
long edge alongside body cloth and select it. A body-only swatch cannot reveal an
unseen decorative border. In that case the prompt requests a plain finished edge
and forbids inheriting template black stripes or inventing zari/embroidery.
AI can still deviate; live visual validation of this revision is pending.
The lower-right reference now shows waist-to-hem pleats with the hanging pallu.
Back-pallu remains pose + fabric only, without identity inputs.
