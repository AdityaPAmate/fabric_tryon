"""Apply a photographed swatch inside the cloth silhouette of a detail reference."""
import io

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.ai.fabric.body_region import select_body_fabric_region
from fabricapp.ai.images.catalog_encoding import save_catalog_png
from fabricapp.catalog_engine.composite_assets import reference_maps


def render_swatch_shot(data, shot, target_rgb=None):
    maps = reference_maps(shot)
    reference, fabric_mask = maps['reference'], maps['mask']

    options = data.get('options', {})
    source = data['fabric_image']
    source.seek(0)
    with Image.open(source) as image:
        # Some definitions share raw crop coordinates with provider input and palette measurement.
        swatch = (image if shot.swatch_original_orientation else ImageOps.exif_transpose(image)).convert('RGB')
    crop = (select_body_fabric_region(data)[0] if shot.swatch_body_only else options.get('fabric_crop_box'))
    if crop:
        left, top, right, bottom = crop
        right, bottom = min(right, swatch.width), min(bottom, swatch.height)
        if right <= left or bottom <= top:
            raise ValueError('Fabric crop is outside the swatch.')
        swatch = swatch.crop((left, top, right, bottom))

    # Keep a source hem border at the bottom when fitting a tall fabric photo.
    texture = ImageOps.fit(swatch, reference.size, Image.Resampling.LANCZOS, centering=(.5, 1))
    # Transfer only broad, neutral fold shading. The reference's original
    # colour and embroidery never enter the swatch pixels.
    luminance, inside, midtone = maps['luminance'], maps['inside'], maps['midtone']
    shading = np.clip(luminance / midtone, .82 if shot.swatch_body_only else .76,
                      1.0 if shot.swatch_body_only else 1.06)
    pixels = np.asarray(texture, dtype=np.float32)
    if shot.natural_swatch_shading:
        # Remove broad exposure bands in the source, preserving weave and print.
        swatch_light = np.asarray(texture.convert('L').filter(
            ImageFilter.GaussianBlur(reference.width / 15)), dtype=np.float32)
        cloth_midtone = max(1, float(np.median(swatch_light[inside])))
        pixels *= np.clip(cloth_midtone / np.maximum(swatch_light, 1), .65, 1.20)[:, :, None]
        if target_rgb is not None:
            texture_rgb = np.maximum(np.median(pixels[inside], axis=0), 1)
            pixels *= np.clip(target_rgb / texture_rgb, .75, 1.25)
        shading = np.clip(luminance / midtone, .60, 1.10)
    if shot.composite_relief:
        # A neutral map carries construction shadows and highlights independently
        # of the reference textile's colour. Its alpha marks a separate welt
        # whose cut of the same cloth has a different pattern alignment.
        shading *= maps['relief']
        welt = maps['welt']
        offset = max(1, reference.width // 24)
        shifted = np.pad(pixels, ((0, 0), (0, offset), (0, 0)), mode='edge')[:, offset:]
        pixels = pixels * (1 - welt) + shifted * welt
    cloth = Image.fromarray(np.clip(pixels * shading[:, :, None], 0, 255).astype(np.uint8))
    backdrop = reference
    if shot.composite_backdrop:
        with Image.open(shot.composite_backdrop) as image:
            backdrop = image.convert('RGB')
        if backdrop.size != reference.size:
            raise ValueError(f'Composite backdrop does not match {shot.reference.name}')
    if shot.natural_swatch_shading and not shot.composite_relief:
        # Keep a soft contact shadow just beyond the cloth boundary.
        alpha = np.asarray(fabric_mask.filter(
            ImageFilter.GaussianBlur(reference.width / 90)), dtype=np.float32)
        backdrop = Image.fromarray(np.uint8(np.asarray(backdrop) * (1 - .25 * alpha[:, :, None] / 255)))
    result = Image.composite(cloth, backdrop, fabric_mask)
    if options.get('draft_mode'):
        result.thumbnail((768, 768), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    save_catalog_png(result, output)
    diagnostics = {
        'kind': 'swatch_composite', 'reference_mask': shot.reference_mask.name,
        'fabric_crop_box': crop, 'output_dimensions': list(result.size), 'no_new_ai_generation': True,
    }
    if shot.natural_swatch_shading and target_rgb is not None:
        diagnostics['solid_fabric_target_rgb'] = np.rint(target_rgb).astype(int).tolist()
    return GenerationResult(output.getvalue(), data.get('seed', 42), diagnostics)
