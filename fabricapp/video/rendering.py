"""Video rendering dispatch, independent of provider calls and delivery."""
from .errors import VideoError


def renderer_name(profile):
    # Jobs created before the registry used only this boolean. Keep retries stable.
    name = profile.get('renderer') or ('shirt_collar' if profile.get('source_collar_opening') else 'passthrough')
    if name not in ('passthrough', 'shirt_collar'):
        raise VideoError('invalid_motion_profile', 'This saved video renderer is not supported.')
    return name


def preflight(profile, source_bytes):
    if renderer_name(profile) == 'shirt_collar':
        from .collar import prepare_collar, ffmpeg_path
        prepare_collar(source_bytes)
        ffmpeg_path()


def render(profile, provider_path, source_bytes, directory):
    if renderer_name(profile) == 'shirt_collar':
        from .collar import render_commercial
        return render_commercial(provider_path, source_bytes, directory)
    return provider_path, None
