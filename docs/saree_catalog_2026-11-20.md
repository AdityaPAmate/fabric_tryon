# Saree report corrections — 20 November 2026

Reviewed reports `2026-11-20_102408_001` and `2026-11-20_102418_001` in the separate
Desktop tester. Both describe the same generated catalog at revision fe43910.
Back shows two overlapping wearers; border shows a real-looking curved detail
but is reconstructed by AI. Fourth panel now shows a full flat saree, but still
reconstructs its artwork. Pleats changes the reference folds.

## Evidence and changes

- The prepared current back asset hash matches the report input exactly. Its
  silhouette is diagonal, while the previous prompt demanded a straight pallu.
  Removed that conflict and retained the user-selected template geometry, with
  exactly one existing wearer. No claim that this alone proves duplication fixed.
- Back report has only template and fabric inputs; no identity was transmitted.
  Added immutable shot policy `allows_identity_reference=False`, validated before
  execution and before provider calls. Runner forces the existing provider guard
  even if a builder omits it. Attempts to add request/front identity are errors.
- Corrected stale manifest hash/dimensions after the user's fe43910 asset change.
- Fourth panel now uses the complete actual source photograph. Every edge stays
  visible, no AI reinterprets body/border/pallu designs. To satisfy the fixed panel
  and no padding/cropping, source aspect adapts to the panel; this can change
  apparent proportions. It cannot reveal cloth absent from the uploaded photo.
- Fifth panel uses an actual source border crop. Explicit selection wins.
  Conservative sustained-colour evidence can narrow the previous overly broad
  body-adjacent band; the report source narrows from [0,0,312,465] to [50,0,151,465].
  This is not universal semantic detection. Neutral/ambiguous borders require
  explicit selection; fallback is honestly marked `body_only_no_confirmed_border`.
  Existing product pixels are resized, not sharpened or invented. Low-resolution
  input limits close-up sharpness. Border longitudinal extent may be cropped.
- Sixth panel continues to edit the original pleats template with body and actual
  border references. Removed the instruction to extend the pallu outside the frame,
  which contradicted its visible template edge. Reinforced unchanged fold count,
  overlap, contour and crop. A deterministic texture-projection experiment showed
  stretching and insufficient realism during visual review and was discarded.
  No unverified synthetic projection is enabled in production.

## Isolation and verification

Generic engine addition is a callback operation, with no Saree name or prompt in
the runner. Only Saree opts in. Front/side configurations and other garment
definitions are unchanged. Source crop coordinates remain original upload pixels.
Two source-photo shots do not consume provider generations; normal catalog now
has four AI edits and six delivered images plus collage. No paid calls were made.

176 offline tests passed before final panel sizing/verification-helper cleanup;
affected tests rerun afterwards. Tests cover actual multipart input slots, actual
source pixels, full-source crop precedence, independent product shots after
provider failures, declaration-level identity rejection and direct provider guard.
Offline tests do not prove generated back/pleats visual fidelity. Those two AI
outputs need subsequent user-generated results or authorized live verification.

Local product previews and test logs are saved under ignored `tmp/`. The earlier
experimental pleats previews are rejected evidence, not production outputs.
