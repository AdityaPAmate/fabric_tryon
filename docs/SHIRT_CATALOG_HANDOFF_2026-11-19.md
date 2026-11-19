# Shirt catalog completion record — 19 November 2026

## Current code and deployment

- Branch: `perf/catalog-speed-optimization`
- Live-verified code commit: `2f586bcba423df6f26d6a8e479111f59da1ed4e3`
- Render service: `srv-db337krbc2fs73cfdt1g`
- Workspace: `tea-d0oqv0uuk2gs738vsulg` (My Workspace)
- Verified deployment: `dep-dbvd6o3l550s739ei3n0`, status `live`
- Application: https://fabric-tryon.onrender.com

## Implemented behavior

Shirt defaults to `editorial-v1`, an image-only 1800x2400 (3:4) collage, with
front at left, side/rear in the middle and collar/cuff/hem in the final column.
There is no outer padding, header/footer or swatch inset. Internal separators
are 12px. Explicit `classic-v1` callers retain the previous edition.

The three numbered portrait reference files now have plain navy trousers,
matching `hem.png`. The portrait prompt preserves those trousers independently
of the shirt fabric. Image-edit provenance is in `SHIRT_NAVY_REFERENCE_EDITS.md`.

The rear keeps its own pose template and original swatch, but takes identity
and finished-shirt appearance from a crop of the generated front. The crop is
(.06, .01, .94, .70) of the full front photograph. The final rear instruction
replaces every visible shirt area, including the yoke, collar, sleeves and cuffs.
If front generation fails, the dependent rear is skipped explicitly. The
sequential runner still makes six planned image generations, with no added
colour post-processing, mask composite, reposing call or automatic colour retry.

Front output has a 1536px longest-side limit; the other views use 1024px, or
768px in draft mode. Portrait subject references opt into 768px; other provider
callers retain their existing 511px default. Swatch and identity limits are
unchanged. Shirt prompts own the measured palette and material wording.

## Latest report investigation and live verification

Investigated reports:
`shirt/2026-11-19_160101_001` and `shirt/2026-11-19_160325_001` in the local tester.
Both selected the rear view. Both used the same brown `pant_fabric2.jpg`,
Vihaan identity, seed 42, guidance 7 and white-marble-terrace background.
Both produced a white rear shirt while other views carried the brown cloth.
Their rear prompt/request hashes and all input hashes matched one another.
The failed production prompt was reconstructed locally with its exact SHA-256.
The old rear had only a face identity reference, not the generated front outfit.

The fix changes only the rear conditioning and its dependency. The other five
prompts remained byte-identical to the failed reports. This identifies the
failed request/conditioning path; it does not claim to reveal an undocumented
internal decision or a single causal token inside the generative model.

Verification used exactly the user-approved six paid generations: one full
public deployed-endpoint replay with the saved report's original source and
parameters. Result: **78.832 seconds**, six images, no failed views, 3:4 collage.
Every shot confirmed revision `2f586bc` and one provider attempt.

Actual response diagnostics confirmed:

- Every shot's pose-reference and fabric-input hashes matched the failed report.
- The five unchanged views also retained their prompt and identity-input hashes.
- Only the rear changed its prompt and image 2, now the generated-front crop.
- The raw rear and complete collage were visually reviewed: rear cloth was
  brown across the back, yoke, collar, both sleeves and cuffs; navy trousers
  and the rear pose remained present.

A fixed central-back inspection region (x .30-.70, y .35-.65) changed from
median RGB [213,212,214] to [66,54,40]. Its bright-neutral pixel fraction fell
from 61.93% to 0.04%. This is evidence for the reported dark-brown case, not a
runtime colour validator or a rule for rejecting legitimately white cloth.

Evidence, ignored by Git:
`outputs/shirt_report_back_2f586bc/` contains the source, request, six photos,
collage, events and `summary.json` with the per-view hash comparisons.
Only this reported fabric was live-tested under the six-generation cap.

Tests: all 171 passed in `tmp/shirt_report_back_full_tests.log`, including
provider-input routing and the failed-front/dependent-rear error case.

Earlier successful pale-lilac rollout: `21068f0`, 72.858 seconds, evidence in
`outputs/shirt_live_21068f0_20261119/lilac/`. That earlier result predates the
navy-trouser asset update and is not the current report replay.
