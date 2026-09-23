"""
Stage: Local-only debugging helpers (Option A from our earlier discussion).
These functions save copies of the images to disk ONLY when
SAVE_DEBUG_FILES is turned on in settings (set it True on localhost,
False in production). In production this module is still imported
(so nothing crashes), it simply does nothing when called.
"""

import os
from django.conf import settings

DEBUG_DIR = "debug"


def save_debug_copy(buffer, filename):
    """Save a copy of the exact resized image bytes sent to Cloudflare."""
    if not getattr(settings, "SAVE_DEBUG_FILES", False):
        return
    os.makedirs(DEBUG_DIR, exist_ok=True)
    path = os.path.join(DEBUG_DIR, filename)
    with open(path, "wb") as f:
        f.write(buffer.getvalue())
    buffer.seek(0)
    print(f"Debug copy saved: {path}")


def save_output_copy(image_bytes, filename):
    """Save a copy of the final generated output image."""
    if not getattr(settings, "SAVE_DEBUG_FILES", False):
        return
    os.makedirs(DEBUG_DIR, exist_ok=True)
    path = os.path.join(DEBUG_DIR, filename)
    with open(path, "wb") as f:
        f.write(image_bytes)
    print(f"Output copy saved: {path}")