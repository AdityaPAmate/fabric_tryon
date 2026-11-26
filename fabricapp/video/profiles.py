"""Compatibility imports; definitions now live in video.garments."""
from collections.abc import Mapping
from .registry import GARMENT_MODULES, select_profile

GARMENTS = tuple(GARMENT_MODULES)
# Legacy health metadata only. Per-garment request validation and the UI use
# the registry, so this list cannot select a wrong garment profile.
MOTION_CHOICES = (('mirror_check', 'Current inspection'), ('walking', 'Walking / catwalk'),
                  ('shirt_commercial', 'Cinematic shirt commercial'))


class _Profiles(Mapping):
    def __getitem__(self, garment):
        return select_profile({'garment_type': garment})

    def __iter__(self):
        return iter(GARMENTS)

    def __len__(self):
        return len(GARMENTS)


PROFILES = _Profiles()
