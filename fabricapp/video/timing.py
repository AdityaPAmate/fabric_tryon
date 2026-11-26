"""Per-stage elapsed time; JSON fields avoid a video schema migration."""
import time
from contextlib import contextmanager


@contextmanager
def measure(timing, stage):
    start = time.monotonic()
    try:
        yield
    finally:
        # Accumulate repeated operations within this attempt, excluding queue time.
        key = stage + '_seconds'
        timing[key] = round(timing.get(key, 0) + time.monotonic() - start, 3)
