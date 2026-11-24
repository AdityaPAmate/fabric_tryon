from rest_framework import serializers
from fabricapp.serializers import FabricTryOnRequestSerializer, GARMENT_TYPE_CHOICES

MOTIONS = ('auto', 'turn', 'subtle')


class VideoRequestSerializer(FabricTryOnRequestSerializer):
    """All existing image inputs retain their existing validation."""
    motion = serializers.ChoiceField(choices=MOTIONS, default='auto')


class AnimateImageSerializer(serializers.Serializer):
    """Reuse an existing generated photo without an extra image-generation call."""
    source_image = serializers.ImageField()
    garment_type = serializers.ChoiceField(choices=GARMENT_TYPE_CHOICES, required=False)
    motion = serializers.ChoiceField(choices=MOTIONS, default='auto')
    pose = serializers.CharField(required=False, allow_blank=True, max_length=100)
    camera_view = serializers.ChoiceField(choices=('front', 'side', 'close_up'), required=False)
