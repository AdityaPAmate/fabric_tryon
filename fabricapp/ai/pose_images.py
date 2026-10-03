"""
Stage: Pose reference images -> pose GUIDE (flat silhouette).

A pose image (stored by pose name, or uploaded by the customer as
pose_image) is NEVER sent to the model as a photo. It is first turned
into a flat grey silhouette on a white background, so it contains only
the body outline: no face, no clothes, no fabric colours, no jewellery,
no background. The model can then take ONLY the pose from it.

Folder layout (inside fabricapp/ai/poses/):
    poses/<pose>.png                 -> normal image, works for every garment
    poses/<garment_type>/<pose>.png  -> garment-specific image (e.g. poses/saree/)
    poses/_guides/...                -> generated silhouettes (cache, do not edit)
Lookup order: garment folder first, then the normal folder.
Saree-only poses are kept only in poses/saree/.

The silhouette of a stored image is made once and cached in poses/_guides/.
Customer uploads (pose_image) are converted on every request.

Needs (only when a silhouette has to be made): pip install rembg onnxruntime
"""

import io
import logging
from pathlib import Path

from PIL import Image, ImageOps

logger = logging.getLogger("fabricapp")

POSE_IMAGE_DIR = Path(__file__).resolve().parent / "poses"
POSE_GUIDE_DIR = POSE_IMAGE_DIR / "_guides"
POSE_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")

# True  -> the written pose sentence (pose_data.py) is sent TOGETHER with the
#          silhouette (the text adds what a silhouette cannot show: hands
#          held in front of the body, eye direction, ...).
# False -> only the silhouette is used for a named pose (to test it alone).
POSE_TEXT_WITH_GUIDE = True

GUIDE_MAX_DIM = 511
GUIDE_FIGURE_COLOR = (110, 110, 110)
GUIDE_BACKGROUND_COLOR = (255, 255, 255)
REMBG_MODEL_NAME = "silueta"  # small (~43 MB) background-removal model

_session = None


class PoseGuideError(Exception):
    """Raised when a pose silhouette cannot be made."""
    pass


def _find(folder, pose):
    for ext in POSE_IMAGE_EXTENSIONS:
        path = folder / f"{pose}{ext}"
        if path.is_file():
            return path
    return None


def get_pose_image_path(pose, garment_type=None):
    """Returns the Path of the stored pose image, or None if no image exists."""
    if not pose:
        return None
    if garment_type:
        found = _find(POSE_IMAGE_DIR / garment_type, pose)
        if found:
            return found
    return _find(POSE_IMAGE_DIR, pose)


def make_pose_guide_image(source):
    """
    source: a file path, or a file-like object (an uploaded image).
    Returns a PIL image: grey person-shaped silhouette on white.
    """
    global _session
    try:
        from rembg import remove, new_session
    except ImportError:
        raise PoseGuideError("rembg is not installed. Run: pip install rembg onnxruntime")

    try:
        if hasattr(source, "seek"):
            source.seek(0)
        image = Image.open(source)
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((GUIDE_MAX_DIM, GUIDE_MAX_DIM))

        if _session is None:
            _session = new_session(REMBG_MODEL_NAME)
        mask = remove(image, session=_session, only_mask=True)
        mask = mask.convert("L").point(lambda v: 255 if v >= 128 else 0)

        figure = Image.new("RGB", image.size, GUIDE_FIGURE_COLOR)
        background = Image.new("RGB", image.size, GUIDE_BACKGROUND_COLOR)
        return Image.composite(figure, background, mask)
    except PoseGuideError:
        raise
    except Exception as e:
        raise PoseGuideError(f"Could not make the pose silhouette: {e}")


def _to_png_buffer(image):
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)
    return buffer


def make_pose_guide_buffer(source):
    """Silhouette of an uploaded / given image as a PNG buffer."""
    return _to_png_buffer(make_pose_guide_image(source))


def get_stored_pose_guide(image_path, force=False):
    """
    Silhouette of a stored pose image as a PNG buffer. Made once, then
    read from poses/_guides/ (rembg is not needed once the file exists).
    """
    image_path = Path(image_path)
    relative = image_path.relative_to(POSE_IMAGE_DIR).with_suffix(".png")
    guide_path = POSE_GUIDE_DIR / relative

    if (
        not force
        and guide_path.is_file()
        and guide_path.stat().st_mtime >= image_path.stat().st_mtime
    ):
        return io.BytesIO(guide_path.read_bytes())

    guide = make_pose_guide_image(str(image_path))
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    guide.save(guide_path, "PNG")
    logger.info("Pose silhouette created: %s", guide_path)
    return io.BytesIO(guide_path.read_bytes())


def build_all_guides():
    """
    Makes (or remakes) the silhouette of EVERY stored pose image, so you can
    open poses/_guides/ and check each one by eye.
    Run: py manage.py shell -c "from fabricapp.ai.pose_images import build_all_guides; build_all_guides()"
    """
    count = 0
    for path in sorted(POSE_IMAGE_DIR.rglob("*")):
        if path.suffix.lower() not in POSE_IMAGE_EXTENSIONS:
            continue
        if POSE_GUIDE_DIR in path.parents:
            continue
        get_stored_pose_guide(path, force=True)
        relative = path.relative_to(POSE_IMAGE_DIR).with_suffix(".png")
        print(f"OK  {path}  ->  {POSE_GUIDE_DIR / relative}")
        count += 1
    print(f"Done: {count} silhouette(s) made.")


def report():
    """
    Shows which pose images / silhouettes exist.
    Run: py manage.py shell -c "from fabricapp.ai.pose_images import report; report()"
    """
    from .pose_data import POSE_OPTIONS, POSE_ONLY_FOR

    print(f"POSE_TEXT_WITH_GUIDE = {POSE_TEXT_WITH_GUIDE}")
    for pose in POSE_OPTIONS:
        normal = _find(POSE_IMAGE_DIR, pose)
        saree = _find(POSE_IMAGE_DIR / "saree", pose)
        only = " (saree-only)" if pose in POSE_ONLY_FOR else ""
        normal_guide = (POSE_GUIDE_DIR / f"{pose}.png").is_file()
        saree_guide = (POSE_GUIDE_DIR / "saree" / f"{pose}.png").is_file()
        print(
            f"{pose}{only}: normal image={'YES' if normal else 'no'} "
            f"(silhouette={'YES' if normal_guide else 'no'})  "
            f"saree image={'YES' if saree else 'no'} "
            f"(silhouette={'YES' if saree_guide else 'no'})"
        )