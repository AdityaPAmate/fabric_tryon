"""Source-photo collar opening; Gimmeclip still supplies the moving body shots."""
from io import BytesIO
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageOps

from .errors import VideoError

MODEL = Path(__file__).parent / 'assets' / 'face_detection_yunet_2026may.onnx'
WIDTH, HEIGHT, FPS = 540, 960, 24


def ffmpeg_path():
    executable = shutil.which('ffmpeg')
    if not executable:
        raise VideoError('video_renderer_unavailable',
                         'The commercial video renderer is unavailable. Deploy the updated Docker image.', True)
    return executable


def find_face(image):
    import cv2
    import numpy as np
    ratio = min(1, 640 / max(image.size))
    size = (round(image.width * ratio), round(image.height * ratio))
    pixels = cv2.cvtColor(np.asarray(image.resize(size)), cv2.COLOR_RGB2BGR)
    detector = cv2.FaceDetectorYN.create(str(MODEL), '', size,
                                       score_threshold=.85, nms_threshold=.3, top_k=100)
    _, faces = detector.detect(pixels)
    if faces is None or len(faces) != 1:
        raise VideoError('collar_not_found',
                         'A single clear face is needed to locate the collar. Use a front-facing shirt image. Your image is saved.')
    return tuple(float(value) / ratio for value in faces[0, :4])


def prepare_collar(image_bytes):
    """Return original pixels and a bounded horizontal pan, never invented detail."""
    with Image.open(BytesIO(image_bytes)) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
    x, y, width, height = find_face(image)
    # Neck/collar starts just above the lower face edge. A little chest includes
    # the top buttons. Horizontal margin permits a subtle left-to-right slide.
    view_width = round(width * 1.8)
    view_height = round(width * 2)
    margin = max(4, round(width * .16))
    left = round(x + width / 2 - (view_width + margin) / 2)
    top = round(y + height * .8)
    right, bottom = left + view_width + margin, top + view_height
    if (view_width < 48 or left < 0 or top < 0 or right > image.width or
            bottom > image.height):
        raise VideoError('collar_not_found',
                         'The image does not include enough collar and upper chest for this opening. Your image is saved.')
    return image.crop((left, top, right, bottom)), view_width, (left, top, right, bottom)


def render_commercial(provider_path, image_bytes, directory):
    """Replace seconds 0-2 with a real collar pan; keep seconds 2-8 of AI motion.

    No extra generation or retiming. The provider prompt reserves 0-3.5s for
    sleeves so its retained 2-3.5s follows the source collar opening.
    """
    import cv2
    cap = cv2.VideoCapture(str(provider_path), cv2.CAP_FFMPEG)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps else 0
    finally:
        cap.release()
    if not 7.8 <= duration <= 9:
        raise VideoError('invalid_video', 'Commercial motion must be an approximately eight-second clip.', True)
    image, view_width, bounds = prepare_collar(image_bytes)
    directory = Path(directory)
    source_path, output_path = directory / 'collar.png', directory / 'commercial.mp4'
    image.save(source_path, 'PNG')
    fit = (f'scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease:force_divisible_by=2,'
           f'pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={FPS},format=yuv420p')
    filters = (
        f'[0:v]trim=duration=2,setpts=PTS-STARTPTS,'
        f'crop={view_width}:{image.height}:x=(iw-ow)*t/2:y=0,{fit}[collar];'
        f'[1:v]trim=start=2:end=8,setpts=PTS-STARTPTS,{fit}[motion];'
        '[collar][motion]concat=n=2:v=1:a=0[out]'
    )
    try:
        subprocess.run([ffmpeg_path(), '-hide_banner', '-nostdin', '-loglevel', 'error', '-y',
                        '-threads', '1', '-filter_complex_threads', '1',
                        '-loop', '1', '-framerate', str(FPS), '-i', str(source_path),
                        '-threads', '1', '-i', str(provider_path), '-filter_complex', filters,
                        '-map', '[out]', '-an', '-t', '8', '-c:v', 'libx264',
                        '-threads', '1', '-preset', 'veryfast', '-crf', '18',
                        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output_path)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
    except (subprocess.SubprocessError, OSError):
        raise VideoError('video_composition_failed',
                         'The collar opening could not be joined. Retry reuses the saved image and video.', True)
    return output_path, {'version': 'source-collar-pan-v1', 'opening_seconds': 2,
                         'provider_start_seconds': 2, 'collar_box': list(bounds),
                         'source_crop_size': list(image.size)}
