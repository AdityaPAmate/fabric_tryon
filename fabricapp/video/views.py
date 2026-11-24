import hmac
import re
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
from .service import create_job, job_response
from .gimmeclip import GimmeclipClient
from .errors import VideoError


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
        # Atomic compare-and-set prevents two retry requests from queuing it twice.
        updated = VideoJob.objects.filter(pk=job.pk, status='failed', retryable=True).update(
            status='queued', error_code='', error_message='', retryable=False)
        if not updated:
            return Response({'detail': 'Only retryable failed jobs can be queued again.'}, status=409)
        job.refresh_from_db()
        return Response(job_response(job), status=202)


class InspectVideoProviderView(VideoJobView):
    """Operator-only, read-only evidence for an existing job; never submit work."""
    def get(self, request, job_id):
        job = self.get_job(job_id)
        provider = {}
        if job.polling_url:
            try:
                provider = GimmeclipClient().status(job.polling_url)
            except VideoError as exc:
                return Response({'detail': str(exc), 'code': exc.code}, status=503)

        def clip_id(value):
            return value if isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value) else None

        raw = clip_id(provider.get('aiClip'))
        rendered = provider.get('clip')
        rendered = clip_id(rendered.get('id')) if isinstance(rendered, dict) else None
        stored = re.fullmatch(r'https://gimmeclip\.com/api/v0/clips/([a-f0-9]{64})/file', job.provider_video_url)
        stored = stored.group(1) if stored else None
        response = Response({
            'job_id': str(job.pk), 'profile_version': job.profile_version,
            'prompt': job.motion_profile.get('prompt'),
            'seconds': job.motion_profile.get('seconds'),
            'provider_state': provider.get('state'),
            'raw_clip_id': raw, 'rendered_clip_id': rendered, 'stored_clip_id': stored,
            'stored_output_kind': ('raw' if stored and stored == raw else
                                   'rendered' if stored and stored == rendered else 'unknown'),
        })
        response['Cache-Control'] = 'no-store'
        return response
