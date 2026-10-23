"""Registry for garment-specific pose options and metadata.

Each garment package owns its pose definitions in its own poses.py.

Expected export for new garment pose files:

    POSES = {
        "pose_key": {
            "hides_face": False,
            "requires_full_body": True,
        },
    }

Saree currently exports SAREE_POSES. The registry supports that existing
shape while the other garment pose files are being populated.
"""

from functools import lru_cache
from importlib import import_module


POSE_MODULES = {
    "blazer": "fabricapp.ai.blazer.poses",
    "kurta": "fabricapp.ai.kurta.poses",
    "kurti_pant": "fabricapp.ai.kurti_pant.poses",
    "pant": "fabricapp.ai.pant.poses",
    "saree": "fabricapp.ai.saree.poses",
    "shirt": "fabricapp.ai.shirt.poses",
}


class PoseRegistryError(Exception):
    """Raised when a garment pose module has an invalid structure."""


@lru_cache(maxsize=None)
def _load_pose_data(garment_type):
    """Load one garment's pose definitions."""
    module_path = POSE_MODULES.get(garment_type)
    if module_path is None:
        return {}

    module = import_module(module_path)

    # New garment files should export POSES. Support SAREE_POSES as a
    # compatibility path for the existing saree implementation.
    pose_data = getattr(module, "POSES", None)
    if pose_data is None and garment_type == "saree":
        pose_data = getattr(module, "SAREE_POSES", None)

    # Empty pose files are valid while the architecture is being filled in.
    if pose_data is None:
        return {}

    if not isinstance(pose_data, dict):
        raise PoseRegistryError(
            f"{module_path} must export POSES as a dictionary."
        )

    return pose_data


def get_pose_options(garment_type=None):
    """Return pose keys for one garment, or the union across garments."""
    if garment_type is not None:
        return list(_load_pose_data(garment_type).keys())

    all_options = []
    seen = set()

    for garment in POSE_MODULES:
        for pose in _load_pose_data(garment):
            if pose not in seen:
                seen.add(pose)
                all_options.append(pose)

    return all_options


def get_pose_metadata(garment_type, pose):
    """Return metadata for a garment pose, or None if the pose is unknown."""
    if not garment_type or not pose:
        return None

    entry = _load_pose_data(garment_type).get(pose)
    if entry is None:
        return None

    # A pose entry may be a metadata dictionary, or just its prompt text.
    if not isinstance(entry, dict):
        return {
            "hides_face": False,
            "requires_full_body": False,
        }

    return {
        "hides_face": bool(entry.get("hides_face", False)),
        "requires_full_body": bool(entry.get("requires_full_body", False)),
        **{
            key: value
            for key, value in entry.items()
            if key not in {"hides_face", "requires_full_body"}
        },
    }


def get_pose_sentence(pose, garment_type=None, garment_style=None, detail_keys=None):
    """Resolve pose wording from the selected garment's own poses module."""
    if not pose:
        return None
    if garment_type:
        module_path = POSE_MODULES.get(garment_type)
        if module_path:
            module = import_module(module_path)
            getter = getattr(module, "get_pose_prompt", None)
            if getter:
                sentence = getter(pose, garment_style, detail_keys)
                if sentence:
                    return sentence
            saree_getter = getattr(module, "get_pose_parts", None)
            if saree_getter:
                parts = saree_getter(pose)
                if parts and parts.get("pose_text"):
                    return parts["pose_text"]
    return None
