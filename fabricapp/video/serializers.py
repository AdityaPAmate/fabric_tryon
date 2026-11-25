from rest_framework import serializers
from fabricapp.serializers import FabricTryOnRequestSerializer, GARMENT_TYPE_CHOICES
from .profiles import MOTION_CHOICES


class VideoRequestSerializer(FabricTryOnRequestSerializer):
    """Preserve image validation; choose only the requested video motion."""
    video_motion = serializers.ChoiceField(choices=MOTION_CHOICES, default='mirror_check')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        validate_commercial_garment(attrs)
        return attrs


class AnimateImageSerializer(serializers.Serializer):
    """Reuse an existing generated photo without an extra image-generation call."""
    source_image = serializers.ImageField()
    garment_type = serializers.ChoiceField(choices=GARMENT_TYPE_CHOICES, required=False)
    pose = serializers.CharField(required=False, allow_blank=True, max_length=100)
    camera_view = serializers.ChoiceField(choices=('front', 'side', 'close_up'), required=False)
    video_motion = serializers.ChoiceField(choices=MOTION_CHOICES, default='mirror_check')

    def validate(self, attrs):
        validate_commercial_garment(attrs)
        return attrs


def validate_commercial_garment(attrs):
    if attrs.get('video_motion') == 'shirt_commercial' and attrs.get('garment_type', 'shirt') != 'shirt':
        raise serializers.ValidationError({'video_motion': 'Cinematic shirt commercial is for shirts only.'})
