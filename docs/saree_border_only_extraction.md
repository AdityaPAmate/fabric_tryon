# Fifth panel: only the extracted side border

Reviewed `2026-11-20_124032_001` (issue: `border did not come`, c4d7e43).
Its border trace explicitly says `body_only_no_confirmed_border`, with crop
`[0,0,736,490]`. The old implementation then rotated the full source photograph,
so body and broad terminal artwork could enter even if a border crop existed.
The user's red-peacock screenshot exhibits that failure clearly.

## Implementation

Only the fifth panel opts into `border_extraction.py`. Existing front, side,
rear, full-product photo, front-derived pleats and shared provider requests do
not change. In particular, the side-view border-context selector remains intact.

1. An explicit `fabric_border_crop_box` wins and is checked against source bounds.
2. Otherwise, analyse a bounded thumbnail for persistent long side edges over
   the upper/middle source region. Search line position and slope, then select
   an outer/inner edge pair, favouring a visible full band over narrow piping.
   Right side and narrower pairs are considered if the left band is unsuitable.
   This is numerical geometry, not a semantic textile segmentation guarantee.
3. Four source corners delimit the selected trapezoid. Rectify ONLY that band
   with Pillow's quadrilateral mapping. Store its original-image coordinates
   and numerical edge scores in the returned trace.
4. Render a central segment of the extracted band diagonally from top-left to
   bottom-right on neutral grey. The renderer only receives the extracted strip,
   so the unselected body/pallu cannot leak into the fifth photo. Do not repeat
   or generate new motifs. Source resolution limits the sharpness of a close-up;
   enlargement is bounded when choosing a segment.
5. Remove the whole-fabric fallback. Ambiguous patterned inputs produce
   `border_selection_required` and an actionable diagnostic asking for the
   existing crop field, instead of labelling a full product photo as a border.
   Uniform swatches get an honestly labelled `plain_source_edge`, with no invented
   ornamental border. A failed required border prevents publishing a misleading
   complete collage, while the other successfully generated images remain.

This approach keeps border content source-faithful and adds no paid generation.
It is best for photographed, approximately straight long-side borders. For a
folded, occluded or ambiguous border, select a clear short section explicitly.

## Research

- [OpenCV geometric transformations](https://docs.opencv.org/4.x/da/d6e/tutorial_py_geometric_transformations.html):
  four-point mappings rectify photographed regions; full projective transforms
  are an alternative. This implementation uses Pillow QUAD, not OpenCV's API.
- [Pillow QuadTransform](https://pillow.readthedocs.io/en/stable/reference/ImageTransform.html#PIL.ImageTransform.QuadTransform):
  maps the upper-left, lower-left, lower-right and upper-right source corners
  into a rectangle. No OpenCV package or model dependency was added.
- [scikit-image line-transform examples](https://scikit-image.org/docs/stable/auto_examples/edges/plot_line_hough_transform.html):
  line detection is useful for long boundaries. The implementation performs a
  small direct line-parameter search using existing NumPy/SciPy dependencies.

## Verification and limits

188 offline tests passed. New tests cover explicit-band pixel isolation from red
body/lime pallu, slanted-edge rectification, ambiguous-pattern rejection, manual
bounds, landscape crops and the public catalog stream's selection-required error.

Visually reviewed four local examples: the actual new white report source, an
earlier floral source, and red/blue delivered full-product photos from the tester.
The latter two are already resized product views, not claimed to be original
upload bytes. All produced separate border-only previews. Local render times
were approximately 0.10–0.17 seconds; these are not deployed catalog timings.
No paid Cloudflare generation or Cloudinary upload was performed.

Evidence is under ignored `outputs/saree_border_only_20261120/`: each preview and
trace, plus a catalog preview replacing ONLY the fifth image in the saved report.
The five other saved images are reused; this is not a newly generated live catalog.
