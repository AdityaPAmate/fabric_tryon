"""Lossless catalog encoding; compression controls CPU/file size, never pixels."""
from django.conf import settings


def save_catalog_png(image, output):
    enabled = getattr(settings, 'CATALOG_PERFORMANCE_ENABLED', True)
    level = getattr(settings, 'CATALOG_PNG_COMPRESS_LEVEL', 3) if enabled else 6
    image.save(output, 'PNG', compress_level=max(0, min(9, int(level))), optimize=False)
