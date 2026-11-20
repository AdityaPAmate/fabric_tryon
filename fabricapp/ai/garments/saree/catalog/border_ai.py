"""Saree-only AI border detail: genuine source evidence, never template ornament."""
import io

from fabricapp.ai.garments.saree.catalog.border_extraction import extract_band, render_from_source
from fabricapp.ai.garments.saree.catalog.product_details import _load


BORDER_PROMPT = (
    'Create ONE sharp macro product photograph of the actual saree LONG SIDE BORDER / SELVEDGE. '
    'Image 0 is a low-resolution placement guide made ONLY from the submitted border: '
    'keep its continuous diagonal band running from TOP LEFT to BOTTOM RIGHT. '
    'Image 1 is a close-up of that SAME real border and is the only textile design authority. '
    'Re-photograph the border with crisp, clearly resolved motif edges and natural woven texture. '
    'Preserve the exact source colours, motif shapes, stripe count, motif order and orientation. '
    'Keep one complete border width visible, with a small neutral light-grey studio area '
    'outside its finished edges. Show only this narrow long-side border, not the whole saree, '
    'the broad pallu end artwork; this is not the main body print or scattered body motifs. Do not add designs, flowers, '
    'stripes, metallic shine or embroidery absent from image 1. For plain cloth, show a '
    'plain finished edge; invent no ornamental border. Use even neutral white light, '
    'natural fabric thickness and subtle physical relief. No sunlight, colour cast, '
    'harsh shadow, blur, pasted cutout, person, mannequin, hands, text or collage. '
)


def build_border_config(data, seed):
    # No global body-colour conditioning: border colours can differ from the body.
    return {
        'prompt': BORDER_PROMPT, 'seed': seed, 'guidance': data.get('guidance', 7),
        'output_dimensions': (384, 512) if (data.get('options') or {}).get('draft_mode') else (800, 1056),
        'subject_input_max_side': 768, 'fabric_crop_box': None,
        'fabric_source_format': 'PNG', 'classified_recovery': True,
        'fabric_type': data.get('fabric_type', 'unspecified'),
        'fabric_region': 'border', 'fabric_region_selection': 'extracted_side_band_ai_edit',
        'prompt_version': 'saree-border-ai-detail-v1', 'safety_retry_count': 0,
    }


def prepare_edit_inputs(data, shot, source, garment_source):
    if shot.key != 'border':
        return source, garment_source
    image, _ = _load(data)
    strip, metadata = extract_band(image, data.get('options') or {})
    guide = render_from_source(image, strip, metadata, (532, 704))
    # Supply a local repeat at usable aspect. Sending a 35x609 strip through the
    # provider's 511px limit would shrink the border width to only 29 pixels.
    height = min(strip.height, max(1, strip.width * 4))
    top = (strip.height - height) // 2
    detail = strip.crop((0, top, strip.width, top + height))
    subject, fabric = io.BytesIO(), io.BytesIO()
    guide.save(subject, 'PNG'); detail.save(fabric, 'PNG')
    subject.seek(0); fabric.seek(0)
    return subject.getvalue(), fabric
