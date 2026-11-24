from rest_framework import serializers
from fabricapp.serializers import FabricTryOnRequestSerializer, GARMENT_TYPE_CHOICES


class VideoRequestSerializer(FabricTryOnRequestSerializer):
    """Image validation is unchanged; video uses the single fixed mirror motion."""
    pass


class AnimateImageSerializer(serializers.Serializer):
    """Reuse an existing generated photo without an extra image-generation call."""
    source_image = serializers.ImageField()
    garment_type = serializers.ChoiceField(choices=GARMENT_TYPE_CHOICES, required=False)
    pose = serializers.CharField(required=False, allow_blank=True, max_length=100)
    camera_view = serializers.ChoiceField(choices=('front', 'side', 'close_up'), required=False)
