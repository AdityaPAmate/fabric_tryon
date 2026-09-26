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
    FACE_OPTIONS,
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

IMPLEMENTED_GARMENT_TYPES = {"kurta", "kurti_pant", "saree", "shirt", "pant", "blazer"}

GENDER_CHOICES = [
    ("men", "Men"),
    ("women", "Women"),
    ("boy", "Boy"),
    ("girl", "Girl"),
]

BODY_TYPE_CHOICES = [
    ("slim", "Slim"),
    ("trim", "Trim"),
    ("plus", "Plus"),
]

FACE_CHOICES = [
    (name, name.capitalize())
    for names in FACE_OPTIONS.values()
    for name in names
]


class FabricTryOnRequestSerializer(serializers.Serializer):
    person_image = serializers.ImageField(required=False)
    fabric_image = serializers.ImageField(required=False)
    garment_image = serializers.ImageField(required=False)

    garment_type = serializers.ChoiceField(
        choices=GARMENT_TYPE_CHOICES, required=False
    )
    garment_style = serializers.CharField(required=False, allow_blank=False)

    camera_view = serializers.CharField(required=False, allow_blank=False)
    background = serializers.CharField(required=False, allow_blank=False)

    gender = serializers.ChoiceField(choices=GENDER_CHOICES, required=False)
    body_type = serializers.ChoiceField(choices=BODY_TYPE_CHOICES, required=False)
    face_choice = serializers.ChoiceField(choices=FACE_CHOICES, required=False)

    additional_style_note = serializers.CharField(
        required=False, allow_blank=False, max_length=300
    )

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
                f"'{value}' is not a valid camera_view. Valid values: {CAMERA_VIEW_OPTIONS}."
            )
        return value

    def validate_background(self, value):
        if value not in BACKGROUND_OPTIONS:
            raise serializers.ValidationError(
                f"'{value}' is not a valid background. Valid values: {BACKGROUND_OPTIONS}."
            )
        return value

    def validate(self, data):
        person_image = data.get("person_image")
        fabric_image = data.get("fabric_image")
        garment_image = data.get("garment_image")
        garment_type = data.get("garment_type")
        garment_style = data.get("garment_style")
        gender = data.get("gender")
        body_type = data.get("body_type")
        face_choice = data.get("face_choice")

        if bool(fabric_image) == bool(garment_image):
            raise serializers.ValidationError(
                {"fabric_image": "Provide exactly one of fabric_image or garment_image — not both, and not neither."}
            )

        if fabric_image:
            if not garment_type:
                raise serializers.ValidationError(
                    {"garment_type": "garment_type is required when fabric_image is used."}
                )
            valid_styles = GARMENT_STYLE_OPTIONS.get(garment_type)
            if valid_styles is not None:
                if not garment_style:
                    raise serializers.ValidationError(
                        {"garment_style": f"garment_style is required for garment_type '{garment_type}'. Valid values: {valid_styles}."}
                    )
                if garment_style not in valid_styles:
                    raise serializers.ValidationError(
                        {"garment_style": f"'{garment_style}' is not valid for garment_type '{garment_type}'. Valid values: {valid_styles}."}
                    )
            elif garment_style:
                raise serializers.ValidationError(
                    {"garment_style": f"garment_type '{garment_type}' does not accept a garment_style value."}
                )
        else:
            if garment_type or garment_style:
                raise serializers.ValidationError(
                    {"garment_type": "garment_type/garment_style are not used when garment_image is provided."}
                )

        if person_image:
            if gender or body_type or face_choice:
                raise serializers.ValidationError(
                    {"gender": "gender/body_type/face_choice are not applicable when person_image is uploaded — the uploaded person's own body and face must not be changed."}
                )
        else:
            if not gender:
                raise serializers.ValidationError(
                    {"gender": "gender is required when no person_image is uploaded, so a model can be AI-generated."}
                )

            valid_faces_for_gender = FACE_OPTIONS.get(gender)
            if valid_faces_for_gender is None:
                raise serializers.ValidationError(
                    {"gender": f"Face images are not available yet for gender '{gender}'. Currently supported: {list(FACE_OPTIONS.keys())}."}
                )

            if not face_choice:
                raise serializers.ValidationError(
                    {"face_choice": "face_choice is required when no person_image is uploaded, so a face can be attached for the AI-generated model."}
                )

            if face_choice not in valid_faces_for_gender:
                raise serializers.ValidationError(
                    {"face_choice": f"'{face_choice}' is not a valid face for gender '{gender}'. Valid faces for '{gender}': {valid_faces_for_gender}."}
                )

        return data