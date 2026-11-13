"""Select the garment's body print when an uploaded panel has distinct edge trim."""
from math import dist
from statistics import median

from PIL import Image, ImageChops, ImageStat


BAND_COUNT = 12


def _band_signature(band):
    width, height = band.size
    horizontal = ImageChops.difference(band.crop((0, 0, width - 1, height)), band.crop((1, 0, width, height)))
    vertical = ImageChops.difference(band.crop((0, 0, width, height - 1)), band.crop((0, 1, width, height)))
    detail = (sum(ImageStat.Stat(horizontal).mean) + sum(ImageStat.Stat(vertical).mean)) / 6
    return detail, ImageStat.Stat(band).mean


def _body_span(sample):
    """Trim consecutive edge bands that differ from a consistent interior region."""
    width, height = sample.size
    if min(width, height) < 36:
        return 0, height
    left, right = round(width * .33), round(width * .67)
    rows = [round(height * i / BAND_COUNT) for i in range(BAND_COUNT + 1)]
    bands = [_band_signature(sample.crop((left, top, right, bottom))) for top, bottom in zip(rows, rows[1:])]

    def interior_rank(start):
        details = [detail for detail, _ in bands[start:start + 3]]
        return median(details), abs(start + 1.5 - BAND_COUNT / 2)

    start = min(range(1, BAND_COUNT - 3), key=interior_rank)
    interior = bands[start:start + 3]
    body_detail = median(detail for detail, _ in interior)
    body_colour = tuple(median(colour[channel] for _, colour in interior) for channel in range(3))

    def looks_like_edge(band):
        detail, colour = band
        colour_gap = dist(colour, body_colour)
        return (detail - body_detail >= 8 and detail >= body_detail * 1.5
                or abs(detail - body_detail) >= 4 and colour_gap >= 38
                or colour_gap >= 55 and max(detail, body_detail) >= 4)

    first, last = 0, BAND_COUNT
    # A photo of laid-out fabric may show a strip of floor before the trim.
    if start >= 3 and not looks_like_edge(bands[0]) and all(map(looks_like_edge, bands[1:3])):
        first = 1
    if start + 3 <= BAND_COUNT - 3 and not looks_like_edge(bands[-1]) and all(map(looks_like_edge, bands[-3:-1])):
        last -= 1
    while first < start and looks_like_edge(bands[first]):
        first += 1
    while last > start + 3 and looks_like_edge(bands[last - 1]):
        last -= 1
    # Leave ambiguous uploads intact. A very small crop may lose the repeat.
    if last - first < 5:
        return 0, height
    # The band next to the detected edge can still straddle the trim boundary.
    inset = max(1, round(height / BAND_COUNT))
    return rows[first] + (inset if first else 0), rows[last] - (inset if last < BAND_COUNT else 0)


def select_body_fabric_region(data):
    selected = (data.get('options') or {}).get('fabric_crop_box')
    if selected is not None:
        return selected, 'explicit_crop'
    source = data.get('fabric_image')
    if source is None:
        return None, 'full_source'

    position = source.tell()
    try:
        source.seek(0)
        with Image.open(source) as fabric:
            width, height = fabric.size
            sample = fabric.convert('RGB')
    finally:
        source.seek(position)
    sample.thumbnail((192, 192))
    sw, sh = sample.size
    top, bottom = _body_span(sample)
    left, right = _body_span(sample.transpose(Image.Transpose.TRANSPOSE))
    # Remove the larger edge region first so it cannot bias the other axis.
    if (right - left) * sh < (bottom - top) * sw:
        top, bottom = _body_span(sample.crop((left, 0, right, sh)))
    else:
        band = sample.crop((0, top, sw, bottom)).transpose(Image.Transpose.TRANSPOSE)
        left, right = _body_span(band)
    if (left, top, right, bottom) == (0, 0, sw, sh):
        return None, 'full_source'
    if left > 0 and right < sw and (top > 0 or bottom < sh):
        # Side borders on photographed panels can slant inwards outside the sampled band.
        margin = round((right - left) / 7)
        left += margin
        right -= margin
    crop = [round(left * width / sw), round(top * height / sh),
            round(right * width / sw), round(bottom * height / sh)]
    return crop, 'detected_body_crop'
