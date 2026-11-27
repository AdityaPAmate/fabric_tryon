"""Frame one AI clip as sleeve detail, neckline detail, then a widening walk."""
from io import BytesIO
from pathlib import Path
import subprocess

from PIL import Image, ImageOps

from .collar import find_face, ffmpeg_path, FPS
from .errors import VideoError


def detail_boxes(image):
    """Use the face to estimate bounded detail regions; this is not pose tracking."""
    try:
        x, y, width, height = find_face(image)
    except VideoError as exc:
        raise VideoError('kurta_details_not_found',
                         'Use one clear front-facing person with the neckline and sleeves visible. Your image is saved.') from exc

    def box(left, top, view_width, view_height):
        if view_width < 48 or view_width > image.width or view_height > image.height:
            raise VideoError('kurta_details_not_found', 'The photo is too tightly framed for kurta detail shots. Your image is saved.')
        left = max(0, min(round(left), image.width - round(view_width)))
        top = max(0, min(round(top), image.height - round(view_height)))
        return left, top, round(view_width), round(view_height)

    centre = x + width / 2
    aspect = image.width / image.height
    sleeve_h = height * 4.6
    sleeve_w = sleeve_h * aspect
    sleeve = box(centre - width * .9 - sleeve_w / 2,
                 y + height * 1.9, sleeve_w, sleeve_h)
    neck_w = width * 2.6
    neckline = box(centre - neck_w / 2, y + height * .85,
                   neck_w, neck_w / aspect)
    return sleeve, neckline


def preflight(image_bytes):
    with Image.open(BytesIO(image_bytes)) as source:
        detail_boxes(ImageOps.exif_transpose(source).convert('RGB'))
    ffmpeg_path()


def content_box(frame, source_size):
    """Remove only verified black padding matching the source photo aspect ratio."""
    import numpy as np
    height, width = frame.shape[:2]
    ratio = min(width / source_size[0], height / source_size[1])
    w, h = round(source_size[0] * ratio), round(source_size[1] * ratio)
    x, y = (width - w) // 2, (height - h) // 2
    outside = np.ones((height, width), dtype=bool)
    outside[y:y+h, x:x+w] = False
    if outside.any() and frame[outside].max() > 12:
        return 0, 0, width, height
    return x, y, w, h


def render(provider_path, image_bytes, directory):
    import cv2
    with Image.open(BytesIO(image_bytes)) as source:
        source_size = ImageOps.exif_transpose(source).size
    capture = cv2.VideoCapture(str(provider_path), cv2.CAP_FFMPEG)
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        duration = capture.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps else 0
        ok, first = capture.read()
        if not ok or not 7.8 <= duration <= 9:
            raise VideoError('invalid_video', 'Kurta commercial needs an approximately eight-second clip.', True)
        active = content_box(first, source_size)
        ax, ay, aw, ah = active
        first_image = Image.fromarray(cv2.cvtColor(first[ay:ay+ah, ax:ax+aw], cv2.COLOR_BGR2RGB))
        sleeve, _ = detail_boxes(first_image)
        capture.set(cv2.CAP_PROP_POS_MSEC, 2000)
        ok, neck_frame = capture.read()
        if not ok:
            raise VideoError('invalid_video', 'Could not read the kurta neckline shot.', True)
        neck_image = Image.fromarray(cv2.cvtColor(neck_frame[ay:ay+ah, ax:ax+aw], cv2.COLOR_BGR2RGB))
        _, neckline = detail_boxes(neck_image)
    finally:
        capture.release()

    def crop(bounds):
        x, y, w, h = bounds
        return f'crop={w}:{h}:{x}:{y}'

    # Keep the provider's active picture size; enlarging to a fixed HD size
    # would not recover detail. H.264 requires even output dimensions.
    output_width, output_height = max(2, aw // 2 * 2), max(2, ah // 2 * 2)
    fit = (f'scale={output_width}:{output_height}:flags=lanczos,setsar=1,'
           f'fps={FPS},format=yuv420p')
    filters = (
        f'[0:v]{crop(active)},split=3[a][b][c];'
        f'[a]trim=start=0:end=2,setpts=PTS-STARTPTS,{crop(sleeve)},{fit}[sleeve];'
        f'[b]trim=start=2:end=3.5,setpts=PTS-STARTPTS,{crop(neckline)},{fit}[neck];'
        f'[c]trim=start=3.5:end=8,setpts=PTS-STARTPTS,'
        f"zoompan=z='max(1,1.5-0.5*on/71)':x='iw/2-iw/zoom/2':y=0:"
        f'd=1:s={output_width}x{output_height}:fps={FPS},setsar=1,format=yuv420p[walk];'
        '[sleeve][neck][walk]concat=n=3:v=1:a=0[out]'
    )
    output = Path(directory) / 'kurta-commercial.mp4'
    try:
        subprocess.run([ffmpeg_path(), '-hide_banner', '-nostdin', '-loglevel', 'error', '-y',
                        '-threads', '1', '-filter_complex_threads', '1', '-i', str(provider_path),
                        '-filter_complex', filters, '-map', '[out]', '-an', '-t', '8',
                        '-c:v', 'libx264', '-threads', '1', '-preset', 'veryfast', '-crf', '18',
                        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
    except (subprocess.SubprocessError, OSError) as exc:
        raise VideoError('video_composition_failed',
                         'Kurta detail views could not be assembled. Retry reuses the saved clip.', True) from exc
    return output, {'version': 'kurta-details-v2', 'sleeve_seconds': 2, 'neckline_seconds': 1.5,
                    'walk_start_seconds': 3.5, 'sleeve_box': list(sleeve),
                    'neckline_box': list(neckline), 'content_box': list(active)}
