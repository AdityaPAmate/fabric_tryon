"""PixVerse V6 through Cloudflare's documented synchronous /ai/run endpoint.

No automatic POST retry: an interrupted response might already have spent credits.
Cloudflare credentials never accompany the subsequent public CDN download.
"""
import base64
import re
from io import BytesIO
from urllib.parse import urlsplit
import requests
from PIL import Image
from django.conf import settings
from .errors import VideoError
from .gimmeclip import provider_error_details


def checked_video_url(url):
    if not isinstance(url, str):
        raise VideoError('invalid_video_response', 'PixVerse returned no video URL.', True)
    try:
        parsed = urlsplit(url)
    except ValueError:
        raise VideoError('invalid_video_response', 'PixVerse returned an invalid video URL.', True)
    if (parsed.scheme != 'https' or parsed.netloc != 'media.pixverse.ai' or
            parsed.username or parsed.password or parsed.fragment or not parsed.path.endswith('.mp4')):
        raise VideoError('invalid_video_response', 'PixVerse returned an untrusted video URL.', True)
    return url


class PixverseClient:
    def generate(self, image_bytes, profile):
        account = (settings.CLOUDFLARE_ACCOUNT_ID or '').strip()
        token = (settings.CLOUDFLARE_API_TOKEN or '').strip()
        if not re.fullmatch(r'[a-fA-F0-9]{32}', account) or not token:
            raise VideoError('provider_not_configured', 'Shirt commercial needs the existing Cloudflare account ID and API token.')
        if not 0 < len(image_bytes) <= 10 * 1024 * 1024:
            raise VideoError('invalid_source_image', 'Commercial reference image must be at most 10 MB.')
        try:
            with Image.open(BytesIO(image_bytes)) as image:
                mime = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}[image.format]
        except (OSError, ValueError, KeyError):
            raise VideoError('invalid_source_image', 'Commercial reference must be PNG, JPEG or WebP.')
        if not 1 <= len(profile['prompt']) <= 2048 or len(profile['negative_prompt']) > 2048:
            raise VideoError('invalid_motion_profile', 'PixVerse prompt exceeds its 2048-character limit.')
        payload = {'model': 'pixverse/v6', 'input': {
            'image_input': f'data:{mime};base64,' + base64.b64encode(image_bytes).decode('ascii'),
            'prompt': profile['prompt'], 'negative_prompt': profile['negative_prompt'],
            'duration': profile['seconds'], 'quality': profile['quality'],
            'aspect_ratio': profile['aspect_ratio'], 'generate_audio': False,
        }}
        try:
            response = requests.post(
                f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/run',
                headers={'Authorization': 'Bearer ' + token, 'cf-aig-max-attempts': '1',
                         'cf-aig-skip-cache': 'true'},
                json=payload, timeout=(10, 300), allow_redirects=False)
        except requests.RequestException:
            raise VideoError('submission_unknown', 'PixVerse submission outcome is unknown. Check Cloudflare AI Gateway history before generating again.')
        with response:
            status = response.status_code
            if status < 400 or status >= 500 or status == 408:
                if status != 200:
                    raise VideoError('submission_unknown', f'Cloudflare PixVerse returned HTTP {status}; submission outcome is unknown.')
            try:
                result = response.json()
                if not isinstance(result, dict):
                    raise ValueError()
            except ValueError:
                raise VideoError('submission_unknown', 'Cloudflare returned an unreadable PixVerse response. Check provider history.')
            if status != 200 or result.get('success') is False or result.get('state') in ('Failed', 'Error'):
                errors = result.get('errors')
                reason = result.get('error')
                if isinstance(errors, list) and errors and isinstance(errors[0], dict):
                    reason = errors[0].get('message') or reason
                details = provider_error_details({'error': reason})
                message = details.get('message') or 'Check Cloudflare Workers AI access and Unified billing credits.'
                raise VideoError('provider_failed', f'Cloudflare PixVerse HTTP {status}: {message}'[:300], details=details)
            if result.get('state') not in (None, 'Completed'):
                raise VideoError('submission_unknown', 'PixVerse has not confirmed completion. Check Cloudflare history before generating again.')
            video = result.get('result')
            if not isinstance(video, dict) or not video.get('video'):
                raise VideoError('submission_unknown', 'PixVerse did not confirm a completed video. Check Cloudflare history before generating again.')
            try:
                return checked_video_url(video['video'])
            except VideoError:
                raise VideoError('submission_unknown', 'PixVerse returned an untrusted output URL. Check Cloudflare history before generating again.')

    def download(self, url):
        return requests.get(checked_video_url(url), headers={'Accept': 'video/mp4'},
                            stream=True, timeout=(10, 120), allow_redirects=False)
