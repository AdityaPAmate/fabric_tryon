"""
Stage: API view. Validates the request, calls the engine, returns the image.
This file knows nothing about Cloudflare or image resizing internals —
that all lives in ai/cloudflare_engine.py.
"""

import logging

from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai.cloudflare_engine import CloudflareGenerationError, generate_tryon_image
from .serializers import FabricTryOnRequestSerializer

logger = logging.getLogger("fabricapp")


class FabricTryOnView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = FabricTryOnRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning("Invalid request received: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            image_bytes = generate_tryon_image(
                person_image=data["person_image"],
                fabric_image=data["fabric_image"],
                garment_type=data["garment_type"],
                options=data.get("options", {}),
            )
        except CloudflareGenerationError as e:
            logger.error("Generation failed: %s", e)
            return Response(
                {"error": "Image generation failed. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return HttpResponse(image_bytes, content_type="image/png")