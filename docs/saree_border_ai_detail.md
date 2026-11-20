# Saree fifth panel: AI border detail

The editorial-v1 fifth panel now calls the configured image-edit provider once,
instead of delivering the enlarged source crop as the final panel. Other panels
are unchanged: three wearer edits, original full product photograph, and a crop
of the generated front for the pleats. A complete catalog therefore normally
uses four AI generations instead of three.

`border_ai.py` owns the prompt and input preparation. The shared executor only
exposes an optional input-preparation callback; other definitions have no callback
and keep their existing inputs. The back-view identity prohibition is unchanged.

The placement guide is built from the actual extracted source border, never the
old white/black-stripe template. A second input supplies a short native border
segment, retaining useful width through the provider's input limit. Both inputs
honour explicit border selection and orientation. Ambiguous patterned inputs
still request a border selection rather than silently using the whole saree.
No separate identity or scene reference enters the border edit.

Border instructions are independent of the body colour profile: preserve the
border's own colours, stripe count, motif sequence and orientation; neutral white
light; diagonal top-left to bottom-right placement; no broad pallu artwork.
Normal output is 800x1056, downsampled into the unchanged 532x704 panel.

## Verification

One live request used the pink/gold source from report
`2026-11-20_131129_001` on 2026-11-20, with network attempts capped at one and
no safety retry. Cloudflare returned 800x1056 with two product-only inputs.
Local evidence: `outputs/saree_border_ai_20261120/border.png` and `trace.json`.
Visual review shows clearer motif edges and woven texture than the prior enlarged
crop. AI reconstructs detail; exact recovery of unseen or blurred source motifs
is not guaranteed. This single sample does not establish quality for all fabrics.
No additional live generations or uploads were performed.
