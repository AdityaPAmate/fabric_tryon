import hmac
from django.conf import settings
from django.http import Http404
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed, APIException
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from fabricapp.models import VideoJob
from .serializers import VideoRequestSerializer, AnimateImageSerializer
from .service import create_job, job_response, can_retry
from .registry import get_definition, DefinitionUnavailable


class VideoNotConfigured(APIException):
    status_code = 503
    default_detail = 'Video API is not configured. Set VIDEO_API_TOKEN and GIMMECLIP_API_KEY.'


class VideoAuthentication(BaseAuthentication):
    def authenticate_header(self, request):
        return 'Bearer'

    def authenticate(self, request):
        token = settings.VIDEO_API_TOKEN
        if not token or not settings.GIMMECLIP_API_KEY:
            raise VideoNotConfigured()
        supplied = request.headers.get('Authorization', '')
        if not hmac.compare_digest(supplied.encode(), ('Bearer ' + token).encode()):
            raise AuthenticationFailed('A valid video API bearer token is required.')
        return None


class VideoView(APIView):
    authentication_classes = [VideoAuthentication]
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
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_job(serializer.validated_data)
        return Response(job_response(job), status=status.HTTP_202_ACCEPTED)


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
        return Response(job_response(job), status=202)
