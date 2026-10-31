# Stage 3: blazer lighting evaluation — 2026-10-31

Outcome: lighting-only prompt changes did not establish consistent fabric
colour preservation. The candidate remains an internal experiment; ordinary
API requests retain the original v4 prompts byte-for-byte. No rollout to other
garments, colour correction, scale or material changes was made.

## Evidence

- Baseline: `debug/generation_baseline_20261031` (5 fabrics, 2 scenes).
- First candidate: `debug/lighting_evaluation_20261031` (10/10 outputs).
- Shorter candidate: `debug/lighting_evaluation_v2_20261031` (3/4 selected
  outdoor outputs; floral rejected with provider code 3030, no alternate seed).
- Each comparison preserves the successful baseline attempt's seed, compact
  versus primary variant, guidance, resolution and exact provider input hashes.
  Assertions verify that the only prompt edit is the scene/lighting block.
- Controlled evaluations disable alternate-prompt/seed retries. Baseline
  fallback cases use their successful seed 43 and compact variant directly.
- Saved JSON includes exact actual requests, statuses, diagnostics, output
  hashes and source snapshots. Original baseline artifacts are preserved.

## Qualitative review

The first candidate's studio floral print appears more distinct, but outdoor
lighting remains warm and some midtones shift. The second candidate does not
consistently resolve this. Purple still appears grey and velvet still differs
from its swatch. Pattern detail and face/body framing also vary. These are
visual observations, not measured colour-error reductions. Single samples
cannot establish causality or account for provider nondeterminism.

## Code and checks

`fabricapp/ai/blazer/lighting.py` holds the candidate. Builders select it only
with internal context `_lighting_experiment=True`, which is not exposed by the
API serializer. `tools/evaluate_blazer_lighting.py` sets that context, reuses
baseline input files and saves before/after galleries. Completed artifacts are
immutable; changed source requires a new output directory.

Seven blazer prompt tests pass, including all routes/styles/backgrounds and
fallback variants, and isolation of the experimental lighting from normal
requests. Separate replay checks compare default prompt bytes to the saved
pre-change module. No HTTP integration or visual-quality claim is made by
these unit tests.

Stage 3 experimentation is complete; the desired colour improvement is not
established. The next colour-preservation stage should address explicit fabric
colour conditioning and garment-region evaluation rather than treating this
lighting experiment as a proven fix. A pure-white swatch and person-photo edit
route are outside the captured benchmark.
