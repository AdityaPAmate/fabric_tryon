"""Apply a solid source colour to the tie while keeping its knot and folds."""
from dataclasses import replace
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import (
    binary_dilation, binary_fill_holes, binary_propagation, distance_transform_edt, gaussian_filter, label,
)


TROUSER_REGIONS = {
    'front': ((.38, .58, .62, .67),
              ((.22, .54), (.78, .54), (.81, .69), (.77, .94), (.55, .94), (.50, .65),
               (.44, .94), (.23, .94), (.19, .69))),
    'side': ((.45, .59, .59, .68),
             ((.35, .54), (.67, .54), (.70, .68), (.72, .86), (.70, .94), (.55, .94),
              (.50, .91), (.43, .91), (.37, .77), (.34, .66))),
    'back': ((.38, .57, .63, .65),
             ((.23, .52), (.77, .52), (.81, .68), (.77, .94), (.55, .95), (.50, .67),
              (.44, .95), (.23, .94), (.19, .68))),
}
SHIRT_OPENINGS = {
    'front': ((.38, .195), (.61, .195), (.59, .26), (.53, .38), (.47, .38), (.40, .265)),
    'side': ((.36, .225), (.48, .195), (.51, .216), (.455, .258), (.397, .299),
             (.366, .345), (.342, .34)),
}


def neutralize_dress_shirt(generation, view, target):
    if view not in SHIRT_OPENINGS or target is None:
        return generation
    target = np.asarray(target, dtype=np.float32)
    if target.mean() > 222 and np.ptp(target) < 16:
        return generation
    with Image.open(BytesIO(generation.image_bytes)) as source:
        image = source.convert('RGB')
    width, height = image.size
    bounds = Image.new('1', image.size)
    ImageDraw.Draw(bounds).polygon([(round(x * width), round(y * height))
                                   for x, y in SHIRT_OPENINGS[view]], fill=1)
    pixels = np.asarray(image, dtype=np.float32)
    light = pixels.mean(axis=2)
    chroma = pixels - light[:, :, None]
    dist_from_jacket = np.linalg.norm(chroma - (target - target.mean()), axis=2)
    candidate = np.asarray(bounds) & (light > 148) & (np.ptp(pixels, axis=2) < 33)
    candidate &= (dist_from_jacket > 12) | (light > target.mean() + 26)
    seeds = candidate & (light > 214) & (np.ptp(pixels, axis=2) < 23)
    shirt = binary_propagation(seeds, mask=candidate)
    if not shirt.any():
        return generation

    # Lift broad shadows on the white cotton and keep folds, seams and the
    # exact tie boundary. Only pixels connected to a bright shirt seed qualify.
    sigma = max(2, width / 70)
    support = np.maximum(gaussian_filter(shirt.astype(np.float32), sigma), .001)
    local = gaussian_filter(pixels * shirt[:, :, None], (sigma, sigma, 0)) / support[:, :, None]
    shift = np.clip((242 - local) * .70, -8, 56)
    weight = np.clip(distance_transform_edt(shirt) / max(2, width / 165), 0, 1)
    corrected = np.rint(np.clip(pixels + shift * weight[:, :, None], 0, 255)).astype(np.uint8)
    output = BytesIO()
    Image.fromarray(corrected).save(output, 'PNG')
    return replace(generation, image_bytes=output.getvalue(), diagnostics={
        **(generation.diagnostics or {}), 'business_shirt_neutralized': True,
    })


def clean_trouser_motifs(generation, view, target):
    if target is None:
        return generation
    with Image.open(BytesIO(generation.image_bytes)) as source:
        image = source.convert('RGB')
    pixels = np.asarray(image, dtype=np.float32)
    width, height = image.size
    sample, outline = TROUSER_REGIONS[view]
    area = Image.new('1', image.size)
    ImageDraw.Draw(area).polygon([(round(x * width), round(y * height)) for x, y in outline], fill=1)
    left, top, right, bottom = (round(value * extent) for value, extent in zip(sample, (width, height) * 2))
    chroma = pixels - pixels.mean(axis=2, keepdims=True)
    observed = np.median(chroma[top:bottom, left:right], axis=(0, 1))
    search_area = binary_dilation(np.asarray(area), iterations=max(1, round(width * .07)))
    search_area[:round(height * .56)] = False
    search_area[round(height * .94):] = False
    plain = search_area & (np.linalg.norm(chroma - observed, axis=2) < 20)
    seeds = np.zeros_like(plain)
    seeds[top:bottom, left:right] = plain[top:bottom, left:right]
    cloth = binary_propagation(seeds, mask=plain)
    # Fill small discrepancies surrounded by the same cloth. Open gaps at the
    # silhouette, vents and spaces between the legs remain outside this mask.
    holes = binary_fill_holes(cloth) & ~cloth
    parts, _ = label(holes)
    counts = np.bincount(parts.ravel())
    defects = (parts > 0) & (counts[parts] <= width * height * .002)
    if not defects.any():
        return generation
    sigma = max(2, width / 55)
    support = gaussian_filter(cloth.astype(np.float32), sigma)
    local = gaussian_filter(pixels * cloth[:, :, None], (sigma, sigma, 0))
    local /= np.maximum(support[:, :, None], .001)
    replace_region = defects & (support > .10)
    corrected = pixels.copy()
    corrected[replace_region] = local[replace_region]
    output = BytesIO()
    Image.fromarray(np.rint(corrected).astype(np.uint8)).save(output, 'PNG')
    return replace(generation, image_bytes=output.getvalue())


def colour_lapel_tie(generation, mask_path, target):
    if target is None:
        return generation
    with Image.open(BytesIO(generation.image_bytes)) as source, Image.open(mask_path) as mask:
        image = source.convert('RGB')
        matte = mask.convert('L').resize(image.size, Image.Resampling.LANCZOS)
    return _colour_tie(generation, image, matte, target)


def colour_portrait_tie(generation, view, target):
    if target is None or view == 'back':
        return generation
    with Image.open(BytesIO(generation.image_bytes)) as source:
        image = source.convert('RGB')
    rgb = np.asarray(image, dtype=np.float32)
    width, height = image.size
    bounds = (.438, .19, .562, .365) if view == 'front' else (.29, .19, .50, .34)
    left, top, right, bottom = (round(value * extent) for value, extent in zip(bounds, (width, height) * 2))
    patch = rgb[top:bottom, left:right]
    if not patch.size:
        return generation
    # The fallback navy tie is distinct from the white shirt and the cloth.
    navy = (patch[:, :, 2] - patch[:, :, 0] > 10) & (patch.max(axis=2) < 135)
    if view == 'side':
        # The visible blade slopes toward the front edge of the side view.
        x = np.arange(left, right) / width
        y = np.arange(top, bottom)[:, None] / height
        navy &= np.abs(x - (.438 - (y - .22) * .58)) < .044
    seeds = np.zeros_like(navy)
    knot_height = round((.32 if view == 'front' else .55) * len(patch))
    seeds[:knot_height] = navy[:knot_height]
    connected = binary_propagation(seeds, mask=navy)
    if connected.mean() < (.10 if view == 'front' else .005):
        return generation
    matte = Image.new('L', image.size)
    matte.paste(Image.fromarray(connected.astype(np.uint8) * 255), (left, top))
    return _colour_tie(generation, image, matte.filter(ImageFilter.GaussianBlur(1.4)), target)


def _colour_tie(generation, image, matte, target):
    target = np.asarray(target, dtype=np.float32)
    inside = np.asarray(matte) > 240
    if not inside.any():
        return generation
    # Read real lighting at the knot and blade but suppress the original weave pattern.
    light = np.asarray(image.convert('L').filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    midpoint = np.median(light[inside])
    shade = np.clip(1 + (light - midpoint) / 145, .72, 1.16)
    solid = Image.fromarray(np.rint(np.clip(target * shade[:, :, None], 0, 255)).astype(np.uint8))
    output = BytesIO()
    Image.composite(solid, image, matte).save(output, 'PNG')
    return replace(generation, image_bytes=output.getvalue(), diagnostics={
        **(generation.diagnostics or {}), 'business_tie_rgb': np.rint(target).astype(int).tolist(),
    })
