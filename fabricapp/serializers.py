"""
Request validation for the fabric try-on API.
"""

from rest_framework import serializers

from .ai.backgrounds import BACKGROUND_OPTIONS
from .ai.camera_data import CAMERA_VIEW_OPTIONS
from .ai.detail_engine import validate_detail_keys
from .ai.faces import FACE_OPTIONS
from .ai.pose_registry import get_pose_metadata, get_pose_options
from .ai.router import (
    GARMENT_STYLE_OPTIONS,
    IMPLEMENTED_GARMENT_TYPES,
)


GARMENT_TYPE_CHOICES = [
    ("kurta", "Kurta"),
    ("kurti_pant", "Kurti + Pant"),
    ("pant", "Pant only"),
    ("saree", "Saree"),
    ("shirt", "Shirt"),
    ("blazer", "Blazer"),
]

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

BLANK_TOLERANT_KEYS = ("face_choice", "body_type", "pose")


class FabricTryOnRequestSerializer(serializers.Serializer):
    person_image = serializers.ImageField(required=False)

    # Exactly one of fabric_image or garment_image is required.
    fabric_image = serializers.ImageField(required=False)
    garment_image = serializers.ImageField(required=False)

    garment_type = serializers.ChoiceField(
        choices=GARMENT_TYPE_CHOICES,
        required=False,
    )
    garment_style = serializers.CharField(
        required=False,
        allow_blank=False,
    )

    garment_details = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
    )

    camera_view = serializers.CharField(
        required=False,
        allow_blank=False,
    )
    background = serializers.CharField(
        required=False,
        allow_blank=False,
    )

    # Pose validity depends on garment_type, so validate it in validate().
    pose = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    gender = serializers.ChoiceField(
        choices=GENDER_CHOICES,
        required=False,
    )
    body_type = serializers.ChoiceField(
        choices=BODY_TYPE_CHOICES,
        required=False,
        allow_blank=True,
    )

    face_choice = serializers.ChoiceField(
        choices=FACE_CHOICES,
        required=False,
        allow_blank=True,
    )
    face_image = serializers.ImageField(required=False)

    additional_style_note = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=300,
    )

    # Optional testing overrides. If omitted, the garment builder uses
    # that garment's defaults.
    seed = serializers.IntegerField(required=False)
    guidance = serializers.FloatField(required=False)

    options = serializers.JSONField(required=False, default=dict)

    def validate_garment_type(self, value):
        if value not in IMPLEMENTED_GARMENT_TYPES:
            raise serializers.ValidationError(
                f"garment_type '{value}' is not implemented yet."
            )
        return value

    def validate_garment_details(self, value):
        """Flatten comma-separated values, remove blanks and duplicates."""
        keys = []
        for item in value:
            for part in str(item).split(","):
                part = part.strip()
                if part and part not in keys:
                    keys.append(part)
        return keys

    def validate_options(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("options must be a JSON object.")

        supported = {"draft_mode", "fabric_crop_box"}
        unknown = sorted(set(value) - supported)
        if unknown:
            raise serializers.ValidationError(
                f"Unsupported option(s): {unknown}. Supported options: "
                f"{sorted(supported)}."
            )

        if "draft_mode" in value and not isinstance(value["draft_mode"], bool):
            raise serializers.ValidationError(
                "options.draft_mode must be true or false."
            )

        if "fabric_crop_box" in value:
            crop_box = value["fabric_crop_box"]
            if (
                not isinstance(crop_box, list)
                or len(crop_box) != 4
                or any(type(coordinate) is not int for coordinate in crop_box)
            ):
                raise serializers.ValidationError(
                    "options.fabric_crop_box must be a list of four integers: "
                    "[left, upper, right, lower]."
                )
            left, upper, right, lower = crop_box
            if left < 0 or upper < 0 or right <= left or lower <= upper:
                raise serializers.ValidationError(
                    "options.fabric_crop_box must have non-negative left/upper "
                    "coordinates and right/lower greater than left/upper."
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

    def _drop_blank_optional_keys(self, data):
        for key in BLANK_TOLERANT_KEYS:
            if data.get(key) == "":
                data.pop(key)

    def _check_garment_source(self, data):
        fabric_image = data.get("fabric_image")
        garment_image = data.get("garment_image")
        garment_type = data.get("garment_type")
        garment_style = data.get("garment_style")

        if bool(fabric_image) == bool(garment_image):
            raise serializers.ValidationError({
                "fabric_image": (
                    "Provide exactly one of fabric_image or garment_image."
                )
            })

        if garment_image:
            if garment_type or garment_style:
                raise serializers.ValidationError({
                    "garment_type": (
                        "garment_type and garment_style are not used "
                        "when garment_image is provided."
                    )
                })
            if "fabric_crop_box" in data.get("options", {}):
                raise serializers.ValidationError({
                    "options": (
                        "fabric_crop_box can only be used with fabric_image."
                    )
                })
            return

        if not garment_type:
            raise serializers.ValidationError({
                "garment_type": "garment_type is required with fabric_image."
            })

        valid_styles = GARMENT_STYLE_OPTIONS.get(garment_type)
        if valid_styles is not None:
            if not garment_style:
                raise serializers.ValidationError({
                    "garment_style": (
                        f"garment_style is required for '{garment_type}'. "
                        f"Valid values: {valid_styles}."
                    )
                })
            if garment_style not in valid_styles:
                raise serializers.ValidationError({
                    "garment_style": (
                        f"'{garment_style}' is not valid for '{garment_type}'. "
                        f"Valid values: {valid_styles}."
                    )
                })
        elif garment_style:
            raise serializers.ValidationError({
                "garment_style": (
                    f"'{garment_type}' does not accept garment_style."
                )
            })

    def _check_pose(self, data):
        pose = data.get("pose")
        if not pose:
            return

        garment_type = data.get("garment_type")
        valid_poses = get_pose_options(garment_type)

        if pose not in valid_poses:
            raise serializers.ValidationError({
                "pose": (
                    f"'{pose}' is not a valid pose for "
                    f"'{garment_type or 'this request'}'."
                )
            })

        metadata = get_pose_metadata(garment_type, pose) or {}

        if metadata.get("hides_face") and (
            data.get("face_choice") or data.get("face_image")
        ):
            raise serializers.ValidationError({
                "pose": (
                    f"Pose '{pose}' hides the face and cannot be combined "
                    "with face_choice or face_image."
                )
            })

        if (
            data.get("camera_view") == "close_up"
            and metadata.get("requires_full_body")
        ):
            raise serializers.ValidationError({
                "pose": (
                    f"Pose '{pose}' requires a full-body view and cannot "
                    "be used with camera_view 'close_up'."
                )
            })

    def _check_person_source(self, data):
        person_image = data.get("person_image")
        gender = data.get("gender")
        body_type = data.get("body_type")
        face_choice = data.get("face_choice")
        face_image = data.get("face_image")

        if face_choice and face_image:
            raise serializers.ValidationError({
                "face_image": "Send either face_choice or face_image, not both."
            })

        if person_image:
            if gender or body_type or face_choice or face_image:
                raise serializers.ValidationError({
                    "person_image": (
                        "gender, body_type, face_choice, and face_image "
                        "cannot be used with person_image."
                    )
                })
            return

        if not gender:
            raise serializers.ValidationError({
                "gender": (
                    "gender is required when person_image is not provided."
                )
            })

        if face_choice:
            valid_faces = FACE_OPTIONS.get(gender, [])
            if face_choice not in valid_faces:
                raise serializers.ValidationError({
                    "face_choice": (
                        f"'{face_choice}' is not a valid face for '{gender}'. "
                        f"Valid faces: {valid_faces}."
                    )
                })

    def _check_garment_details(self, data):
        keys = data.get("garment_details") or []
        if not keys:
            return

        if data.get("garment_image"):
            raise serializers.ValidationError({
                "garment_details": (
                    "garment_details cannot be used with garment_image."
                )
            })

        error = validate_detail_keys(
            data.get("garment_type"),
            data.get("garment_style"),
            keys,
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
