# Saree fifth panel: hand detail derived from front

The user supplied the hand screenshot as framing guidance, not a separate AI
pose template. The fifth panel now uses the same crop operation as the sixth
pleats panel. Both depend on the generated front and preserve its exact pixels,
fabric, wearer, hand anatomy and seed. No independent hand generation is made.
The screenshot asset remains in the manifest as historical framing guidance;
it is not sent to the provider. The public shot key remains `border` for clients.

The fifth ROI follows the front waist/hand framing, centred at 48% of source width,
covering 39%-61% of source height for the normal front aspect. Width is derived
from the 532x704 panel aspect and bounded to 96% of the source. The sixth ROI is
unchanged. Coordinates are independent of fabric colour and print. A changed
front pose can move hands outside this framing; crop is not a hand detector.

Normal catalogs use three AI edits (front, side, back), original full product
photography, and two front-derived crops. If the front fails, both derived panels
fail as dependencies instead of generating unrelated fallback photographs.
Back-view face/person prohibition and other garment pipelines remain unchanged.

## White lower-skirt defect

The supplied screenshot shows a large white lower-left pleat area while the
pallu has been replaced. The white front pose template contains cloth in that
same location. The previous front prompt had a general all-cloth replacement
instruction but no explicit lower skirt/recessed-pleat region assignment. It also
allowed an options-level fabric crop to replace the full product input.

The front now keeps complete product evidence in image 1 and explicitly assigns
the wrapped lower skirt, inner tucks and recessed pleats to the actual saree body.
A separately available body ROI is sent as image 2 (no identity) or image 3
(identity present), with minimum size/aspect checks. White source motifs remain
allowed; no global white-pixel recolouring is performed. The screenshot alone
cannot prove which inference decision left that region unchanged. The correction
has local routing tests and the single-sample live verification described below.

## Verification

Six saved front outputs (3309, 3302, 3295, 3288, 3281, 3274) were used for local
crop previews. Evidence is under `outputs/saree_hand_crop_20261120/`. Tests compare
complete hand-panel pixels against the expected crop for several fabric colours,
verify no provider call, source hash/seed, dependency failure and bounded aspect.
The 62 focused tests passed. After explicit user approval, exactly one Cloudflare
front generation used the original pink/gold saree source from report
`2026-11-20_131129_001`, seed 42, face choice poonam and white_marble_terrace.
Automatic network and safety retries were disabled. The provider accepted the
full source plus a separate body ROI [199,0,551,420] in image 3. Visual review of
the returned front shows pink lower pleats instead of the supplied screenshot's
large white lower-skirt section. Both hand and pleats panels were derived from
that actual returned front with no further AI calls.

Evidence: `outputs/saree_front_body_verified_20261120/front.png`, `hand.png`,
`pleats.png`, provider trace and two crop source-hash traces. This is a local run
through the production runner/provider code, not a whole deployed-catalog test.
No uploads were performed. One successful sample does not establish a zero
failure rate for all fabrics or prove a single model-internal cause.
