"""
API view: validates the request, runs image generation, uploads the
generated image to Cloudinary, and returns its delivery URL as JSON.
"""

import logging

from django.http import JsonResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .timing import image_request_timing, timed_stage, set_timing_metadata
from .ai.cloudflare_engine import CloudflareGenerationError
from .ai.provider_errors import failure_message
from .ai.main import generate_tryon_image
from .serializers import FabricTryOnRequestSerializer
from .services.cloudinary_service import (
    CloudinaryUploadError,
    upload_generated_image,
)

logger = logging.getLogger("fabricapp")


def health_check(request):
    """Unauthenticated endpoint used by the Render health check."""
    return JsonResponse({"status": "ok"})


class FabricTryOnView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        with image_request_timing():
            response = self._generate_response(request)
            set_timing_metadata(http_status=response.status_code)
            return response

    def _generate_response(self, request):
        serializer = FabricTryOnRequestSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning("Invalid request received: %s", serializer.errors)
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        set_timing_metadata(garment=data.get("garment_type") or "garment_image",
                            style=data.get("garment_style"),
                            draft_mode=data.get("options", {}).get("draft_mode", True))

        try:
            with timed_stage("generation_total"):
                generation = generate_tryon_image(
                    person_image=data.get("person_image"),
                    fabric_image=data.get("fabric_image"),
                    garment_image=data.get("garment_image"),
                    garment_type=data.get("garment_type"),
                    garment_style=data.get("garment_style"),
                    gender=data.get("gender"),
                    body_type=data.get("body_type"),
                    face_choice=data.get("face_choice"),
                    face_image=data.get("face_image"),
                    camera_view=data.get("camera_view"),
                    background=data.get("background"),
                    additional_style_note=data.get("additional_style_note"),
                    pose=data.get("pose"),
                    garment_details=data.get("garment_details", []),
                    options=data.get("options", {}),
                    seed=data.get("seed"),
                    guidance=data.get("guidance"),
                )
        except CloudflareGenerationError as exc:
            logger.error("Generation failed: %s", exc)
            if exc.failure_type:
                return Response(
                    {
                        "success": False,
                        "error": failure_message(exc.failure_type),
                        "provider": "cloudflare",
                        "provider_code": exc.provider_code,
                        "failure_type": exc.failure_type,
                        **({"generation": exc.diagnostics} if exc.diagnostics else {}),
                    },
                    status=(status.HTTP_422_UNPROCESSABLE_ENTITY
                            if exc.failure_type in ("input_rejected", "output_rejected")
                            else status.HTTP_502_BAD_GATEWAY),
                )
            if exc.provider_code == 3030:
                return Response(
                    {
                        "success": False,
                        "error": (
                            "The image provider rejected this prompt and image "
                            "combination (Cloudflare error 3030). Try a different "
                            "source image or adjust the generation instructions."
                        ),
                        "provider": "cloudflare",
                        "provider_code": exc.provider_code,
                        "failure_type": "input_combination_rejected",
                        **({"generation": exc.diagnostics} if exc.diagnostics else {}),
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            return Response(
                {
                    "success": False,
                    "error": "Image generation failed. Please try again.",
                    "provider": "cloudflare",
                    "provider_code": exc.provider_code,
                    **({"generation": exc.diagnostics} if exc.diagnostics else {}),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            with timed_stage("cloudinary_upload"):
                uploaded_image = upload_generated_image(generation.image_bytes)
        except CloudinaryUploadError as exc:
            logger.error("Generated image could not be stored: %s", exc)
            return Response(
                {
                    "success": False,
                    "error": (
                        "Image was generated but could not be stored. "
                        "Please try again."
                    ),
                    **({"generation": generation.diagnostics} if generation.diagnostics else {}),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        camera_view = data.get("camera_view")
        pose = data.get("pose")

        response_data = {
            "success": True,
            "garment_type": data.get("garment_type"),
            "garment_style": data.get("garment_style"),
            "camera_view": camera_view or "default",
            "pose": pose or "default",
            "garment_details": data.get("garment_details", []),
            "background": data.get("background") or "default",
            "gender": data.get("gender"),
            "body_type": data.get("body_type") or "default",
            "face_choice": data.get("face_choice"),
            "face_image_uploaded": bool(data.get("face_image")),
            "generation_seed": generation.effective_seed,
            **({"generation": generation.diagnostics} if generation.diagnostics else {}),
            "images": [
                {
                    "view": camera_view or pose or "default",
                    **uploaded_image,
                }
            ],
        }

        return Response(response_data, status=status.HTTP_200_OK)
