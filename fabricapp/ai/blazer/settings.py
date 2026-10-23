"""Default image-generation settings for this garment type."""

DEFAULT_SEED = 24
DEFAULT_GUIDANCE = 7.0


def get_generation_settings(*, seed=None, guidance=None):
    """Return the defaults unless request values are provided."""
    return {
        "seed": DEFAULT_SEED if seed is None else seed,
        "guidance": DEFAULT_GUIDANCE if guidance is None else guidance,
    }