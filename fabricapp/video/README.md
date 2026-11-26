# Video architecture

This module is the only owner of animation behavior. Image generation and
catalog generation retain their existing code, routes and contracts.

## Request flow

1. `GET /api/video-options/?garment_type=shirt` returns public, non-secret UI
   metadata. It does not call any provider or require a generation API key.
2. Either existing POST entry point validates explicit `garment_type` and an
   optional `video_motion`. Missing motion selects that garment's default;
   unknown or cross-garment styles fail instead of silently falling back.
3. `registry.select_profile()` resolves a garment definition once at job creation.
   The JSON profile and version are saved on the existing `VideoJob` record.
4. The existing serial worker uses that saved profile, including on retries.
   `/generate-tryon-video/` calls the existing image adapter; `/animate-image/`
   uses saved uploaded bytes and skips image generation.
5. Gimmeclip receives the full source image and the saved prompt. The provider
   job reference and completed clip URL remain checkpoints, preventing a
   render/storage retry from generating another paid clip.
6. `rendering.py` dispatches passthrough or the existing source-collar composition;
   `storage.py` owns download, decode checks and final Cloudinary delivery.

For a ready-made `garment_image`, `garment_type` is video context only. The video
serializer removes it while validating the original ready-image request, then
restores it for animation selection. The video worker removes that context from
the image adapter's inputs. The image API itself is unchanged.

## Where to change a garment

Edit `garments/<garment>.py` for prompt, version, help text and source framing.
The unchanged shirt prompt text is in the data-only `garments/shirt_prompts.py`.
No garment names should be added as conditionals to the worker, provider or UI.
The explicit registry is the allowlist; user input never becomes an import path.
Garments load lazily. A broken garment configuration returns a video-only 503
for that garment; it does not prevent the image/catalog URLs or other garments
from loading. The old health motion list is compatibility metadata, not the UI's
source of garment capabilities.

Definitions/styles are frozen dataclasses, not a workflow framework. New
definitions have one default and at most two published styles. At the user's
explicit request, the existing third shirt commercial option is retained in a
small compatibility tuple until they choose which shirt styles to keep. Its
prompt, version, duration and source-collar composition are unchanged. All three
remain visible. This exception cannot be used for another garment or a new style.

Each of saree, kurta, kurti+pant, pant and blazer has its own front-presentation
and walking definition. These are new video prompts requiring visual evaluation,
not a claim that all garment outputs have been visually certified. The source
hints are input requirements for the user; they are not automatic segmentation.
Pants do not require a face or the shirt collar detector.

## Saved jobs and rendering

Do not resolve the latest definition from a running job. Changing a definition
affects new jobs only. Old profiles without a `renderer` key still use their saved
`source_collar_opening` flag; an older commercial without that flag remains a
passthrough clip. No retroactive opening is added.

The shirt renderer remains in `collar.py` to preserve the established crop and
FFmpeg behavior. Shared orchestration calls only the rendering dispatcher. The
current provider animation route supports 4/6/8 seconds, prompts of 3–300
characters; definitions validate those limits before any generation.

## Timings and quality

Existing response timing fields remain. New fields distinguish initial queue
wait, creation-to-ready total, post-provider elapsed time, image upload, photo
upload, download, decode/continuity checks, local render and final video upload.
Download includes the HTTP request and streamed body. Storage-stage timings
describe the successful final delivery attempt; wall-clock totals also include
poll intervals, retries and pauses. New source bytes have SHA-256/dimensions
recorded in private job payload metadata; the source is not transformed.

`quality_status=not_verified` is distinct from pipeline `status=completed`.
`needs_review` reflects an advisory outer-frame drift flag. Neither MP4 decoding
nor that heuristic verifies exact fabric identity; multi-shot commercial checks
are not a fabric-certification mechanism.

## Reliability boundaries

The existing ambiguous-submit guard and atomic retry compare-and-set are retained.
Preparing jobs interrupted for more than one hour are explicitly failed rather
than left invisible to the worker or submitted with uncertain inputs. No files
are deleted by that recovery step.

This change adds no queue service, schema migration, infrastructure or paid plan.
Free Render's local SQLite/source media remain ephemeral. Restart-proof storage,
customer ownership/auth, API-level request idempotency, provider URL expiry
tracking and multi-worker claims remain separate future work; these are not
provided by the registry. Direct provider delivery is not substituted for the
existing composed final URL.

## Verification

`fabricapp.test_video_registry` covers bounded styles, garment isolation, public
options, missing context, legacy plan reuse, stale input recovery and timings.
Existing video/provider/renderer tests exercise saved work and real local HTTP /
FFmpeg without paid generations. Existing image/catalog tests are regression
checks, not edited to accommodate video behavior. UI tests verify dynamic styles
and saved-image garment context.
