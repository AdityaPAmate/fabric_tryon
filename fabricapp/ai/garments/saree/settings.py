"""Default image-generation settings for saree requests."""

DEFAULT_SEED = 42
DEFAULT_GUIDANCE = 7.0


def get_generation_settings(*, seed=None, guidance=None):
    return {
        "seed": DEFAULT_SEED if seed is None else seed,
        "guidance": DEFAULT_GUIDANCE if guidance is None else guidance,
    }
