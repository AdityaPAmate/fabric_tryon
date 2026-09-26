"""
Stage: API view. Validates the request, calls the engine, returns the
image as a JSON response (base64-encoded), not raw binary.
This file knows nothing about Cloudflare or image resizing internals —
that all lives in ai/cloudflare_engine.py.
"""

import base64
import logging

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
        camera_view = data.get("camera_view")
        background = data.get("background")

        try:
            image_bytes = generate_tryon_image(
                person_image=data.get("person_image"),
                fabric_image=data.get("fabric_image"),
                garment_image=data.get("garment_image"),
                garment_type=data.get("garment_type"),
                garment_style=data.get("garment_style"),
                gender=data.get("gender"),
                body_type=data.get("body_type"),
                face_choice=data.get("face_choice"),
                camera_view=camera_view,
                background=background,
                additional_style_note=data.get("additional_style_note"),
                options=data.get("options", {}),
            )
        except CloudflareGenerationError as e:
            logger.error("Generation failed: %s", e)
            return Response(
                {"success": False, "error": "Image generation failed. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        encoded_image = base64.b64encode(image_bytes).decode("utf-8")

        response_data = {
            "success": True,
            "garment_type": data.get("garment_type"),
            "garment_style": data.get("garment_style"),
            "camera_view": camera_view or "default",
            "background": background or "default",
            "gender": data.get("gender"),
            "body_type": data.get("body_type") or "default",
            "face_choice": data.get("face_choice"),
            "images": [
                {
                    "view": camera_view or "default",
                    "format": "png",
                    "data": encoded_image,
                }
            ],
        }
        return Response(response_data, status=status.HTTP_200_OK)