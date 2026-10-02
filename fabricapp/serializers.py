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
from .ai.pose_data import POSE_OPTIONS, POSES_HIDING_FACE, POSE_ONLY_FOR
from .ai.garment_details import validate_detail_keys

GARMENT_TYPE_CHOICES = [
    ("kurta", "Kurta"),
    ("kurti_pant", "Kurti + Pant"),
    ("pant", "Pant only"),
    ("saree", "Saree"),
    ("shirt", "Shirt"),
    ("frock", "Frock"),
    ("blazer", "Blazer"),
]

# Only these have a working pipeline right now.
IMPLEMENTED_GARMENT_TYPES = {"kurta", "kurti_pant", "saree", "shirt", "pant", "blazer"}

# Used only when no person_image is given (the model generates the person).
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

# Flat list of every predefined face name (both genders). Which face
# is allowed with which gender is checked in validate() below.
FACE_CHOICES = [
    (name, name.capitalize())
    for names in FACE_OPTIONS.values()
    for name in names
]

# Built from pose_data.py — adding a new pose there automatically makes
# it a valid choice here, no other change needed.
POSE_CHOICES = [(p, p) for p in POSE_OPTIONS]

# Optional keys that Postman/forms sometimes send with an empty value.
# An empty value is treated exactly like "not sent".
BLANK_TOLERANT_KEYS = ("face_choice", "body_type", "pose")


class FabricTryOnRequestSerializer(serializers.Serializer):
    # Optional: if not given, the model generates its own person.
    person_image = serializers.ImageField(required=False)

    # Exactly one of fabric_image / garment_image is required
    # (checked in validate()).
    fabric_image = serializers.ImageField(required=False)
    garment_image = serializers.ImageField(required=False)

    # Only used with fabric_image (checked in validate()).
    garment_type = serializers.ChoiceField(
        choices=GARMENT_TYPE_CHOICES, required=False
    )
    garment_style = serializers.CharField(required=False, allow_blank=False)

    # Movable parts (sleeves, tuck, dupatta). Send the key repeatedly
    # (garment_details=folded_sleeves & garment_details=tucked) or comma-separated.
    garment_details = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False
    )

    # Prompt-text overrides. Not sent => original photo's pose /
    # background is kept.
    camera_view = serializers.CharField(required=False, allow_blank=False)
    background = serializers.CharField(required=False, allow_blank=False)

    # NEW — this field was missing entirely, which was the root cause
    # of "pose is ignored, original pose stays": DRF silently drops any
    # field that is not declared here, so pose never reached the engine.
    # Not sent => original pose (person_photo) / default own-model pose
    # is kept, exactly like before this feature existed.
    pose = serializers.ChoiceField(
        choices=POSE_CHOICES, required=False, allow_blank=True
    )

    # Used only when no person_image is given.
    gender = serializers.ChoiceField(choices=GENDER_CHOICES, required=False)
    body_type = serializers.ChoiceField(
        choices=BODY_TYPE_CHOICES, required=False, allow_blank=True
    )

    # OPTIONAL. Not sent => the model generates its own face.
    face_choice = serializers.ChoiceField(
        choices=FACE_CHOICES, required=False, allow_blank=True
    )

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

    def validate_garment_details(self, value):
        """Flattens comma-separated values, drops blanks and duplicates."""
        keys = []
        for item in value:
            for part in str(item).split(","):
                part = part.strip()
                if part and part not in keys:
                    keys.append(part)
        return keys


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

    def _drop_blank_optional_keys(self, data):
        """Treat an empty face_choice / body_type / pose as 'not sent'."""
        for key in BLANK_TOLERANT_KEYS:
            if data.get(key) == "":
                data.pop(key)

    def _check_garment_source(self, data):
        """Rules for fabric_image / garment_image / garment_type / garment_style."""
        fabric_image = data.get("fabric_image")
        garment_image = data.get("garment_image")
        garment_type = data.get("garment_type")
        garment_style = data.get("garment_style")

        if bool(fabric_image) == bool(garment_image):
            raise serializers.ValidationError(
                {"fabric_image": "Provide exactly one of fabric_image or garment_image — not both, and not neither."}
            )

        if garment_image:
            if garment_type or garment_style:
                raise serializers.ValidationError(
                    {"garment_type": "garment_type/garment_style are not used when garment_image is provided."}
                )
            return

        # fabric_image path
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

    def _check_person_source(self, data):
        """Rules for person_image / gender / body_type / face_choice."""
        person_image = data.get("person_image")
        gender = data.get("gender")
        body_type = data.get("body_type")
        face_choice = data.get("face_choice")

        if person_image:
            # A real person photo is given: the person's own body and
            # face must not be changed, so these must not be sent.
            if gender or body_type or face_choice:
                raise serializers.ValidationError(
                    {"gender": "gender/body_type/face_choice are not applicable when person_image is uploaded."}
                )
            return

        # No person photo: the model generates the person.
        if not gender:
            raise serializers.ValidationError(
                {"gender": "gender is required when no person_image is uploaded, so a model can be AI-generated."}
            )

        # face_choice is OPTIONAL. Only if it IS sent, it must match the gender.
        if face_choice:
            valid_faces = FACE_OPTIONS.get(gender)
            if valid_faces is None:
                raise serializers.ValidationError(
                    {"face_choice": f"No predefined faces exist for gender '{gender}'. Do not send face_choice — the model will generate its own face."}
                )
            if face_choice not in valid_faces:
                raise serializers.ValidationError(
                    {"face_choice": f"'{face_choice}' is not a valid face for gender '{gender}'. Valid faces for '{gender}': {valid_faces}."}
                )

    def _check_pose(self, data):
        """
        A pose that hides the face (see pose_data.POSES_HIDING_FACE)
        cannot be combined with face_choice — the generated face would
        never be visible, so there would be nothing to verify it against.
        """
        pose = data.get("pose")
        face_choice = data.get("face_choice")
        if pose in POSES_HIDING_FACE and face_choice:
            raise serializers.ValidationError(
                {"pose": f"pose '{pose}' hides the face and cannot be combined with face_choice."}
            )
        allowed_garments = POSE_ONLY_FOR.get(pose)
        if allowed_garments is not None and data.get("garment_type") not in allowed_garments:
            raise serializers.ValidationError(
                {"pose": f"pose '{pose}' is only available for garment_type {allowed_garments}."}
            )

    def _check_garment_details(self, data):
        keys = data.get("garment_details") or []
        if not keys:
            return
        if data.get("garment_image"):
            raise serializers.ValidationError(
                {"garment_details": "garment_details are not used when garment_image is provided."}
            )
        error = validate_detail_keys(
            data.get("garment_type"), data.get("garment_style"), keys
        )
        if error:
            raise serializers.ValidationError({"garment_details": error})


    def validate(self, data):
        self._drop_blank_optional_keys(data)
        self._check_garment_source(data)
        self._check_garment_details(data)
        self._check_person_source(data)
        self._check_pose(data)
        return data