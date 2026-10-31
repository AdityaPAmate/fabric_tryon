# Blazer material selection

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

Explicit material selection applies only to **blazer + fabric_image** requests.
Other garment types and garment-image requests accept omitted/`unspecified`
but return HTTP 400 for cotton/silk/velvet. Unknown values, empty strings and
null are also invalid. There is no new nested `options` key.

Success responses echo `fabric_type`. Provider trace `prompt_version` identifies
an explicit material, e.g. `blazer-material-v1-velvet`. The coordinator routes
the selection into both primary and fallback prompts. The material controls
the jacket surface only; existing colour conditioning, crop, pattern scale,
pose, outfit construction, seed, guidance, lighting and upload flow are retained.
No database migration or client change is needed for old requests.

Material affects model instructions rather than physical cloth simulation.
Real cotton/silk vary by weave and finish, and exact drape or surface fidelity
is not guaranteed. Validation tests establish API/plumbing/prompt behaviour;
saved live comparisons provide separate qualitative evidence.

Development branch: `codex/blazer-fabric-material`. No deployment is implied.

## Validation evidence

The full local `fabricapp` suite passes 45 tests. This includes actual multipart
validation through the view and real prompt builder with the provider engine
and Cloudinary uploader stubbed, plus routing, retries and colour regressions.
It establishes the local contract; it is not a live HTTP deployment test.

Six live Cloudflare outputs were captured: cotton/silk/velvet in studio and
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
