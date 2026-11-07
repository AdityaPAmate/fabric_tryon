# Fabric Try-On Tester UI

Run `python server.py` from this folder and open `http://localhost:5500`.
Use one tester server at a time. Python's standard library is sufficient.
Set the API URL to the backend you want to test; the UI derives either
`/api/replace-fabric/` or `/api/generate-catalog/` from the selected mode.

Single-image controls and output/report saving are preserved. Material applies
to all six fabric-based garment types; ready-garment mode omits material/crop.
Catalog mode omits pose/camera and displays shots incrementally, then selects the
final collage. Actual totals, layout and aspect ratio come from stream events.

## Current saree catalog

Six photographs in the supplied three-column arrangement, 1800 x 2400 (3:4):
front at left; side and back in the middle; texture, border and pleats at right.
There is no header, footer, product text or swatch inset, and the unused product
text inputs have been removed. The old seven-image catalog references are replaced
by `01_front_pallu.png` through `06_pleats_hem.png`.

Back-pallu always uses only pose reference + fabric, never a face/person/front
identity input. A global catalog identity can still be used for front/side shots.
In normal single-image mode this pose is disabled while face/person inputs are
selected, and the backend rejects such combinations.

Image/report metadata retains seed, provider trace, framing, reference and collage
information. Local output saves are sequential. Report JSON retains full catalog
context; failures preserve URLs and record missing-copy errors. Old reports are
not rewritten. After cancellation or a broken stream, already-ready images remain
available; the backend cannot resume a job after refresh or process restart.

## Verification and installation

- `node test_catalog_client.cjs` checks stream fragmentation and six-shot metadata.
- `python test_reports.py` exercises the real local HTTP report handler using
  temporary directories. Neither command needs paid AI calls.
- `python ../install_tester_ui.py` updates an independently installed Desktop tester,
  backing up its files under project `debug/` and preserving outputs/reports.
  Repository edits alone do not update an independently installed copy.

Backend contract and live evidence: `docs/catalog.md`. Reference-only previews
prove layout only; paid live tests separately check actual fabric transfer.

Saree now exports 3:4 (1800 x 2400). Advanced options provide separate optional main-body and long-side-border crops in original fabric pixels. Border defaults to the complete original photo; a body-only swatch cannot establish a decorative border.
