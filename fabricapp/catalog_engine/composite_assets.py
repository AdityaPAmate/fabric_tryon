"""Byte-bounded cache of static reference maps, never uploaded product images."""
from collections import OrderedDict
from threading import RLock

import numpy as np
from django.conf import settings
from PIL import Image, ImageFilter

_cache = OrderedDict()
_lock = RLock()
_bytes = 0
MAX_BYTES = 32 * 1024 * 1024


def _load(shot):
    with Image.open(shot.reference) as image, Image.open(shot.reference_mask) as mask:
        reference, fabric_mask = image.convert('RGB'), mask.convert('L')
    if fabric_mask.size != reference.size:
        raise ValueError(f'Cloth mask does not match {shot.reference.name}')
    light = np.asarray(reference.convert('L').filter(ImageFilter.GaussianBlur(8)), dtype=np.float32)
    inside = np.asarray(fabric_mask) > 240
    result = {'reference': reference, 'mask': fabric_mask, 'luminance': light,
              'inside': inside, 'midtone': max(1, float(np.median(light[inside])))}
    if shot.composite_relief:
        with Image.open(shot.composite_relief) as image:
            if image.size != reference.size:
                raise ValueError(f'Composite relief does not match {shot.reference.name}')
            result['relief'] = np.asarray(image.convert('L'), dtype=np.float32) / 128
            result['welt'] = np.asarray(image.getchannel('A'), dtype=np.float32)[:, :, None] / 255
    for value in result.values():
        if isinstance(value, np.ndarray):
            value.setflags(write=False)
    return result


def reference_maps(shot):
    global _bytes
    if not getattr(settings, 'CATALOG_PERFORMANCE_ENABLED', True):
        return _load(shot)
    paths = (shot.reference, shot.reference_mask, shot.composite_relief)
    key = tuple((str(p.resolve()), p.stat().st_mtime_ns, p.stat().st_size) if p else None for p in paths)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key][0]
        value = _load(shot)
        size = sum(v.nbytes if isinstance(v, np.ndarray) else
                   v.width*v.height*len(v.getbands()) if isinstance(v, Image.Image) else 0
                   for v in value.values())
        if size <= MAX_BYTES:
            while _cache and _bytes + size > MAX_BYTES:
                _, (_, removed) = _cache.popitem(last=False)
                _bytes -= removed
            _cache[key] = (value, size)
            _bytes += size
        return value
