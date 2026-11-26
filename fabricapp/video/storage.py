"""Keep completed video in durable Cloudinary storage, not web-server media."""
import cloudinary.uploader
from pathlib import Path
from .errors import VideoError
from .gimmeclip import GimmeclipClient, checked_url
from .continuity import check_continuity
from .rendering import render
from .timing import measure


def validate_download_url(url):
    checked_url(url, 'video')


def store_video(url, job_id, *, profile=None, source_bytes=None, allow_cuts=False):
    profile = profile or {}
    allow_cuts = allow_cuts or profile.get('multi_shot', False)
    timing = {}
    validate_download_url(url)
    # Authenticate only to Gimmeclip's validated clip endpoint; redirects are disabled.
    try:
        client = GimmeclipClient()
        with measure(timing, 'download'):
            download = client.download(url)
        with download as response:
            if response.status_code != 200:
                raise VideoError('download_failed', 'Generated video could not be downloaded.', True)
            import tempfile
            with tempfile.TemporaryDirectory(prefix='fabric-video-') as directory:
                path = Path(directory) / 'animation.mp4'
                total = 0
                with measure(timing, 'download'), path.open('wb') as content:
                    for chunk in response.iter_content(64 * 1024):
                        total += len(chunk)
                        if total > 100 * 1024 * 1024:
                            raise VideoError('video_too_large', 'Generated video exceeds the 100 MB limit.')
                        content.write(chunk)
                with path.open('rb') as content:
                    if b'ftyp' not in content.read(32):
                        raise VideoError('invalid_video', 'Provider output is not an MP4 video.', True)
                with measure(timing, 'validation'):
                    continuity = check_continuity(path, allow_cuts=allow_cuts)
                with measure(timing, 'render'):
                    path, composition = render(profile, path, source_bytes, directory)
                if composition is not None:
                    with measure(timing, 'validation'):
                        continuity = check_continuity(path, allow_cuts=True)
                with path.open('rb') as content:
                    with measure(timing, 'final_upload'):
                        result = cloudinary.uploader.upload(content, resource_type='video',
                            folder='vastra-tryon/videos', public_id=str(job_id), overwrite=True)
    except VideoError:
        raise
    except Exception:
        raise VideoError('video_storage_failed', 'Generated video could not be stored. Retry will reuse the existing result.', True)
    if not isinstance(result, dict) or not result.get('secure_url'):
        raise VideoError('video_storage_failed', 'Video storage returned no delivery URL.', True)
    video = {'url': result['secure_url'], 'public_id': result.get('public_id'),
            'duration': result.get('duration'), 'format': result.get('format', 'mp4'),
            'continuity': continuity, 'timing': timing}
    if composition is not None:
        video['composition'] = composition
    return video
