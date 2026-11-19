# Shirt catalog handoff — 19 November 2026

> Resume note: the user subsequently asked to complete the remaining work.
> The snapshot below records the initial `5d8b1ca` deployment, not final quality.
> Follow-up changes use `shirt-editorial-swatch-v4-*`: region-specific detail
> edits, a measured palette without colour-name overrides, non-conflicting
> sleeve/hem options and 768px portrait subject references. Other provider
> callers keep the existing 511px subject-input default. A v2 cuff edit followed
> the reference, but v2 front cuffs were rolled; a v3 pale-fabric front invented
> a waistband over the shirt. Simplified reference-preservation instructions
> and the portrait input-size opt-in followed. The v4 green front, collar and
> cuff were visually inspected and uploaded: the front kept full wrist cuffs
> and the untucked hem; the close-ups kept their reference regions. All 169
> tests passed (`tmp/shirt_v4_full_tests.log`). The user approved a NEW maximum
> ten-generation allowance; four focused generations were used, leaving six
> reserved for one deployed pale-fabric catalog. Its actual timing, revision,
> events and images are saved under `outputs/shirt_live_<revision>_20261119/`.
> Never treat the older 69.376s run as a test of the v4 implementation.

## User's requested work

Update the Shirt catalog to 3:4. Import downloaded `1_shirt_front.png`,
`2_shirt_side.png`, `3_shirt_back.png` as the first three references. Keep the
existing collar, sleeve/cuff and hem references in the final column. Keep
generation time low. User has now asked to stop at the current stage and hand
remaining work to another model because usage is nearly exhausted.

## Completed code and deployment

- Checkout: `C:/Users/ADMIN/Desktop/fabric_tryon`
- Branch: `perf/catalog-speed-optimization`
- Pushed commit: `5d8b1cae8ec02b10784ab0dd8ad961808203b2a1`
- Commit title: `Add reference-based 3:4 Shirt catalog with smaller detail generations`
- Git working tree was clean at handoff, before this uncommitted handoff note.
- Render service: `srv-db337krbc2fs73cfdt1g`, workspace `tea-d0oqv0uuk2gs738vsulg`
- Render deployment: `dep-dbvbvd3l550s739bdr4g`, confirmed `live`.
- URL: https://fabric-tryon.onrender.com
- The six live response diagnostics all confirm the commit above.

New Shirt-owned implementation:
`fabricapp/ai/garments/shirt/catalog/editorial.py`.
Registry defaults Shirt to `editorial-v1`; explicit `classic-v1` retains the
previous 9:16 behavior. No other garment implementation was changed.

Layout is image-only 1800x2400: full front on left, side/back stacked in the
middle, collar/cuff/hem stacked on the right. No outer padding or header/footer;
12px internal separators. `close_up` remains the public key for the side view
for client compatibility. All six are independent template edits. Front uses
a 1536px longest side, other shots 1024px, draft 768px. No finish hook or local
pixel recoloring was added.

Copied reference assets (hash-verified identical to Downloads originals):
`fabricapp/ai/references/assets/catalog/shirt/01_front.png`, `02_side.png`,
`03_back.png`. Existing details remain `shirt_collar.png`, `sleeve.png`, `hem.png`.

## Verification already performed

- Targeted catalog tests: 26 passed, including three new HTTP/provider-routing
  tests in `fabricapp/test_shirt_editorial_catalog.py`.
- Full suite: 166 ran; 165 initially passed. One existing aspect-ratio test
  still expected Shirt 9:16. Updated its expected default to 3:4, then reran
  that exact test successfully. The entire suite was not rerun after this
  expectation-only change. Log: `tmp/shirt_full_tests.log`.
- One real deployed catalog completed in **69.376 seconds**, all six shots,
  Cloudinary upload and final 3:4 collage; no failed views or collage error.
  This proves execution and measured latency for ONE fabric, not universal
  visual correctness.

Live evidence folder:
`outputs/shirt_live_5d8b1ca_20261119/green/`
Contains `source.jpg`, six individual images, `catalog.png`, `events.json`,
`summary.json`. These outputs are ignored by Git but exist locally.

## Remaining issues — do NOT claim the visual requirements are complete

The live collage was visually inspected at handoff. It exposes real failures:

1. **Cuff shot does not follow its sleeve reference.** The middle panel of the
   last column shows an upper-body short-sleeved shirt, rather than the requested
   sleeve/cuff close-up. Inspect raw `cuff.jpg` against `sleeve.png`, and the
   actual serialized prompt/input geometry in the response diagnostics.
2. Front, side and rear show rolled sleeves despite the default full-sleeve
   instruction. Check whether contradictory template/conditioning instructions
   override the desired sleeve treatment. Do not assume a cause without inspecting.
3. Green cloth tone/shading varies between panels, with visible bright bands
   on some shots. The supplied green source itself has a strong bright stripe;
   separate faithful source appearance from unwanted added lighting.
4. Detail images are generated at their reference aspect ratios then cover-
   cropped into narrow panels. Review whether this removes important collar,
   cuff or hem content. Do not introduce padding to hide the issue.
5. Inspect all six raw outputs at full resolution and compare their own
   references, not only request success or collage metadata.
6. A second patterned/lilac fabric has NOT been live-tested. Also validate
   identity, background, folded/full sleeves, tucked/untucked options after
   correcting reference adherence. Keep changes confined to Shirt.

## Continuation tools and commands

Python: `.\venv\Scripts\python.exe`

Tests:
```
.\venv\Scripts\python.exe manage.py test fabricapp.test_shirt_editorial_catalog fabricapp.test_catalog --noinput
.\venv\Scripts\python.exe manage.py test fabricapp --noinput
```

Temporary live script: `tmp/verify_deployed_shirt.py`.
It accepts `--revision <commit-prefix>` and `--case green` or `--case lilac`.
Without a case it runs BOTH full catalogs (12 paid generations): do not run
that by default. Green source is saved in the evidence folder. Lilac source:
`C:/Users/ADMIN/Desktop/fabric_tryon_tester_ui/reports/shirt/2026-11-19_101610_001/garment_source.jpg`.

Automatic approval review rejected the two-catalog/12-generation command
because available authorization was at most 8 generations. A reduced single
catalog/6-generation command was then approved and completed. Do not assume a
fresh paid-generation allowance. The user has asked to stop further work now.

After fixes: run relevant tests, commit/push to the existing branch, verify
the intended revision deploys, and visually review the real results before
claiming quality is fixed. Render autoDeploy is configured yes but did not
trigger on this push; an explicit plugin deployment of latest commit was used.
