"""
Stage: Request validation.
Defines what a valid API request looks like — which fields are
required, and which garment_type values are currently supported.
"""

from rest_framework import serializers

from .ai.prompts import (
    GARMENT_STYLE_OPTIONS,
    CAMERA_VIEW_OPTIONS,
    BACKGROUND_OPTIONS,
)

GARMENT_TYPE_CHOICES = [
    ("kurta", "Kurta"),
    ("kurti_pant", "Kurti + Pant"),
    ("pant", "Pant only"),
    ("saree", "Saree"),
    ("shirt", "Shirt"),
    ("frock", "Frock"),
    ("blazer", "Blazer"),
]

# Only these have a working, tested pipeline right now.
# Others are listed above for API stability but are not built yet.
IMPLEMENTED_GARMENT_TYPES = {"kurta", "kurti_pant", "saree", "shirt", "pant", "blazer"}


class FabricTryOnRequestSerializer(serializers.Serializer):
    person_image = serializers.ImageField(required=True)
    fabric_image = serializers.ImageField(required=True)
    garment_type = serializers.ChoiceField(
        choices=GARMENT_TYPE_CHOICES, required=True
    )
    # Only required for garment_types listed in GARMENT_STYLE_OPTIONS
    # (currently blazer and kurta). Left optional here at the field level
    # because whether it's required depends on garment_type — that
    # cross-field check happens in validate() below.
    garment_style = serializers.CharField(required=False, allow_blank=False)

    # NEW this session — renamed from "pose". Optional for every
    # garment_type. Not given => original pose/framing in the uploaded
    # person photo is kept unchanged (today's behavior).
    camera_view = serializers.CharField(required=False, allow_blank=False)

    # NEW this session. Optional for every garment_type. Not given =>
    # original background in the uploaded person photo is kept unchanged
    # (today's behavior).
    background = serializers.CharField(required=False, allow_blank=False)

    options = serializers.JSONField(required=False, default=dict)

    def validate_garment_type(self, value):
        if value not in IMPLEMENTED_GARMENT_TYPES:
            raise serializers.ValidationError(
                f"garment_type '{value}' is not implemented yet."
            )
        return value

    def validate_camera_view(self, value):
        if value not in CAMERA_VIEW_OPTIONS:
            raise serializers.ValidationError(
                f"'{value}' is not a valid camera_view. "
                f"Valid values: {CAMERA_VIEW_OPTIONS}."
            )
        return value

    def validate_background(self, value):
        if value not in BACKGROUND_OPTIONS:
            raise serializers.ValidationError(
                f"'{value}' is not a valid background. "
                f"Valid values: {BACKGROUND_OPTIONS}."
            )
        return value

    def validate(self, data):
        garment_type = data.get("garment_type")
        garment_style = data.get("garment_style")
        valid_styles = GARMENT_STYLE_OPTIONS.get(garment_type)

        if valid_styles is not None:
            # This garment_type requires a garment_style.
            if not garment_style:
                raise serializers.ValidationError(
                    {
                        "garment_style": (
                            f"garment_style is required for garment_type "
                            f"'{garment_type}'. Valid values: {valid_styles}."
                        )
                    }
                )
            if garment_style not in valid_styles:
                raise serializers.ValidationError(
                    {
                        "garment_style": (
                            f"'{garment_style}' is not valid for garment_type "
                            f"'{garment_type}'. Valid values: {valid_styles}."
                        )
                    }
                )
        elif garment_style:
            # garment_type doesn't use styles but one was sent anyway.
            raise serializers.ValidationError(
                {
                    "garment_style": (
                        f"garment_type '{garment_type}' does not accept a "
                        f"garment_style value."
                    )
                }
            )

        return data