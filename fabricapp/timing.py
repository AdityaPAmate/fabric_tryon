"""Log image-request timings without changing responses or generation settings."""

import json
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

logger = logging.getLogger("fabricapp")
_context = ContextVar("image_timing_context", default=None)


def set_timing_metadata(**fields):
    context = _context.get()
    if context is not None:
        context.update(fields)


@contextmanager
def timed_stage(stage, **fields):
    started = time.monotonic()
    outcome = "ok"
    try:
        yield fields
    except BaseException:
        outcome = "error"
        raise
    finally:
        record = dict(_context.get() or {"request_id": "unscoped"})
        record.update(fields)
        record.update(stage=stage, outcome=outcome,
                      duration_ms=round((time.monotonic() - started) * 1000))
        logger.info("Image timing: %s", json.dumps(record, sort_keys=True))


@contextmanager
def image_request_timing():
    token = _context.set({"request_id": uuid4().hex})
    try:
        with timed_stage("api_total"):
            yield
    finally:
        _context.reset(token)
