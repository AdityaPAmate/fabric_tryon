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

from fabricapp.ai.main import generate_tryon_image
from fabricapp.ai.pipeline.catalog_prompts import catalog_plan, edit_config
from fabricapp.ai.providers.cloudflare_engine import generate_tryon_image as generate_edit
from fabricapp.catalog_engine.registry import STYLE_EDITIONS, get_request_definition
from fabricapp.serializers import FabricTryOnRequestSerializer
from fabricapp.services.cloudinary_service import upload_generated_image

logger = logging.getLogger('fabricapp')
# Bounded per web process; catalogue work must not occupy every request thread.
CATALOG_SLOTS = threading.BoundedSemaphore(1)


class CatalogRequestSerializer(FabricTryOnRequestSerializer):
    catalog_edition = serializers.CharField(required=False, max_length=64)
    catalog_product = serializers.JSONField(required=False, default=dict)
    garment_as_swatch = serializers.BooleanField(required=False)

    DETAIL_CROPS = ('fabric_body_crop_box', 'fabric_border_crop_box')

    def _check_garment_source(self, data):
        if not data.get('garment_image'):
            return super()._check_garment_source(data)
        # In a catalog these fields select a template. The finished garment
        # still goes through the ordinary ready-made source validation.
        super()._check_garment_source({key: value for key, value in data.items()
                                     if key not in ('garment_type', 'garment_style')})
        if data.get('garment_style') and not data.get('garment_type'):
            raise serializers.ValidationError({'garment_type': 'Choose a garment type with garment_style.'})

    def validate_options(self, value):
        if not isinstance(value, dict):
            return super().validate_options(value)
        details = {key: value[key] for key in self.DETAIL_CROPS if key in value}
        validated = super().validate_options({key: val for key, val in value.items() if key not in details})
        for key, box in details.items():
            # Reuse the existing pixel-coordinate contract, including bool rejection.
            try:
                super().validate_options({'fabric_crop_box': box})
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({key: exc.detail})
        return {**validated, **details}

    def validate_catalog_product(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('Provide an object containing catalog product fields.')
        if any(not isinstance(text, str) or len(text) > 100 or any(ord(c) < 32 for c in text)
               for text in value.values()):
            raise serializers.ValidationError('Product values must be single-line strings of at most 100 characters.')
        return {key: text.strip() for key, text in value.items()}

    def validate(self, data):
        if data.pop('garment_as_swatch', False):
            edition = STYLE_EDITIONS.get((data.get('garment_type'), data.get('garment_style')))
            if (data.get('garment_image') is None or data.get('fabric_image') is not None or
                    data.get('garment_type') != 'kurta' or not edition):
                raise serializers.ValidationError({'garment_as_swatch': 'Choose a ready garment photo and a supported Kurta catalog style.'})
            if data.get('catalog_edition') not in (None, edition):
                raise serializers.ValidationError({'catalog_edition': f'Garment fabric extraction requires {edition}.'})
            from PIL import Image, ImageOps

            source = data.pop('garment_image')
            source.seek(0)
            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened).convert('RGB')
            options = data.setdefault('options', {})
            box = options.pop('fabric_crop_box', None)
            if box is None:
                # Below the placket, inside the central panel of a front-on kurta photo.
                box = [round(image.width * .34), round(image.height * .53),
                       round(image.width * .66), round(image.height * .82)]
            if box[2] > image.width or box[3] > image.height or box[2] <= box[0] or box[3] <= box[1]:
                raise serializers.ValidationError({'options': {'fabric_crop_box': 'Choose a crop inside the garment photo.'}})
            fabric = io.BytesIO()
            image.crop(box).save(fabric, 'PNG')
            fabric.seek(0)
            data['fabric_image'] = fabric
            data['catalog_edition'] = edition
        data = super().validate(data)
        crops = {key: data.get('options', {})[key] for key in self.DETAIL_CROPS if key in data.get('options', {})}
        if crops:
            if data.get('garment_type') != 'saree' or not data.get('fabric_image'):
                raise serializers.ValidationError({'options': 'Detail crops require a saree catalog fabric_image.'})
            from PIL import Image
            source = data['fabric_image']
            position = source.tell()
            try:
                source.seek(0)
                with Image.open(io.BytesIO(source.read())) as image:
                    width, height = image.size
            finally:
                source.seek(position)
            for key, box in crops.items():
                if box[2] > width or box[3] > height:
                    raise serializers.ValidationError({'options': {key: 'Crop must be inside the original fabric image.'}})
        if data.get('pose') or data.get('camera_view'):
            raise serializers.ValidationError({'camera_view': 'Catalog selects its own views; omit camera_view and pose.'})
        try:
            definition = get_request_definition(data)
        except ValueError as exc:
            raise serializers.ValidationError({'catalog_edition': str(exc)})
        unknown = set(data.get('catalog_product', {})) - set(definition.product_fields)
        if unknown:
            raise serializers.ValidationError({'catalog_product': 'Unsupported product fields: ' + ', '.join(sorted(unknown))})
        if definition.validate_request:
            errors = definition.validate_request(data)
            if errors:
                raise serializers.ValidationError(errors)
        data['catalog_edition'] = definition.edition
        data.setdefault('options', {}).setdefault('draft_mode', False)
        return data


def generate_catalog(data, stopped):
    """Compatibility entry point; providers remain replaceable in API tests."""
    from fabricapp.catalog_engine.runner import generate_catalog as run, Services
    yield from run(data, stopped, Services(generate_tryon_image, generate_edit, upload_generated_image))


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
        from fabricapp.catalog_engine.validation import validate_definition
        try:
            validate_definition(get_request_definition(serializer.validated_data),
                                serializer.validated_data.get('catalog_product'))
        except ValueError:
            logger.exception('Invalid catalog definition')
            return Response({'error': 'Catalog configuration is unavailable.'}, status=503)
        if not CATALOG_SLOTS.acquire(blocking=False):
            return Response({'error': 'Catalog generator is busy. Try again shortly.'}, status=429)
        data = dict(serializer.validated_data)
        # Django closes request upload files after the response; detached buffers
        # give the stream ownership without depending on request file lifetime.
        try:
            for key in ('person_image', 'fabric_image', 'garment_image', 'face_image'):
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
