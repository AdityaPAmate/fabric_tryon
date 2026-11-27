import time
from django.conf import settings
from django.http import Http404
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from fabricapp.models import VideoJob
from .serializers import VideoRequestSerializer, AnimateImageSerializer
from .service import create_job, job_response, can_retry
from .registry import get_definition, DefinitionUnavailable


MAX_WAIT_SECONDS = 1800


def video_response(job, wait):
    """Wait only for the existing worker; never generate or submit a second job."""
    if wait:
        deadline = time.monotonic() + MAX_WAIT_SECONDS
        while job.status not in ('completed', 'failed'):
            job.refresh_from_db()
            if job.status in ('completed', 'failed') or time.monotonic() >= deadline:
                break
            time.sleep(1)
    code = status.HTTP_200_OK if job.status in ('completed', 'failed') else status.HTTP_202_ACCEPTED
    return Response(job_response(job), status=code)


class VideoNotConfigured(APIException):
    status_code = 503
    default_detail = 'Video API is not configured. Set GIMMECLIP_API_KEY on the backend.'


class VideoView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


class VideoOptionsView(APIView):
    """Public metadata only: no generation, provider calls or API key needed."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            definition = get_definition(request.query_params.get('garment_type'))
        except DefinitionUnavailable as exc:
            return Response({'detail': str(exc)}, status=503)
        except ValueError as exc:
            return Response({'garment_type': str(exc)}, status=400)
        return Response(definition.options())


class GenerateTryOnVideoView(VideoView):
    serializer_class = VideoRequestSerializer
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not settings.GIMMECLIP_API_KEY:
            raise VideoNotConfigured()
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        wait = serializer.validated_data.pop('wait')
        job = create_job(serializer.validated_data)
        return video_response(job, wait)


class AnimateImageView(GenerateTryOnVideoView):
    serializer_class = AnimateImageSerializer


class VideoJobView(VideoView):
    def get_job(self, job_id):
        try:
            return VideoJob.objects.get(pk=job_id)
        except VideoJob.DoesNotExist:
            raise Http404

    def get(self, request, job_id):
        return Response(job_response(self.get_job(job_id)))


class RetryVideoJobView(VideoJobView):
    def post(self, request, job_id):
        wait = serializers.BooleanField().run_validation(request.data.get('wait', True))
        job = self.get_job(job_id)
        if not can_retry(job):
            return Response({'detail': 'Only retryable failed jobs can be queued again.'}, status=409)
        # Atomic compare-and-set prevents two retry requests from queuing it twice.
        updated = VideoJob.objects.filter(pk=job.pk, status='failed',
            error_code=job.error_code, retryable=job.retryable,
            provider_video_url=job.provider_video_url).update(
            status='queued', error_code='', error_message='', retryable=False)
        if not updated:
            return Response({'detail': 'Only retryable failed jobs can be queued again.'}, status=409)
        job.refresh_from_db()
        return video_response(job, wait)
