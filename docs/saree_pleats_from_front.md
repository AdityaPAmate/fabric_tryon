# Saree detail panel derived from its generated front

User requested the lower-front region shown in their screenshot instead of
another AI interpretation of the folds. Reviewed report
`2026-11-20_121648_001` (issue: `border on plates`, revision 2fc7f85).

The public `pleats` key now declares a `crop` operation depending on `front`.
It uses the original generated front bytes held by the runner, not the collage,
not the old sixth reference, and not the uploaded swatch. No AI request, palette
conditioning, border-reference input or independent pleats seed is used.
The derived image inherits the front's seed; its trace records source view,
original source-image SHA256, resolved normalized crop, output dimensions and
`no_new_ai_generation=True`.

The Saree-owned resolver uses the established full-length front framing: roughly
the lower 50–94% vertically, centred around the lower saree/pallu. It calculates
width from the 532:852 panel aspect to retain the lower hem without another
cover crop or padding. Bounds scale with resolution, never with fabric colour,
pattern or material. This is a declared framing crop, not semantic body detection;
if a future front pose changes substantially, update the resolver alongside it.
It cannot manufacture extra pleats absent from the original front.

The old independent AI pleats builder is removed and explicitly rejects direct
pleats calls. The old numbered sixth asset remains archived in the reference
folder/manifest but is no longer declared as a production shot reference. Its
filename is not reported as the reference for the derived image.

If front generation fails, pleats reports `front_reference_failed`; it does not
silently generate another outfit. If only front upload fails, the generated
front bytes still exist and the crop can be produced. Catalog delivery remains
six images plus a 3:4 collage, now with three AI edits instead of four.
Front, side, back, full-product and diagonal-border generation are unchanged.
Back identity prohibition remains enforced.

## Verification

- 182 offline tests passed, including actual multipart routing (three provider
  calls), local HTTP/storage stand-ins, dependency failure behavior, complete
  crop pixel equality, source hash/seed provenance, and multiple source colours
  and resolutions. No paid Cloudflare calls or uploads were made.
- Applied the production crop to the saved report's actual front; visually
  inspected `outputs/saree_front_detail_20261120/pleats.png` and assembled a preview
  using the report's other five images. These are local evidence files, not a
  newly generated live catalog. The front's fabric, folds, pallu and lighting
  appear in the detail without another generative interpretation.

No new reference edit or additional front pleats were necessary; changing the
working front reference would change the already accepted first image.
