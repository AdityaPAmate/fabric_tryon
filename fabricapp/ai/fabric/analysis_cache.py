"""Immutable-source analysis cache, owned by one catalog request only."""
from copy import deepcopy
from threading import RLock


class AnalysisCache:
    def __init__(self):
        self.values = {}
        self.lock = RLock()


def cached_analysis(source, key, compute):
    cache = getattr(source, '_catalog_analysis_cache', None)
    if cache is None:
        return compute()
    key = (source._catalog_source_key, key)
    with cache.lock:
        if key not in cache.values:
            cache.values[key] = compute()
        # Callers may augment palettes; never mutate another shot's cached value.
        return deepcopy(cache.values[key])
