# Stage 4: measured fabric colour reference — 2026-10-31

Implemented for blazer swatch requests. Original image RGB pixels (after any
selected crop) provide a small palette. Nearest-neighbour sampling avoids
averaging fine print colours during palette extraction. Values and descriptive
colour families are placed early in both primary and fallback prompts.
Caller stream positions are restored, and the request context is not mutated.
The uploaded image bytes, resize/JPEG processing, lighting, scale, material,
seed and guidance are unchanged.

## Rollout

Single-family palettes get automatic conditioning (`blazer-colour-v5`). This
is a conservative palette gate, not proof a fabric is physically plain.
Multi-colour palettes retain the previous prompts by default; the internal
`_colour_reference_experiment` context allows further offline/live tests.
There is no new frontend parameter. Garment-image requests use their existing
route. Other garment builders are not changed by this blazer rollout.

## Live evidence

Baseline: `debug/generation_baseline_20261031`.
First candidate: `debug/colour_evaluation_20261031` (9/10 outputs).
Pattern candidate: `debug/colour_evaluation_v2_20261031` (9/10 outputs; floral
outdoor rejected twice with provider code 3030). Purple outdoor and checks
outdoor each succeeded after a same-seed/prompt retry. Failed attempts are
retained, not replaced or counted as successful outputs.

Each pair preserves the successful baseline request's exact provider input
hashes, seed, guidance, resolution and primary/compact variant. Assertions
verify that removing the colour reference produces the original prompt byte
for byte. Alternate-seed fallback is disabled for these comparisons. This is
a comparison against baseline lighting, not against stage 3's experiment.

The initial late palette improved purple in studio but not outdoors. The early
palette still produced grey in one purple studio sample. Consolidating tonal
variants into one measured single-family reference gave lavender-purple in both
studio/outdoor samples in the final four-case check at
`debug/colour_evaluation_v3_20261031`; green retained its teal family. The red
reference is identical to its successful v2 requests and retains a deep red
family. These are visual observations, not measured Delta E claims
or a guarantee of repeatability. Patterned results remain mixed: floral
outdoor rejection and checks detail/placement issues prevent their automatic
rollout. Velvet surface fidelity remains a separate material problem.

## Verification and limitations

Prompt/colour tests cover source-position restoration (including errors),
crop selection, palette retention of distinct colours, automatic single-family
conditioning, default isolation of multicolour experiments, both retry variants
and all existing blazer prompt contracts. Successful live output/input hashes,
dimensions, paired settings and final default prompt equivalence are checked
separately in `rollout_verification.json` in the final experiment directory.

The benchmark uses one face reference and generated body, five fabrics, two
scenes and business style. Other blazer styles/routes have unit coverage but
not equivalent live-image coverage. It does not validate pure-white swatches,
physical colour calibration, embedded ICC conversion, exact pattern fidelity,
face identity or all fabrics. No complete garment mask or quantitative garment
colour-error metric is claimed. Build-time tests do not establish visual quality.

The selected default is implemented in this local branch; no deployment was
performed. Archived experiments include source snapshots and exact actual
requests so their results remain attributable after the default was enabled.
