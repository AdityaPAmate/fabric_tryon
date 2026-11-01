"""One streamed request, independent catalogue images, anchored on the front view."""
import io
import json
import logging
import queue
import threading

from django.http import StreamingHttpResponse
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai.main import generate_tryon_image
from .ai.cloudflare_engine import generate_tryon_image as generate_edit, CloudflareGenerationError
from .ai.fabric_colour import measure_fabric_colours, has_single_colour_family, colour_reference_prompt
from .ai.fabric_material import material_prompt, fabric_target
from .serializers import FabricTryOnRequestSerializer
from .services.cloudinary_service import upload_generated_image

logger = logging.getLogger('fabricapp')
# Bounded per web process; catalogue work must not occupy every request thread.
CATALOG_SLOTS = threading.BoundedSemaphore(1)
DETAILS = {
    'shirt': [('collar', 'collar and neckline'), ('cuff', 'sleeve cuff'), ('hem', 'lower shirt hem')],
    'blazer': [('lapel', 'lapel and collar'), ('cuff', 'sleeve cuff'), ('hem', 'lower jacket hem')],
    'kurta': [('neckline', 'neckline'), ('cuff', 'sleeve end'), ('hem', 'lower garment hem')],
    'kurti_pant': [('neckline', 'kurti neckline'), ('sleeve', 'kurti sleeve end'), ('hem', 'lower kurti hem')],
    'pant': [('waistband', 'trouser waistband'), ('pocket', 'trouser side pocket'), ('hem', 'trouser ankle hem')],
    'saree': [('pallu', 'pallu'), ('border', 'saree border'), ('pleats', 'saree pleats')],
}


class CatalogRequestSerializer(FabricTryOnRequestSerializer):
    def validate(self, data):
        data = super().validate(data)
        if data.get('garment_image'):
            raise serializers.ValidationError({'fabric_image': 'Catalog requires a fabric swatch and garment_type.'})
        if data.get('pose') or data.get('camera_view'):
            raise serializers.ValidationError({'camera_view': 'Catalog selects its own views; omit camera_view and pose.'})
        data.setdefault('options', {}).setdefault('draft_mode', False)
        return data


def catalog_plan(garment):
    details = [(key, f'tight product detail photograph of the {part} only; fill the frame with this area, not the full person')
               for key, part in DETAILS[garment]]
    if garment == 'shirt':
        details = [
            ('collar', 'extreme close-up of the shirt collar, collar points and top two buttons; '
             'frame from below the chin to the upper chest only; exclude the face, eyes, hair, waist and arms'),
            ('cuff', 'extreme close-up of one existing shirt sleeve cuff and its seam, '
             'with only a small adjoining area of sleeve and arm; exclude face and full torso'),
            ('hem', 'extreme close-up of the lower shirt hem, curved edge and hem stitching, '
             'with only a small adjoining section of shirt fabric and trousers; exclude face and chest'),
        ]
    return [('front', 'front full-body view'),
            ('three_quarter', 'three-quarter full-body view, turned approximately 45 degrees; '
             'both the front button line and one side seam must be visible, not a 90-degree side profile'),
            ('back', 'back full-body view, facing away from the camera')] + details


def edit_config(data, shot, anchor_seed):
    target = fabric_target(data['garment_type'], data.get('garment_style'), data.get('garment_details'))
    profile = measure_fabric_colours(data['fabric_image'], data.get('options', {}).get('fabric_crop_box'))
    colour = colour_reference_prompt(profile, target) if has_single_colour_family(profile) else ''
    prompt = (
        f'Create exactly ONE photograph: {shot}. Image 0 is the approved front photograph of this catalogue. '
        'Show the SAME person wearing the SAME finished outfit, with the same fit, seams, buttons, '
        'colours, fabric pattern size, material and background. Change only camera angle or framing as requested. '
        f'The garment being catalogued is {target}. Image 1 is its original fabric swatch: '
        'preserve its colours, texture and motifs; do not replace the outfit or invent a different garment. '
        'Preserve the separate garments from image 0. Maintain neutral light and realistic fold shading. '
        'For a rear view show the rear construction of this same garment; do not show a front-facing chest. '
        'For a detail view crop the requested area and retain its construction; do not add a collar, cuff or pocket '
        'if the original garment does not have one. No collage, panels, swatch inset, text or watermark. '
        + colour + material_prompt(data.get('fabric_type', 'unspecified'), data['garment_type'],
                                  data.get('garment_style'), data.get('garment_details'))
    )
    return {'prompt': prompt, 'seed': anchor_seed, 'guidance': data.get('guidance', 7),
            'prompt_version': 'catalog-edit-v1', 'safety_retry_count': 0}


def generate_catalog(data, stopped):
    """Yield progress. Successful images survive failures of other catalogue shots."""
    plan = catalog_plan(data['garment_type'])
    yield {'event': 'started', 'total': len(plan), 'views': [key for key, _ in plan]}
    anchor = None
    anchor_seed = None
    images, failed = [], []
    blocked = False
    for index, (view, shot) in enumerate(plan):
        if stopped.is_set():
            return
        if blocked or (view != 'front' and anchor is None):
            failed.append(view)
            yield {'event': 'image_failed', 'view': view, 'error': 'generation_unavailable' if blocked else 'front_reference_failed'}
            continue
        yield {'event': 'generating', 'view': view, 'index': index + 1, 'total': len(plan)}
        try:
            for key in ('person_image', 'fabric_image', 'face_image'):
                if data.get(key):
                    data[key].seek(0)
            if view == 'front':
                generation = generate_tryon_image(**data, camera_view='front')
                # Keep the reference even if delivery upload fails.
                anchor, anchor_seed = generation.image_bytes, generation.effective_seed
            else:
                generation = generate_edit(
                    person_image=io.BytesIO(anchor), fabric_image=data['fabric_image'],
                    garment_type=data['garment_type'], garment_style=data.get('garment_style'),
                    scenario='person_photo', options=data.get('options', {}),
                    prompt_config=edit_config(data, shot, anchor_seed),
                )
            image = {'view': view, **upload_generated_image(generation.image_bytes)}
            images.append(image)
            yield {'event': 'image_ready', 'image': image, 'completed': len(images), 'total': len(plan)}
        except Exception as exc:
            logger.exception('Catalog shot failed: %s', view)
            failed.append(view)
            failure = exc.failure_type if isinstance(exc, CloudflareGenerationError) else None
            blocked = failure in ('allocation_exhausted', 'authentication_error') or (
                isinstance(exc, CloudflareGenerationError) and exc.status_code in (401, 403, 429))
            yield {'event': 'image_failed', 'view': view, 'error': failure or 'image_generation_or_upload_failed'}
    yield {'event': 'complete', 'status': 'completed' if not failed else ('partial' if images else 'failed'),
           'images': images, 'failed_views': failed, 'total': len(plan)}


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
