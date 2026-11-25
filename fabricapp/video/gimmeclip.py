"""Photo animation contract: https://gimmeclip.com/openapi.json.

Never automatically retry an ambiguous edit POST. Only fixed provider paths
receive the key; redirects are disabled on every request.
"""
import re
from io import BytesIO
from PIL import Image
import requests
from django.conf import settings
from .errors import VideoError

BASE = 'https://gimmeclip.com'


def provider_error_details(result):
    """Retain useful diagnostics without credentials, source URLs or raw payloads."""
    details = {}
    code = result.get('code')
    if isinstance(code, str) and re.fullmatch(r'[a-z_]{1,48}', code):
        details['code'] = code
    stage = result.get('failedStage')
    if stage in ('source', 'generating', 'transcribing', 'translating', 'rendering', 'saving'):
        details['stage'] = stage
    message = result.get('error')
    if isinstance(message, str):
        for secret in (settings.GIMMECLIP_API_KEY, settings.VIDEO_API_TOKEN, settings.CLOUDFLARE_API_TOKEN):
            if secret:
                message = message.replace(secret, '[redacted]')
        message = re.sub(r'gc_[A-Za-z0-9_-]+|Bearer\s+\S+|https?://\S+', '[redacted]', message, flags=re.I)
        details['message'] = ' '.join(message.split())[:200]
    return details


def checked_url(url, kind):
    patterns = {'photo': r'/api/v0/photos/[a-f0-9]{32}',
                'job': r'/api/v0/edits/[a-f0-9]{64}',
                'video': r'/api/v0/clips/[a-f0-9]{64}/file'}
    if not isinstance(url, str) or not re.fullmatch(re.escape(BASE) + patterns[kind], url):
        raise VideoError('invalid_provider_response', f'Gimmeclip returned an invalid {kind} URL.')
    return url


class GimmeclipClient:
    def __init__(self):
        self.key = settings.GIMMECLIP_API_KEY.strip()

    def _request(self, method, url, *, submission=False, **kwargs):
        headers = {'Authorization': 'Bearer ' + self.key, 'User-Agent': 'VastraTryOn/1.0'}
        headers.update(kwargs.pop('headers', {}))
        try:
            response = requests.request(method, url, headers=headers, timeout=(10, 120),
                                        allow_redirects=False, **kwargs)
        except requests.RequestException:
            raise VideoError('submission_unknown' if submission else 'provider_unavailable',
                             'Gimmeclip submission outcome is unknown. Check provider history.' if submission
                             else 'Gimmeclip is temporarily unavailable.', not submission)
        if response.status_code not in (200, 201, 202):
            status = response.status_code
            response.close()
            if submission and (status < 400 or status >= 500 or status == 408):
                raise VideoError('submission_unknown', 'Gimmeclip did not confirm submission. Check provider history.')
            code = {401: 'invalid_provider_key', 402: 'payment_required', 403: 'provider_forbidden',
                    429: 'quota_exceeded'}.get(status, 'provider_rejected')
            raise VideoError(code, f'Gimmeclip returned HTTP {status}.',
                             status == 429 or (not submission and status >= 500))
        return response

    def _json(self, method, url, **kwargs):
        submission = kwargs.get('submission', False)
        with self._request(method, url, **kwargs) as response:
            try:
                result = response.json()
                if not isinstance(result, dict):
                    raise ValueError()
                return result
            except ValueError:
                raise VideoError('submission_unknown' if submission else 'invalid_provider_response',
                                 'Gimmeclip returned an unreadable response.', not submission)

    def upload_photo(self, image_bytes):
        config = self._json('GET', BASE + '/api/v0/edits/config')
        allowance = config.get('aiEdit')
        if not isinstance(allowance, dict):
            raise VideoError('animation_unavailable', 'Gimmeclip photo animation is unavailable.')
        if allowance.get('left') == 0 or allowance.get('perDay') == 0:
            raise VideoError('quota_exceeded', 'Gimmeclip animation quota is exhausted.', True)
        try:
            with Image.open(BytesIO(image_bytes)) as image:
                mime = {'PNG': 'image/png', 'JPEG': 'image/jpeg', 'WEBP': 'image/webp'}[image.format]
        except (OSError, ValueError, KeyError):
            raise VideoError('invalid_source_image', 'Generated photo must be PNG, JPEG or WebP.')
        if not 0 < len(image_bytes) <= 10 * 1024 * 1024:
            raise VideoError('source_image_too_large', 'Gimmeclip accepts photos up to 10 MB.')
        result = self._json('POST', BASE + '/api/v0/photos', data=image_bytes,
                            headers={'Content-Type': mime})
        return checked_url(result.get('url'), 'photo')

    def submit(self, photo_url, profile):
        checked_url(photo_url, 'photo')
        prompt, seconds = profile['prompt'], profile['seconds']
        if not 3 <= len(prompt) <= 300 or seconds not in (4, 6, 8):
            raise VideoError('invalid_motion_profile', 'Gimmeclip needs a 3-300 character prompt and 4, 6 or 8 seconds.')
        recipe = {'v': 1, 'source': {'url': photo_url, 'start': 0, 'end': seconds},
                  'frame': 'original', 'aiEdit': {'idea': prompt, 'animate': True}}
        result = self._json('POST', BASE + '/api/v0/edits', submission=True, json={'recipe': recipe})
        job_id = result.get('id')
        if not isinstance(job_id, str) or not re.fullmatch(r'[a-f0-9]{64}', job_id):
            raise VideoError('submission_unknown', 'Gimmeclip did not return a valid job ID. Check provider history.')
        return BASE + '/api/v0/edits/' + job_id

    def poll(self, url):
        result = self._json('GET', checked_url(url, 'job'))
        state = result.get('state')
        if state in ('source', 'generating', 'transcribing', 'translating', 'rendering', 'saving'):
            return None
        if state == 'error':
            details = provider_error_details(result)
            message = details.get('message') or details.get('code') or 'Provider returned no detailed reason.'
            stage = details.get('stage', 'video generation')
            raise VideoError('provider_failed', f'Gimmeclip failed at {stage}: {message}'[:300], details=details)
        if state != 'done':
            raise VideoError('invalid_provider_response', 'Gimmeclip returned an unknown state.', True)
        # Match GimmeVideoLab: the completed edit is the delivered output.
        clip = result.get('clip')
        clip_id = (clip.get('id') if isinstance(clip, dict) else None) or result.get('aiClip')
        if not isinstance(clip_id, str) or not re.fullmatch(r'[a-f0-9]{64}', clip_id):
            raise VideoError('invalid_video_response',
                             'Gimmeclip completed without a valid clip ID. Retry will check the same job.', True)
        return BASE + '/api/v0/clips/' + clip_id + '/file'

    def download(self, url):
        return self._request('GET', checked_url(url, 'video'), stream=True,
                             headers={'Accept': 'video/mp4'})
