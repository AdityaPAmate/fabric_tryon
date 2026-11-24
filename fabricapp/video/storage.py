"""Keep completed video in durable Cloudinary storage, not web-server media."""
import cloudinary.uploader
from pathlib import Path
from .errors import VideoError
from .gimmeclip import GimmeclipClient, checked_url
from .continuity import check_continuity


def validate_download_url(url):
    checked_url(url, 'video')


def store_video(url, job_id):
    validate_download_url(url)
    # Authenticate only to Gimmeclip's validated clip endpoint; redirects are disabled.
    try:
        with GimmeclipClient().download(url) as response:
            if response.status_code != 200:
                raise VideoError('download_failed', 'Generated video could not be downloaded.', True)
            import tempfile
            with tempfile.TemporaryDirectory(prefix='fabric-video-') as directory:
                path = Path(directory) / 'animation.mp4'
                total = 0
                with path.open('wb') as content:
                    for chunk in response.iter_content(64 * 1024):
                        total += len(chunk)
                        if total > 100 * 1024 * 1024:
                            raise VideoError('video_too_large', 'Generated video exceeds the 100 MB limit.')
                        content.write(chunk)
                with path.open('rb') as content:
                    if b'ftyp' not in content.read(32):
                        raise VideoError('invalid_video', 'Provider output is not an MP4 video.', True)
                continuity = check_continuity(path)
                with path.open('rb') as content:
                    result = cloudinary.uploader.upload(content, resource_type='video',
                        folder='vastra-tryon/videos', public_id=str(job_id), overwrite=True)
    except VideoError:
        raise
    except Exception:
        raise VideoError('video_storage_failed', 'Generated video could not be stored. Retry will reuse the existing result.', True)
    if not isinstance(result, dict) or not result.get('secure_url'):
        raise VideoError('video_storage_failed', 'Video storage returned no delivery URL.', True)
    return {'url': result['secure_url'], 'public_id': result.get('public_id'),
            'duration': result.get('duration'), 'format': result.get('format', 'mp4'),
            'continuity': continuity}
