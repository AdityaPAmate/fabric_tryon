"""Reuse fixed product photography and optionally replace only its background."""
import io

from PIL import Image, ImageOps

from fabricapp.ai.images.image_utils import make_blank_canvas
from fabricapp.ai.providers.cloudflare_engine import GenerationResult


def render_reference_shot(data, shot, definition, services):
    source = shot.reference.read_bytes()
    seed = data.get('seed', 42)
    if not data.get('background') or not shot.reference_mask:
        return GenerationResult(source, seed, {'kind': 'original_reference', 'no_new_ai_generation': True})

    with Image.open(io.BytesIO(source)) as original, Image.open(shot.reference_mask) as mask:
        if mask.size != original.size:
            raise ValueError(f'Reference mask does not match {shot.reference.name}')
        # Only the background is generated. The source garment and user's fabric never enter this request.
        plate = services.edit(
            fabric_image=make_blank_canvas(256, 256), garment_type=data['garment_type'],
            scenario='generated_person', options={'draft_mode': data.get('options', {}).get('draft_mode', False)},
            prompt_config=definition.build_config(data, shot, seed),
        )
        with Image.open(io.BytesIO(plate.image_bytes)) as backdrop:
            backdrop = ImageOps.fit(backdrop.convert('RGB'), original.size, method=Image.Resampling.LANCZOS)
        composite = Image.composite(original.convert('RGB'), backdrop, mask.convert('L'))
    output = io.BytesIO()
    composite.save(output, 'PNG')
    return GenerationResult(output.getvalue(), plate.effective_seed, {
        **(plate.diagnostics or {}), 'kind': 'background_composite',
    })
