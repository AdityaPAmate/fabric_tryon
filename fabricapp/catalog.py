"""One streamed request, independent catalogue images, anchored on the front view."""
import io
import json
import logging
import queue
import threading
from uuid import uuid4

from django.http import StreamingHttpResponse
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from fabricapp.ai.images.catalog_collage import compose_catalog, LAYOUT
from fabricapp.ai.main import generate_tryon_image
from fabricapp.ai.pipeline.catalog_prompts import catalog_plan, edit_config
from fabricapp.ai.references.catalog_reference import get_catalog_reference_path
from fabricapp.ai.providers.cloudflare_engine import generate_tryon_image as generate_edit, CloudflareGenerationError
from fabricapp.serializers import FabricTryOnRequestSerializer
from fabricapp.services.cloudinary_service import upload_generated_image

logger = logging.getLogger('fabricapp')
# Bounded per web process; catalogue work must not occupy every request thread.
CATALOG_SLOTS = threading.BoundedSemaphore(1)


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
        camera_view = view if view in ('front', 'close_up') else None
        if blocked or (not camera_view and anchor is None and template is None):
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
                                 'head_to_hip' if view == 'close_up' else
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
