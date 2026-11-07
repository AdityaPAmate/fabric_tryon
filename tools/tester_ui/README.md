# Fabric Try-On Tester UI

Updated copy of the user's existing tester, preserving its styling, timer,
single-image workflow, local outputs and testing reports. Run `python server.py`
from this folder (or the installed Desktop copy) and visit `http://localhost:5500`.
Use one tester server at a time. Python's standard library is sufficient.

Material options apply to all six fabric-based garment types. Ready garment
mode omits material and crop. Single/Catalog mode uses the configured API host
and derives `/api/replace-fabric/` or `/api/generate-catalog/` accordingly.
The catalog endpoint must be deployed on that host or run locally; the default
Render URL does not imply that this feature branch has been deployed.

Catalog mode ignores pose/camera and renders the edition’s declared images (seven for saree, six for shirt), with
individual Open/Save and Inspect/Report controls. Stop generation cancels the
connection; the backend's active provider request may still finish. No collage
or scale controls are added. Source crop is optional and uses original pixels.
The rear image is now a garment close-up, and the angle view requests a
front-dominant three-quarter pose. Shirt collar and cuff views use the packaged
reference templates. Reports preserve each image's `framing` and
`reference_template` metadata when the current backend supplies it.

Pose and detail choices in `js/api_options.js` reflect the current backend.
Colour conditioning remains automatic; no colour-correction sliders are added.
The report's generated-person fields reflect only what was actually submitted,
so person-photo requests do not report disabled gender or stale face settings.

## Reports

Reports retain the existing paths: `reports/<garment>/<timestamp>/report.json`,
`reports/<garment>/all_reports.json`, and `reports/index.jsonl`.

Version 2 adds material, generation mode, crop/options, selected catalog view,
catalog ID, full set status, ready images, failed-view errors, provider codes,
per-image generation seed/diagnostics (when supplied by the API), and duration.
`catalog_images/` contains independent copies of all successful images in the
set. The selected image remains in the existing `files.generated_output` field.
Inspect/Report selects an individual ready or failed view; the saved report
also includes the complete catalog context. Missing local/remote copies record
`copy_error` and retain their delivery URLs. Old reports remain untouched.

Request elapsed time excludes local saves. Images save sequentially through
the existing `/save-output` helper to avoid assigning duplicate local filenames
within a catalog. After stopping or a broken stream, already-ready images
remain available, and reports record cancelled/interrupted status.

Tests: `node --test test_catalog_client.cjs` and `python test_reports.py`.
The report tests POST to the real local HTTP handler with temporary directories;
the stream tests exercise fragmented protocol data. Neither requires paid AI
requests. `python ../install_tester_ui.py` installs reviewed files into the
original Desktop tester directory and backs up existing files under project
`debug/`; outputs and reports are preserved.

## Saree editorial edition

Saree catalog requests now default to `editorial-v1`: seven reference-driven views
and a 1800 × 3200 (9:16) PNG with backend-rendered header/footer. Optional product fields
appear in catalog mode for saree. Empty facts are omitted; no material composition
or product length is inferred. Reports retain the product fields, edition and layout.
The normal single-image flow is unchanged. Existing deployed servers must be updated
before using the new catalog fields. The UI source is in this repository; an independently
installed Desktop tester must be updated separately using the existing installer.

The seven-panel saree edition now uses six AI photographs and one derived fabric
edge crop. `image.generation.kind=derived_crop` records its source image and bounds;
reports retain this metadata. This avoids regenerating the supplied white woven
border design as a product detail. Side identity/pose references are separated;
neckline has a dedicated close crop. A real blue-floral catalog was live-tested;
see `docs/saree_catalog_live_evidence.json` for the scope and remaining limitations.

Current revision: seven independent saree images, including a real side-border
shot instead of a derived body crop. Back pallu shares the normal saree
pose-reference builder. All default catalog exports are 9:16; saree is 1800×3200,
shirt is 1296×2304. The viewer displays the server's ratio metadata and preserves
natural image dimensions. Older live-test notes above describe earlier revisions.

Back-pallu (`back_showing_pallu`) accepts no face or person identity references.
The normal-pose dropdown disables it while those inputs are selected. Catalog
requests may still use a face for other shots; the back-pallu operation omits it
and is independent of the generated front image.
