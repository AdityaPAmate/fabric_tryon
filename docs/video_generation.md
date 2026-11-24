# Fabric TryOn: optional image-to-video

Branch: codex/fabric-image-to-video. Base: perf/catalog-speed-optimization at 27e7314.
The original Desktop backend was clean and matched its upstream before this branch.

## Flow and preserved behavior

Single-image and catalog URLs, validation, image prompts and provider settings keep
their existing contracts. The image view and video worker share the small
`services/tryon_service.py` adapter to the existing `generate_tryon_image` engine.
Catalog generation continues to use its existing runner and streaming protocol.

Video mode accepts every valid existing single-image request: all six garments,
fabric/ready garment, generated/uploaded person, face reference, style, material,
pose, camera, background, details, crop, seed, guidance and draft settings. It first
runs that exact image pipeline, persists the image, uploads it to Gimmeclip, polls
the saved edit, and stores the MP4 in Cloudinary. Image settings affect the source
photo; Gimmeclip does not expose the image engine's seed/guidance controls.

Motion is independent: `auto`, `turn`, or `subtle`. Auto uses detail movement for
close-ups, gentle movement for custom poses/person references/side views, and a
slow side/back display for a normal front photo. Hands remain still. Each job
saves its complete 8-second motion profile so deployment changes cannot alter a
resumed request. Video quality and accurate unseen back details remain model dependent.

## API

Video endpoints require `Authorization: Bearer <VIDEO_API_TOKEN>`.
`GIMMECLIP_API_KEY` remains on the server. Without video configuration the existing
image/catalog endpoints still start and work; video endpoints return 503.

- POST `/api/generate-tryon-video/`: original image multipart fields plus optional
  `motion` (`auto` default). Returns 202 with job_id/status_url; queues only.
- POST `/api/animate-image/`: multipart `source_image` (PNG/JPEG/WebP), optional
  garment_type, camera_view, pose and motion. Reuses those photo bytes, skipping
  image generation. The UI's "Make video from this image" uploads its selected
  generated single image/catalog shot, not the collage or an arbitrary server URL.
- GET `/api/video-jobs/<uuid>/`: status, image/video, garment_type, chosen motion,
  timing, and error.retryable. Internal paths, provider URLs and keys stay private.
- POST `/api/video-jobs/<uuid>/retry/`: only failed retryable jobs; resumes the same
  image, uploaded Gimmeclip photo, accepted provider edit, or finished MP4 as available.

States: queued -> image_generating -> video_submitting -> video_generating ->
video_storing -> completed (or failed). The short preparing state only persists inputs.
Ambiguous edit submissions cannot be retried blindly. Inspect provider history if
a worker stops after submission but before saving the returned edit ID. Never
repeat a create POST automatically after an unknown response.

`timing` contains elapsed_seconds, total_seconds, image_generation_seconds and
video_generation_seconds. Values are seconds or null. Provider generation time is
submission to observed completion, including queue/poll intervals and worker
pauses; it is not GPU-only time. Existing-photo jobs have no image generation time.

The prototype has a shared operator token, not individual customer accounts.

## Tester UI

The repository copy is tools/tester_ui; the Desktop copy is fabric_tryon_tester_ui.
Choose Single image, Catalog, or Generate video. Image controls remain available.
For video, enter the backend VIDEO_API_TOKEN and choose Auto/Turn/Subtle motion.
The result area shows a live total timer and a separate live video timer, progress,
source image, MP4 player, downloads, and saved job UUID. Inspect/resume can recover
polling after refresh; retry appears only when the backend permits it.

Stop waiting cancels browser polling, not the remote generation. Resume the saved
UUID against the same API host. The API URL and last job ID are remembered; the
bearer token is not embedded in HTML or persisted by this UI. On resume, the total
timer starts from the backend's elapsed time. Existing image/catalog reports remain
available and video reports add MP4, job status, and timing.

## Local configuration

Use .env.example for required names; keep actual values in ignored .env only.
Set GIMMECLIP_API_KEY and a separate VIDEO_API_TOKEN. Run:

    python manage.py migrate
    python manage.py runserver
    python manage.py run_video_worker

The worker is sequential and protected by an OS file lock. Web and worker must
share the same database and MEDIA_ROOT. Inputs/generated photos remain in
media/video_jobs for retries; final videos are stored in Cloudinary.

## Render

render.yaml and Dockerfile start web and worker together through
`bash deploy/render-start.sh`. One paid 0.5c-512mb service with a 1 GB /var/data disk
is defined. Keep a single instance. SQLite and retry files need this shared disk;
a separate worker service cannot access that disk. Startup applies migrations at
runtime. Missing optional video keys disables only the worker, keeping image APIs up.

Before deployment push this branch, connect the Blueprint, set Cloudflare,
Cloudinary and Gimmeclip keys, and obtain VIDEO_API_TOKEN from Render Environment.
Use the actual Render service URL in the tester. CORS defaults to localhost:5500
and 127.0.0.1:5500; add the exact tester origin if it uses another port or host.
No Render deploy or paid generation is performed by the code checks.

## Verification

Provider HTTP tests use a local stand-in based on the Gimmeclip OpenAPI contract:
https://gimmeclip.com/openapi.json. Postman CLI is unavailable in this environment
because its managed Private Cloud manifest cannot be read, so requests/HTTP
stand-ins are used. Image/provider/Cloudinary integrations are not claimed live.

Commands:

    python manage.py test fabricapp.tests fabricapp.test_fabric_material fabricapp.test_all_garment_fabric fabricapp.test_video_jobs fabricapp.test_gimmeclip_http fabricapp.test_video_storage
    python -m unittest discover -s tools/tester_ui -p test_reports.py
    node tools/tester_ui/test_catalog_client.cjs
    node tools/tester_ui/tests/video_client.test.cjs
    node tools/tester_ui/tests/request_timer.test.cjs
    python manage.py check
    python manage.py makemigrations --check --dry-run

Browser smoke checks use a synthetic photo and local API fixture: original controls,
image preview, completion, video links, existing-photo animation, cancellation,
saved-job resume and live timing. This does not establish live model output quality.

The full original baseline suite has existing catalog reference/identity failures
(test_catalog_engine and test_kurta_catalog). Several catalog assertions are also
sensitive to concurrent call order. Catalog generation source is unchanged by this
branch; these unrelated failures are not claimed fixed. Docker/Render deployment
and live generation still need their own verification.
