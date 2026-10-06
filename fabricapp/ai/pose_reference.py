"""
Stage: Pose reference photos (data + two tiny lookups, no prompt logic).

For some (garment_type, pose) pairs there is a REFERENCE PHOTO of a model
already standing in that pose and wearing the garment. For those pairs the
pose is NOT described in the prompt. Instead the photo itself is sent as
image 0 and edited: only the fabric is replaced, everything else in the
photo (person, pose, drape, background) stays as it is.

Where the photos live (same style as the faces folder in prompts.py):
    fabricapp/ai/poses/<garment_type>/<pose>.jpg
    e.g. fabricapp/ai/poses/saree/pallu_on_head.jpg

To add another pose later: put its photo in that folder and add its
(garment_type, pose) pair to POSE_REFERENCE_KEYS below. Nothing else in
this file changes. (The prompt text for a new garment_type is in
prompt_parts.py / prompt_builder.py; today it exists only for the saree.)

Every other pose keeps using the normal prompt-only path.
"""

POSE_REFERENCE_DIR = "fabricapp/ai/poses"
POSE_REFERENCE_EXTENSION = ".jpg"

# (garment_type, pose) pairs that have a reference photo.
POSE_REFERENCE_KEYS = {
    ("saree", "pallu_on_head"),
}


def has_pose_reference(garment_type, pose):
    """True if this garment + pose has a reference photo registered."""
    return (garment_type, pose) in POSE_REFERENCE_KEYS


def get_pose_reference_path(garment_type, pose):
    """
    Returns the file path of the reference photo, or None if this
    garment + pose has none. Whether the file really exists on disk is
    checked when it is opened (cloudflare_engine.py), so a missing file
    gives a clear error instead of silently using the old path.
    """
    if not has_pose_reference(garment_type, pose):
        return None
    return f"{POSE_REFERENCE_DIR}/{garment_type}/{pose}{POSE_REFERENCE_EXTENSION}" 