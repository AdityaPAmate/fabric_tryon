# Catalog API — current behavior (2026-11-07)

`POST /api/generate-catalog/` remains one multipart POST with an NDJSON stream.
The event names and success/failure semantics are retained. **Saree now defaults
to seven-panel `editorial-v1`; shirt retains six-panel `classic-v1`.** Other garments
retain six-panel classic editions. Counts and views must be read from `started`.

## New optional multipart fields

- `catalog_edition`: an allowlisted edition ID. Omit for the garment default.
  Saree supports `editorial-v1` and the six-panel compatibility `classic-v1`.
- `catalog_product`: a JSON object encoded as a multipart text field. The saree
  editorial edition accepts `title`, `collection`, `subtitle`, `badge`,
  `product_name`, `product_code`, `fabric_description`, `saree_length`,
  `blouse_length`. Values are single-line strings, at most 100 characters.
  Unknown fields are rejected; other editions currently accept no product fields.
  Empty product facts are omitted. Product composition/length is never inferred.

Example product field (all values are illustrative, not defaults):

```json
{"product_name":"Classic Saree","product_code":"S-1001","fabric_description":"Cotton Blend","saree_length":"5.5 m","blouse_length":"0.8 m"}
```

The original fabric/person/material/detail validations apply. Catalog requests
must omit `pose` and `camera_view` and cannot use `garment_image`. The saree
editorial generated model supports women/girls; an uploaded person supplies its
own identity. Final quality is the API default; explicit draft reduces new saree
provider sizes to a maximum side of 512 (with provider-aligned dimensions).
The exported collage remains 2200 × 2900, so draft photographs look softer.

## Saree editorial shots and references

1. `front`: `saree_royal_front_stand.png`; request person/face reference when supplied.
2. `side_portrait`: generated front supplies identity; the side reference is a fourth, below-face composition guide.
3. `back_pallu`: separate catalog copy of `back_showing_pallu.jpg`; front identity anchor.
4. `neckline`: `saree_neckline.png`; front identity/outfit anchor.
5. `pallu`: `saree_pallu.png`; independent fabric-only template edit.
6. `border`: deterministic close crop of generated `pallu`, rather than a new AI edit of the woven-border template. The original border reference remains a layout guide.
7. `pleats`: `saree_pleats.png`; independent fabric-only template edit.

Templates control pose/drape/crop, while the request swatch controls saree fabric.
The side shot uses a blank image 0, original swatch image 1, cropped front identity
image 2, and a below-face pose guide image 3. This avoids the template model's face
competing with the requested identity. Neckline uses a cropped front identity and
an explicit lip-to-bust frame. The border panel is a declared local `crop` operation
with `generation.kind=derived_crop`, `source_view=pallu`, source hash and crop bounds.
It does not create another AI image or fabricate a macro weave. Seven panels require
six AI generations in the final implementation. PNG transport preserves the swatch
without JPEG colour subsampling. Classified provider errors, input hashes and strict
image-dimension validation are enabled for this edition; legacy single-image saree
behavior remains unchanged.

The front image is retained before uploading, so its upload failure does not lose
its identity anchor. Front generation failure skips its three dependent shots;
pallu and pleats can still run, and border requires a successful pallu. Quota/auth
failures stop remaining work. Exact physical colour, pattern scale and edge design
remain generative limitations; the visual evidence below is from one actual input.

The backend composes all seven successful shots into `saree-editorial-v1`, draws
header/footer text, and uploads the PNG. This edition has no separate swatch inset;
`collage.includes_original_swatch` is false. Shirt retains its original swatch inset
and `portrait-catalog-v4` layout. `started` includes `catalog_edition` and `layout`;
`complete` includes `catalog_edition`. Existing event fields remain available.

## Operation and validation

Definitions/assets/fonts are validated before opening a stream. Invalid request
fields return 400; unavailable catalog configuration returns 503; busy process
returns 429. Shot failures after streaming begins remain NDJSON events.
One catalog slot per process, sequential generation, 10-second heartbeats and
cancellation behavior are retained. There is no durable job queue or resume API.

See [catalog_architecture.md](catalog_architecture.md) for extension points.
`/api/catalog/` and the repository tester include optional saree product fields.
An independent installed tester needs updating separately. Backend push is not
proof of deployment; verify the deployed version before using new request fields.

Local reference-only layout proof, without AI calls or uploads:

```powershell
venv\Scripts\python.exe tools/preview_catalog.py --references --output output/saree_catalog_reference_preview.png
```

Use `--shots-dir PATH` instead of `--references` to recompose generated files named
`front.png`, `side_portrait.png`, etc.; `--product-json PATH` changes product text
without generating photographs again.

Validation: 98 Django tests, 4 tester stream tests and 5 local report tests.
The suite covers identical prepared swatch bytes across every provider request,
four-slot reference separation, incorrect output rejection, quota handling and
border crop provenance with no provider call. Real local HTTP stand-ins separately
exercise multipart requests and storage behavior.

After explicit approval, 14 real Cloudflare generations and their Cloudinary
uploads completed on 2026-11-07: a full seven-generation baseline plus seven focused
rechecks. Every request used the same original blue floral swatch; all prepared
`input_image_1` hashes match. The final collage uses six selected real photographs
and a local crop of the generated pallu. It was composed and uploaded without new
AI calls. See [saree_catalog_live_evidence.json](saree_catalog_live_evidence.json).

Local final output: `output/saree_fabric_catalog.png`; original input:
`output/saree_fabric_swatch.png`. Full prompts/traces and run results are in
`debug/saree_fabric_*_20261107/` (gitignored). The first reference-only preview is
layout evidence only and must not be presented as proof of fabric transfer.

Visual review: all seven final panels show the supplied blue floral print;
neckline crop and side identity improved. Side rotation remains weaker than the
supplied guide, and thin edge trim/colour/pattern scale are not physically exact.
This is not an exhaustive quality guarantee for arbitrary fabrics or faces.

Cloudflare documents four input slots and the input-size limit used here:
[Workers AI FLUX.2 klein reference](https://developers.cloudflare.com/changelog/post/2026-01-15-flux-2-klein-4b-workers-ai/).
Postman CLI remained unavailable due to its machine-managed manifest; the evidence
above comes from Django tests, local HTTP stand-ins and the actual provider runs.

---

The notes below are historical; the current contract above takes precedence.

## Dark brown colour refinement (2026-11-04)

The reported shirt catalog 2026-11-04_120928_001 used the same swatch bytes
for all six requests. Recomposition matched the saved collage exactly: the colour
variation originated during generation, not composition.

Single-family dark orange-brown RGB profiles now use the label dark chocolate
brown and explicit original-swatch colour priority. This narrowly gated prompt
reduces orange grading and dark-fabric brightening. White, blue and multicolour
prompts retain their prior behavior. Diagnostics append brown-v2 when active.

Live validation: three targeted shots, then a complete six-shot catalog with the
reported swatch and Raghav face (test runner uses trim body), then a final hem
region-lock check. Cuff and collar improved visually; front/back still differ in
lightness from the swatch. This is a measured improvement, not exact colour fidelity.
No blanket pixel recolouring is applied to skin, scenery or patterned fabrics.

## Hem and framing update (2026-11-04)

Shirt hem now uses the supplied packaged hem.png, like collar and cuff.
Template prompts cover all shirt regions, keep trousers/skin/buttons separate,
and forbid invented limbs in the hem reference. Three-quarter is now a close-up
from head through garment hem, with no lower legs or shoes.
The portrait-catalog-v2 sleeve/cuff panel contains the complete image with white
side padding where needed, rather than cropping away cuff and wrist edges.
Live checked fabric tests verified sleeve replacement and close-up angle. A second
hem-only test corrected invented limbs and preserved the supplied hem geometry.
70 tests passed; the final prompt was rechecked with 16 catalog tests.
Other panel positions are unchanged. Tests cover all three templates, partial
failure independence, and preservation of sleeve image edges.

## Fixed portrait catalog (2026-11-04)

Final output: one 1800 x 3200 PNG, composed locally without another AI call.
Fixed placement: front left; three-quarter and rear close-up top right; three detail
views below; original uploaded swatch across the bottom. Other garments retain
their existing three detail views in the same slots. No layout or image selection.
Images are resized proportionally with centered crops to fill fixed panels.
Off-center subjects may need better source framing; images are never stretched.

The stream retains image_ready diagnostics and adds composing and collage_ready.
The complete event includes collage and collage_error. Missing views or failed
composition/upload produce partial/failed status and no final collage.
The tester selects the final collage as output, saves it locally, and archives
catalog.collage in reports alongside source images. Hem uses existing generation
until a separate hem reference is supplied.

Validation: 69 Django tests, 5 report HTTP tests, 3 stream tests; previously generated
live images composed locally and visually checked. No fresh Cloudflare generation
was used for this deterministic composition change. Deployment remains separate.

# Generate Catalog

Branch: `codex/catalog-image-set`. No deployment is implied.

Open `/api/catalog/` for the included browser form. Select a swatch, garment,
optional person photo and material, then click **Generate Catalog** once.
It renders separate images with individual Open / Save links. No collage is
created. This repository is a backend; the page is an additional usable entry
point and the same API can be connected to an existing separate frontend.

## API contract

`POST /api/generate-catalog/` accepts multipart fields from
`/api/replace-fabric/`, with these differences:

- `fabric_image` and `garment_type` are required; garment-image mode is unsupported.
- Do not send `camera_view` or `pose`; the catalog chooses its own shots.
- Existing garment-style/person-source/material/detail validation still applies.
- Default quality is final (`options.draft_mode=false`); explicit draft is supported.

One POST keeps a streaming response open (`application/x-ndjson`). Each line is
an independent JSON object. Read it incrementally using `fetch` and
`response.body.getReader()`, not `response.json()`.

Example events:

```json
{"event":"started","total":6,"views":["front","three_quarter","back","collar","cuff","hem"]}
{"event":"generating","view":"front","index":1,"total":6}
{"event":"heartbeat"}
{"event":"image_ready","image":{"view":"front","url":"https://..."},"completed":1,"total":6}
{"event":"image_failed","view":"cuff","error":"image_generation_or_upload_failed"}
{"event":"complete","status":"partial","images":[],"failed_views":["cuff"],"total":6}
```

The final `images` array contains every successfully uploaded image (the example
above abbreviates it). Status is `completed`, `partial`, or `failed`.
Validation errors are HTTP 400 before streaming; a busy process returns HTTP 429.
Once HTTP 200 begins, shot errors are stream events, not HTTP status changes.
A fatal stream error emits `event=error`; a dropped connection may have no final event.
`started` and `complete` include a `catalog_id`. Ready images include
`generation_seed` and provider `generation` diagnostics when available; failed
events include provider code/diagnostics when available. The existing Desktop
tester integration and its version-2 reports are maintained in `tools/tester_ui`.

All garments get a front view, a front-dominant three-quarter view and a rear close-up (not a full-body rear view). Detail views vary:

- Shirt: collar, cuff, hem.
- Blazer: lapel, cuff, hem.
- Kurta: neckline, sleeve end, hem.
- Kurti-pant: kurti neckline, sleeve end, hem.
- Trousers: waistband, pocket, ankle hem.
- Saree: pallu, border, pleats.

## Generation and operation

The existing public coordinator generates the front image, retaining current
colour/material rules. Most subsequent shots edit that same front reference,
alongside the original fabric swatch, with a dedicated view/detail prompt. This
reduces identity and outfit drift but does not guarantee exact consistency.
Shirt collar/cuff shots edit the packaged user-provided templates; their original skin, geometry and background are retained while fabric is replaced. Other close-ups use the front reference. Close-ups are separate model generations, not crops or a collage. The original
swatch is not regenerated. A nonexistent collar/cuff must not be invented.

Every successful image is uploaded independently using the existing Cloudinary
service. It remains available if a later image fails. Front-generation failure
skips dependent shots, while independent shirt templates can still run; front-upload failure can still use its in-memory reference.
Provider quota/auth errors stop further generation calls. Other failures allow
remaining shots to continue. This version does not support retrying one shot.

This is a streaming version, with no database queue, extra worker service or new
dependencies. Keep the page open: closing it cancels remaining shots after the
active provider call finishes. Server restart interrupts work. It cannot resume
after refresh. Save successful image links before leaving. The stream sends a
heartbeat every 10 seconds and disables reverse-proxy buffering where supported.
Verify streaming on the deployed host: the local test does not prove the host's
maximum response duration or buffering behavior. Do not put this route behind a
proxy that buffers all content or imposes a short hard request deadline.

One catalog is allowed per web process; ordinary generation endpoints retain
their behavior. With the current two-process Gunicorn setup, up to two catalogs
can run at once. Each catalog sends requests sequentially, limiting provider load.
The existing deployment requires no migrations or Docker command change.

## Verification

`python manage.py test fabricapp` passes 67 tests, including the thirteen catalog
tests. These verify multipart validation, sequential stream events, reference
reuse, all garment plans, per-shot failures, quota stopping, cancellation and
capacity control with provider/upload stubs; they do not prove visual quality.

`tools/test_catalog_live.py` exercises one real multipart catalog request and
Cloudflare/Cloudinary calls, saving separate images and event records locally.
Use the project virtualenv and pass `--fabric PATH --output debug/NEW_DIRECTORY`.
The default live example is a generated adult male wearing a shirt, with no
personal photo upload. Outputs and event records are ignored by Git.

Live check on 2026-11-01: the single multipart request completed all six
Cloudflare generations and six actual Cloudinary uploads at 1152 x 1536.
Artifacts: `debug/catalog_live_20261101`. Visual review found a valid rear
view and sleeve/hem details, but the first collar view was too wide.
Dedicated shirt close-up instructions were tightened; four focused real
generation/upload rechecks are in `debug/catalog_detail_recheck_20261101`.
The collar, cuff and hem are now close details in that sample. The angle shot
still leans toward a side profile rather than exactly 45 degrees; a rear/side
outfit can also acquire small differences in seams, accessories and pattern.
These samples establish a functioning image-set flow, not exact garment or
colour reproduction. Other garments have local plan/contract coverage, not
exhaustive live catalog validation. Deployment proxy streaming remains unverified.

Current organization, reference behavior and the completed 2026-11-02 quota-recovery live checks are recorded in `docs/ai_layout.md`. Historical visual evidence above describes previous prompt versions.
