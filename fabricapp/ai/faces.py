"""Predefined face choices and face-image path lookup."""

from pathlib import Path


FACE_IMAGE_DIR = Path(__file__).resolve().parent / "faces"
FACE_IMAGE_EXTENSION = ".png"

FACE_OPTIONS = {
    "men": ["raghav", "vihaan"],
    "women": ["anaya", "poonam"],
}


def get_face_image_path(face_choice):
    """Return the absolute path for a known face, otherwise None."""
    all_faces = {
        face_name
        for face_names in FACE_OPTIONS.values()
        for face_name in face_names
    }

    if face_choice not in all_faces:
        return None

    return FACE_IMAGE_DIR / f"{face_choice}{FACE_IMAGE_EXTENSION}"