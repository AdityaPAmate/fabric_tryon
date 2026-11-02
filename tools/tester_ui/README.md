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

Catalog mode ignores pose/camera and renders six independent images, with
individual Open/Save and Inspect/Report controls. Stop generation cancels the
connection; the backend's active provider request may still finish. No collage
or scale controls are added. Source crop is optional and uses original pixels.

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
