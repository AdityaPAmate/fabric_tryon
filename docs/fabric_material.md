# Fabric material and colour selection

`POST /api/replace-fabric/` accepts an optional multipart form field
`fabric_type`: `unspecified` (default), `cotton`, `silk`, or `velvet`.

Example form fields alongside the existing uploaded images:

```text
fabric_image=<uploaded swatch>
person_image=<uploaded person>
garment_type=blazer
garment_style=business
fabric_type=velvet
```

Use the existing person-source rules: with a person image, do not send gender,
body type or face selection. When generating a person, gender remains required.

- `unspecified` adds no material instructions and does not guess the material.
- `cotton` describes a fine woven, predominantly matte cotton surface.
- `silk` describes a fine smooth surface with restrained lustrous sheen.
- `velvet` describes short plush pile, directional nap and velvety highlights.

Explicit material selection applies to **fabric_image** requests for all six
garment types: `blazer`, `shirt`, `kurta`, `kurti_pant`, `pant` and `saree`.
Garment-image requests accept omitted/`unspecified` but return HTTP 400 for
cotton/silk/velvet. Unknown values, empty strings and null are also invalid.
There is no new nested `options` key.

Success responses echo `fabric_type`. Provider trace `prompt_version` identifies
an explicit material, e.g. `blazer-material-v1-velvet`. The coordinator routes
the selection into both primary and fallback prompts. The material controls
the selected garment's surface only; existing colour conditioning, crop, pattern scale,
pose, outfit construction, seed, guidance, lighting and upload flow are retained.
No database migration or client change is needed for old requests.

Material affects model instructions rather than physical cloth simulation.
Real cotton/silk vary by weave and finish, and exact drape or surface fidelity
is not guaranteed. Validation tests establish API/plumbing/prompt behaviour;
saved live comparisons provide separate qualitative evidence.

Targets follow the garment: shirt; kurta/sherwani/pathani/jodhpuri; kurti;
trousers; saree body/pallu; blazer jacket. Matching dupattas are included only
when explicitly selected, excluding the separately specified white head drape.
White kurti pants, plain kurta pajama rules, blouses and other separate garments
retain their original outfit instructions. Borders, pose and coverage are not
rewritten by the shared conditioning layer.

Measured single-colour-family references now apply to all six garment types.
Multicolour palettes remain experimental, matching the original blazer rollout.
The shirt's legacy palette is replaced only when the new single-family colour
reference is present, so two competing palettes are not sent. Source stream
positions and selected crop coordinates are preserved. Blazer prompt strings
and material defaults retain their previous behaviour.

Development branch: `codex/all-garment-fabric-conditioning`. No deployment is implied.

## Validation evidence

The full local `fabricapp` suite passes 53 tests. This includes actual multipart
validation through the view and real prompt builder with the provider engine
and Cloudinary uploader stubbed, plus routing, retries and colour regressions.
It establishes the local contract; it is not a live HTTP deployment test.

During the original blazer implementation, six live Cloudflare outputs were captured: cotton/silk/velvet in studio and
outdoor, using the same red velvet swatch and face reference. Existing stage-4
unspecified outputs were reused after checking exact prompt equivalence to the
current unspecified builder. Each pair preserves input hashes, successful
baseline seed, guidance, resolution, primary/compact variant and colour
conditioning. Only the material instruction is added. Test-only alternate-seed
fallback is disabled; ordinary API retries are unchanged.

These are controlled surface-choice experiments on one swatch, not evidence
that real cotton and silk swatch photographs match their physical material.
Velvet visibly shows more plush/directional surface response; cotton looks
predominantly woven/matte, and silk has smoother highlights. Exact colour,
identity, framing and folds can still vary with the generative provider.

Local artifacts (gitignored):

- `debug/material_reference_20261031`: reused unspecified references.
- `debug/material_cotton_20261031`, `debug/material_silk_20261031`,
  `debug/material_velvet_20261031`: actual prompts, requests, attempts and outputs.
- `debug/material_verification_20261031.json`: integrity and pairing checks.
- `debug/material_velvet_20261031/comparison_velvet.jpg`: visual comparison.

## Other-garment live checks

`tools/test_all_garment_fabric.py` exercises the public generation coordinator
for five additional garment types, each with an unspecified/explicit-material
pair. Shirt/pants use the red swatch with velvet; kurta uses purple with cotton;
kurti-pant and saree use purple with silk. These are surface-control examples,
not claims about the real fibre content of the input photographs.

Generated adult models are used, with no person/face-photo upload. Per-pair
seed 42, guidance 7, studio background and final output size are fixed. The
actual submitted input hashes must match; only the material instruction may
differ between pair prompts. Colour references are present in both. Alternate
seed fallback is disabled in this test, with real API retries unchanged.

Artifacts are saved under `debug/all_garments_live_20261031`, including original
swatches, prompt configs, actual requests/attempts, outputs, source snapshots
and `overview.jpg`. The unit matrix covers all supported styles, four ordinary
scenarios and all material choices; saree pose-reference has a dedicated check.
Live examples do not exhaust all poses/styles/backgrounds or prove exact colour,
identity, framing or material fidelity.

All 10 initial requests produced valid images. Visual review found the velvet
pant sample changed into a dress, so it is **not** counted as a successful
garment result. The pant material prompt now explicitly preserves the waistband,
crotch, two trouser legs, separate top, subject gender and framing. The full 53
local tests pass with this correction. Its live recheck at
`debug/all_garments_pant_fix_20261031` was blocked by Cloudflare HTTP 429 / code
4006 (`allocation_exhausted`); no corrected pant output was produced. The live
runner now stops immediately on this quota classification. Resume the pant-only
check after provider allocation becomes available; do not infer visual success
from unit tests or image transport integrity.
