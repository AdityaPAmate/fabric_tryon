"""OS-backed local lock: automatically released if the worker exits or crashes."""
from contextlib import contextmanager
from django.conf import settings
from django.core.management.base import CommandError


@contextmanager
def exclusive_worker():
    path = settings.MEDIA_ROOT / 'video_jobs' / '.worker.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            import os
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise CommandError('A video worker is already running on this shared media directory.')
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)
