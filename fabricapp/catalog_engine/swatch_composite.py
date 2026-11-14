"""Apply a photographed swatch inside the cloth silhouette of a detail reference."""
import io

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from fabricapp.ai.providers.cloudflare_engine import GenerationResult
from fabricapp.ai.fabric.body_region import select_body_fabric_region


def render_swatch_shot(data, shot):
    with Image.open(shot.reference) as image, Image.open(shot.reference_mask) as mask:
        reference = image.convert('RGB')
        fabric_mask = mask.convert('L')
    if fabric_mask.size != reference.size:
        raise ValueError(f'Cloth mask does not match {shot.reference.name}')

    options = data.get('options', {})
    source = data['fabric_image']
    source.seek(0)
    with Image.open(source) as image:
        swatch = ImageOps.exif_transpose(image).convert('RGB')
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
    luminance = np.asarray(reference.convert('L').filter(ImageFilter.GaussianBlur(8)), dtype=np.float32)
    inside = np.asarray(fabric_mask) > 240
    midtone = max(1, float(np.median(luminance[inside])))
    shading = np.clip(luminance / midtone, .82 if shot.swatch_body_only else .76,
                      1.0 if shot.swatch_body_only else 1.06)
    cloth = Image.fromarray(np.clip(np.asarray(texture) * shading[:, :, None], 0, 255).astype(np.uint8))
    backdrop = reference
    if shot.composite_backdrop:
        with Image.open(shot.composite_backdrop) as image:
            backdrop = image.convert('RGB')
        if backdrop.size != reference.size:
            raise ValueError(f'Composite backdrop does not match {shot.reference.name}')
    result = Image.composite(cloth, backdrop, fabric_mask)
    if options.get('draft_mode'):
        result.thumbnail((768, 768), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    result.save(output, 'PNG')
    return GenerationResult(output.getvalue(), data.get('seed', 42), {
        'kind': 'swatch_composite', 'reference_mask': shot.reference_mask.name,
        'fabric_crop_box': crop, 'output_dimensions': list(result.size), 'no_new_ai_generation': True,
    })
