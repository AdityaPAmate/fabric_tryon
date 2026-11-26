"""Persist stage boundaries so retries reuse successful image/provider work."""
import logging
import time
from datetime import timedelta
from contextlib import ExitStack
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from fabricapp.models import VideoJob
from fabricapp.services.tryon_service import generate_image
from fabricapp.services.cloudinary_service import upload_generated_image
from .gimmeclip import GimmeclipClient
from .errors import VideoError
from .profiles import select_profile
from .storage import store_video
from .rendering import preflight, renderer_name
from .timing import measure
from .source import metadata as source_metadata

logger = logging.getLogger(__name__)


def save(job, **fields):
    for key, value in fields.items():
        setattr(job, key, value)
    job.save(update_fields=[*fields, 'updated_at'])


def create_job(data):
    data = dict(data)
    profile = select_profile(data)
    data.pop('video_motion', None)
    source_image = data.pop('source_image', None)
    uploads = {key: data.pop(key) for key in ('fabric_image', 'face_image', 'person_image', 'garment_image') if data.get(key)}
    if 'person_image' in uploads:
        data['_has_person_image'] = True
    job = VideoJob.objects.create(payload=data, status='preparing',
                                  profile_version=profile['version'], motion_profile=profile)
    stored = []
    try:
        paths = {}
        for key, upload in uploads.items():
            upload.seek(0)
            # ImageField already checked the content; filenames never come from the caller.
            path = default_storage.save(f'video_jobs/{job.pk}/inputs/{key}', upload)
            paths[key] = path
            stored.append(path)
        image_file = ''
        if source_image is not None:
            source_image.seek(0)
            image_file = default_storage.save(f'video_jobs/{job.pk}/generated_image', source_image)
            stored.append(image_file)
            with default_storage.open(image_file, 'rb') as content:
                data['_video_source'] = source_metadata(content.read())
        save(job, payload=data, image_file=image_file, inputs=paths, status='queued')
    except Exception:
        for path in stored:
            default_storage.delete(path)
        job.delete()
        raise
    return job


def process_job(job):
    """Called only by the exclusive worker; no request thread runs generation."""
    try:
        if job.status == 'completed':
            return
        if job.motion_profile.get('provider') == 'cloudflare_pixverse':
            raise VideoError('legacy_provider_job', 'This saved commercial job used the removed provider. Its image is preserved; create a new Gimmeclip commercial job.')
        if job.polling_url and not job.polling_url.startswith('https://gimmeclip.com/api/v0/edits/'):
            raise VideoError('legacy_provider_job', 'This saved job belongs to the previous video provider. Its references are preserved; create a new Gimmeclip job.')
        if job.status == 'video_submitting' and not job.polling_url:
            raise VideoError('submission_unknown', 'Worker stopped during submission. Check Gimmeclip history before submitting again.')
        if not settings.GIMMECLIP_API_KEY:
            raise VideoError('provider_not_configured', 'GIMMECLIP_API_KEY is not configured.', True)
        timing = dict(job.timing)
        timing.setdefault('started_at', time.time())
        save(job, timing=timing, attempts=job.attempts + 1, error_code='', error_message='',
             provider_error={}, retryable=False)
        if not job.image:
            save(job, status='image_generating')
            if not job.image_file:
                with ExitStack() as stack:
                    data = dict(job.payload)
                    for key, path in job.inputs.items():
                        data[key] = stack.enter_context(default_storage.open(path, 'rb'))
                    if data.get('garment_image'):
                        # garment_type is video context; keep the ready-image
                        # adapter's original inputs and validation semantics.
                        data.pop('garment_type', None)
                    generation = generate_image(data)
                path = default_storage.save(f'video_jobs/{job.pk}/generated_image', ContentFile(generation.image_bytes))
                timing = {**job.timing, 'image_ready_at': time.time()}
                save(job, timing=timing, image_file=path, payload={**job.payload,
                     '_image_seed': generation.effective_seed, '_video_source': source_metadata(generation.image_bytes)})
            with default_storage.open(job.image_file, 'rb') as content:
                with measure(timing, 'image_upload'):
                    image = upload_generated_image(content.read())
            save(job, timing=timing)
            save(job, image=image)
        source_bytes = None
        if renderer_name(job.motion_profile) != 'passthrough':
            with default_storage.open(job.image_file, 'rb') as content:
                source_bytes = content.read()
            # Validate the opening before paying for a new animation. Retries
            # use the same saved source image and never a guessed fixed crop.
            preflight(job.motion_profile, source_bytes)
        client = GimmeclipClient()
        if not job.polling_url and not job.provider_video_url:
            if not job.source_photo_url:
                with default_storage.open(job.image_file, 'rb') as content:
                    timing = dict(job.timing)
                    with measure(timing, 'provider_photo_upload'):
                        photo_url = client.upload_photo(content.read())
                save(job, source_photo_url=photo_url, timing=timing)
            save(job, status='video_submitting', timing={**job.timing, 'video_submitted_at': time.time()})
            profile = job.motion_profile
            polling_url = client.submit(job.source_photo_url, profile)
            save(job, polling_url=polling_url, status='video_generating')
        if not job.provider_video_url:
            save(job, status='video_generating')
            deadline = time.monotonic() + settings.VIDEO_POLL_TIMEOUT
            while time.monotonic() < deadline:
                url = client.poll(job.polling_url)
                if url:
                    timing = dict(job.timing)
                    timing.setdefault('video_ready_at', time.time())
                    save(job, timing=timing, provider_video_url=url)
                    break
                time.sleep(settings.VIDEO_POLL_INTERVAL)
            else:
                raise VideoError('poll_timeout', 'Video is still pending. Retry will check the same Gimmeclip job.', True)
        save(job, status='video_storing')
        video = store_video(job.provider_video_url, job.pk, profile=job.motion_profile,
                            source_bytes=source_bytes)
        # Storage timings are part of the saved final result as well as job timing.
        timing = {**job.timing, **video.get('timing', {})}
        save(job, video=video, status='completed', timing={**timing, 'completed_at': time.time()})
        logger.info('Video job %s completed: %s', job.pk, timing_response(job))
    except VideoError as exc:
        save(job, status='failed', error_code=exc.code, error_message=str(exc),
             provider_error=exc.details, retryable=exc.retryable)
    except Exception:
        # Unknown exceptions around POST must never trigger an automatic second submission.
        ambiguous = job.status == 'video_submitting' and not job.polling_url
        logger.exception('Video job %s failed in stage %s', job.pk, job.status)
        save(job, status='failed', error_code='submission_unknown' if ambiguous else 'stage_failed',
             error_message=('Submission outcome is unknown; check Gimmeclip history.' if ambiguous
                            else 'This stage failed. Retry will reuse saved work.'), retryable=not ambiguous)


def can_retry(job):
    # Old visual-check failures already have a finished provider clip. Recover it
    # under the advisory check instead of paying to generate the image/video again.
    return job.status == 'failed' and (job.retryable or (
        job.error_code == 'video_continuity_failed' and bool(job.provider_video_url)))


def fail_stale_preparing():
    """A hard crash while saving inputs must not leave an invisible job forever.

    Do not guess which files were complete or pay for generation. Keep any files
    for inspection and explicitly fail this incomplete request after one hour.
    """
    return VideoJob.objects.filter(status='preparing', updated_at__lt=timezone.now() - timedelta(hours=1)).update(
        status='failed', error_code='inputs_incomplete',
        error_message='Input saving was interrupted. Create a new video request with the source image.',
        retryable=False, updated_at=timezone.now())


def job_response(job):
    message = job.error_message
    if job.error_code == 'video_continuity_failed' and can_retry(job):
        message = 'Saved video was blocked by an earlier visual check. Retry recovers the same clip for review; no new generation.'
    return {
        'job_id': str(job.pk), 'status': job.status,
        'status_url': f'/api/video-jobs/{job.pk}/',
        'image': job.image or None, 'video': job.video or None,
        'garment_type': job.payload.get('garment_type', 'garment'),
        'timing': timing_response(job), 'motion': job.motion_profile.get('motion'),
        'profile_version': job.profile_version,
        'quality_status': ('needs_review' if job.video.get('continuity', {}).get('status') == 'review_required'
                           else 'not_verified'),
        'error': ({'code': job.error_code, 'message': message,
                   'retryable': can_retry(job), 'provider': job.provider_error or None}
                  if job.status == 'failed' else None),
        'created_at': job.created_at.isoformat(), 'updated_at': job.updated_at.isoformat(),
    }


def timing_response(job):
    """Wall-clock timings include provider queue/poll intervals and paused workers."""
    timing = job.timing
    now = job.updated_at.timestamp() if job.status == 'failed' else time.time()
    def duration(start, end):
        if start not in timing:
            return None
        return round(max(0, timing.get(end, now) - timing[start]), 2)
    return {
        'total_seconds': duration('started_at', 'completed_at') if job.status == 'completed' else None,
        'elapsed_seconds': duration('started_at', 'completed_at'),
        'image_generation_seconds': duration('started_at', 'image_ready_at') if 'image_ready_at' in timing else None,
        'video_generation_seconds': duration('video_submitted_at', 'video_ready_at'),
        'queue_wait_seconds': round(max(0, timing['started_at'] - job.created_at.timestamp()), 2)
                              if 'started_at' in timing else None,
        'request_to_ready_seconds': round(max(0, timing['completed_at'] - job.created_at.timestamp()), 2)
                                    if job.status == 'completed' and 'completed_at' in timing else None,
        'post_generation_seconds': duration('video_ready_at', 'completed_at'),
        **{key: timing.get(key) for key in ('image_upload_seconds', 'provider_photo_upload_seconds',
            'download_seconds', 'validation_seconds', 'render_seconds', 'final_upload_seconds')},
    }
