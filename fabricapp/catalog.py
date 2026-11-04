"""One streamed request, independent catalogue images, anchored on the front view."""
import io
import json
import logging
import queue
import threading
from uuid import uuid4

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageStat

from django.http import StreamingHttpResponse
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from fabricapp.ai.images.catalog_collage import compose_catalog, LAYOUT
from fabricapp.ai.images.shirt_collar import load_shirt_collar_mask, render_shirt_collar
from fabricapp.ai.images.shirt_hem import load_shirt_hem_mask, render_shirt_hem
from fabricapp.ai.images.shirt_sleeve import load_shirt_sleeve_mask, render_shirt_sleeve
from fabricapp.ai.main import generate_tryon_image
from fabricapp.ai.pipeline.catalog_prompts import catalog_plan, edit_config
from fabricapp.ai.references.catalog_reference import get_catalog_reference_path
from fabricapp.ai.providers.cloudflare_engine import generate_tryon_image as generate_edit, CloudflareGenerationError, GenerationResult
from fabricapp.serializers import FabricTryOnRequestSerializer
from fabricapp.services.cloudinary_service import upload_generated_image

logger = logging.getLogger('fabricapp')
# Bounded per web process; catalogue work must not occupy every request thread.
CATALOG_SLOTS = threading.BoundedSemaphore(1)


SHIRT_DETAILS = {
    'collar': (load_shirt_collar_mask, render_shirt_collar,
               'soft shadow directly beneath the collar points and along the inner collar roll'),
    'cuff': (load_shirt_sleeve_mask, render_shirt_sleeve,
             'soft shadow under the cuff overlap and along the existing sleeve fold'),
    'hem': (load_shirt_hem_mask, render_shirt_hem,
            'soft shadow along the existing turned hem and under the placket overlap'),
}


def generate_masked_shirt_detail(data, template, view, seed, swatch_bytes):
    load_mask, _, shadow = SHIRT_DETAILS[view]
    base, mask = load_mask(template)
    mask_png = io.BytesIO()
    mask.save(mask_png, format='PNG')
    config = {
        'prompt': (
            'Retexture the existing shirt in image 0, in place. Image 1 is the fabric swatch. '
            'Image 2 is the fabric mask: white means editable shirt, black means protected. '
            'Match the exact composition, crop, seams, folds and shirt silhouette of image 0. '
            'Keep all buttons, skin, trousers and background in their original positions. '
            'Within the white mask, apply the swatch at a realistic scale and follow the existing '
            'panel directions and folds. Match the swatch hue, saturation and print contrast. '
            f'Use soft neutral light and add a {shadow}. '
            'Keep the rest of the fabric gently lit, with a crisp pressed finish. '
            'Avoid dark outlines around the mask and new wrinkles. Output one photograph.'
        ),
        'seed': seed, 'guidance': data.get('guidance', 7),
        'prompt_version': 'catalog-masked-detail-v1', 'output_size_multiple': 32,
        'safety_retry_count': 0,
    }
    result = generate_edit(
        person_image=io.BytesIO(template.read_bytes()), fabric_image=data['fabric_image'],
        fabric_mask=mask_png.getvalue(), garment_type='shirt', scenario='person_photo',
        options=data.get('options', {}), prompt_config=config,
    )
    _, render_local, _ = SHIRT_DETAILS[view]
    local_image = render_local(template, swatch_bytes, data.get('options', {}).get('fabric_crop_box'))
    output = apply_masked_detail_lighting(local_image, result.image_bytes, base, mask)
    return GenerationResult(output, result.effective_seed,
                            {**(result.diagnostics or {}), 'method': 'ai_masked_detail',
                             'lighting': 'ai_soft_luminance_v1'})


def apply_masked_detail_lighting(local_image, ai_image, base, mask):
    """Use AI light and shade while keeping the original geometry and swatch."""
    with Image.open(io.BytesIO(ai_image)) as image:
        luminance = image.convert('L').resize(base.size, Image.Resampling.LANCZOS)
    luminance = luminance.filter(ImageFilter.GaussianBlur(24))
    midtone = ImageStat.Stat(luminance, mask=mask).median[0]
    gain = luminance.point(lambda value: round(255 * max(.80, min(1.06, 1 + (value - midtone) / 200)) / 1.06))
    # Taper the AI contribution near buttons, skin, and the shirt outline.
    interior = mask.filter(ImageFilter.GaussianBlur(20)).point(
        lambda value: max(0, min(255, (value - 160) * 4))
    )
    with Image.open(io.BytesIO(local_image)) as image:
        local = image.convert('RGB')
    lit = ImageChops.multiply(local, Image.merge('RGB', (gain, gain, gain)))
    lit = ImageEnhance.Brightness(lit).enhance(1.06)
    adjusted = Image.composite(lit, local, interior)
    output = io.BytesIO()
    Image.composite(adjusted, base, mask).save(output, format='PNG')
    return output.getvalue()


class CatalogRequestSerializer(FabricTryOnRequestSerializer):
    def validate(self, data):
        data = super().validate(data)
        if data.get('garment_image'):
            raise serializers.ValidationError({'fabric_image': 'Catalog requires a fabric swatch and garment_type.'})
        if data.get('pose') or data.get('camera_view'):
            raise serializers.ValidationError({'camera_view': 'Catalog selects its own views; omit camera_view and pose.'})
        data.setdefault('options', {}).setdefault('draft_mode', False)
        return data


def generate_catalog(data, stopped):
    """Yield progress. Successful images survive failures of other catalogue shots."""
    plan = catalog_plan(data['garment_type'])
    catalog_id = uuid4().hex
    yield {'event': 'started', 'catalog_id': catalog_id, 'total': len(plan), 'views': [key for key, _ in plan]}
    anchor = None
    anchor_seed = None
    images, failed = [], []
    shot_bytes = {}
    data["fabric_image"].seek(0)
    swatch_bytes = data["fabric_image"].read()
    data["fabric_image"].seek(0)
    blocked = False
    for index, (view, shot) in enumerate(plan):
        if stopped.is_set():
            return
        template = get_catalog_reference_path(data['garment_type'], view)
        local_renderer = None
        if template and data['garment_type'] == 'shirt':
            if view in SHIRT_DETAILS:
                local_renderer = SHIRT_DETAILS[view][1]
        camera_view = view if view in ('front', 'close_up') else None
        if (blocked and not local_renderer) or (not camera_view and anchor is None and template is None):
            failed.append(view)
            yield {'event': 'image_failed', 'view': view, 'error': 'generation_unavailable' if blocked else 'front_reference_failed'}
            continue
        yield {'event': 'generating', 'view': view, 'index': index + 1, 'total': len(plan)}
        try:
            for key in ('person_image', 'fabric_image', 'face_image'):
                if data.get(key):
                    data[key].seek(0)
            if camera_view:
                generation = generate_tryon_image(**data, camera_view=camera_view)
                if view == 'front':
                    # Keep the reference even if delivery upload fails.
                    anchor, anchor_seed = generation.image_bytes, generation.effective_seed
            elif local_renderer:
                generation = None
                fallback_reason = 'provider_unavailable'
                if not blocked:
                    try:
                        generation = generate_masked_shirt_detail(data, template, view, anchor_seed if anchor_seed is not None else data.get('seed', 42), swatch_bytes)
                    except CloudflareGenerationError as exc:
                        logger.warning('Masked shirt detail fell back to local rendering: %s', exc)
                        fallback_reason = exc.failure_type or 'provider_error'
                        blocked = exc.status_code in (401, 403, 429) or fallback_reason in ('allocation_exhausted', 'authentication_error')
                if generation is None:
                    generation = GenerationResult(
                        local_renderer(template, swatch_bytes, data.get('options', {}).get('fabric_crop_box')),
                        None, {'method': 'masked_swatch_composite', 'lighting': 'soft_contact_v1',
                               'fallback_reason': fallback_reason},
                    )
            else:
                generation = generate_edit(
                    person_image=io.BytesIO(template.read_bytes() if template else anchor), fabric_image=data['fabric_image'],
                    garment_type=data['garment_type'], garment_style=data.get('garment_style'),
                    scenario='person_pose' if view == 'three_quarter' else 'person_photo', options=data.get('options', {}),
                    prompt_config=edit_config(data, shot, anchor_seed if anchor_seed is not None else data.get('seed', 42),
                                             reference_template=template, view=view),
                )
            image = {'view': view, **upload_generated_image(generation.image_bytes),
                     'generation_seed': generation.effective_seed,
                     'generation': generation.diagnostics,
                     'framing': ('template_close_up' if template else
                                 'rear_close_up' if view == 'back' else
                                 'three_quarter_close_up' if view == 'three_quarter' else
                                 'full_body' if view == 'front' else 'detail_close_up'),
                     'reference_template': template.name if template else None}
            shot_bytes[view] = generation.image_bytes
            images.append(image)
            yield {'event': 'image_ready', 'image': image, 'completed': len(images), 'total': len(plan)}
        except Exception as exc:
            logger.exception('Catalog shot failed: %s', view)
            failed.append(view)
            failure = exc.failure_type if isinstance(exc, CloudflareGenerationError) else None
            blocked = blocked or failure in ('allocation_exhausted', 'authentication_error') or (
                isinstance(exc, CloudflareGenerationError) and exc.status_code in (401, 403, 429))
            yield {'event': 'image_failed', 'view': view, 'error': failure or 'image_generation_or_upload_failed',
                   'provider_code': getattr(exc, 'provider_code', None),
                   'generation': getattr(exc, 'diagnostics', None)}
    if stopped.is_set():
        return
    collage, collage_error = None, None
    if not failed:
        yield {'event': 'composing'}
        try:
            payload = compose_catalog(shot_bytes, swatch_bytes, [key for key, _ in plan])
            collage = {**upload_generated_image(payload), 'view': 'catalog', 'layout': LAYOUT,
                       'source_views': [key for key, _ in plan], 'includes_original_swatch': True}
            yield {'event': 'collage_ready', 'image': collage}
        except Exception:
            logger.exception('Catalog composition or upload failed')
            collage_error = 'collage_composition_or_upload_failed'
    else:
        collage_error = 'required_views_missing'
    yield {'event': 'complete', 'status': 'completed' if collage else ('partial' if images else 'failed'),
           'catalog_id': catalog_id, 'images': images, 'failed_views': failed, 'total': len(plan),
           'collage': collage, 'collage_error': collage_error}


def catalog_stream(data):
    """Heartbeats prevent an idle proxy while a single provider call is running.

    Closing the connection cancels remaining shots, not an in-flight provider call.
    The slot is released by the worker only after that call finishes.
    """
    events = queue.Queue()
    stopped = threading.Event()

    def run():
        try:
            for event in generate_catalog(data, stopped):
                events.put(event)
        except Exception:
            logger.exception('Catalog worker failed')
            events.put({'event': 'error', 'error': 'catalog_failed'})
        finally:
            events.put(None)
            CATALOG_SLOTS.release()

    worker = threading.Thread(target=run, daemon=True, name='catalog-generation')
    worker.start()
    def stream():
        try:
            while True:
                try:
                    event = events.get(timeout=10)
                except queue.Empty:
                    event = {'event': 'heartbeat'}
                if event is None:
                    break
                yield json.dumps(event) + '\n'
        finally:
            stopped.set()

    return stream(), stopped.set


class GenerateCatalogView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = CatalogRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not CATALOG_SLOTS.acquire(blocking=False):
            return Response({'error': 'Catalog generator is busy. Try again shortly.'}, status=429)
        data = dict(serializer.validated_data)
        # Django closes request upload files after the response; detached buffers
        # give the stream ownership without depending on request file lifetime.
        try:
            for key in ('person_image', 'fabric_image', 'face_image'):
                if data.get(key):
                    data[key].seek(0)
                    data[key] = io.BytesIO(data[key].read())
            stream, cancel = catalog_stream(data)
        except Exception:
            CATALOG_SLOTS.release()
            raise
        response = StreamingHttpResponse(stream, content_type='application/x-ndjson')
        response._resource_closers.append(cancel)
        response['Cache-Control'] = 'no-cache, no-store'
        response['X-Accel-Buffering'] = 'no'
        return response
