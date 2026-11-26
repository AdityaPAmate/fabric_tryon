from rest_framework import serializers
from fabricapp.serializers import FabricTryOnRequestSerializer, GARMENT_TYPE_CHOICES
from rest_framework.exceptions import APIException
from .registry import get_definition, DefinitionUnavailable


class VideoDefinitionUnavailable(APIException):
    status_code = 503
    default_detail = 'Video configuration is unavailable for this garment.'


class VideoRequestSerializer(FabricTryOnRequestSerializer):
    """Preserve image validation; choose only the requested video motion."""
    video_motion = serializers.CharField(required=False, max_length=64)

    def validate(self, attrs):
        # Ready-made image validation historically has no garment_type. Retain
        # that image contract; this extra type is solely animation context.
        video_type = attrs.pop('garment_type', None) if attrs.get('garment_image') else None
        attrs = super().validate(attrs)
        if video_type:
            attrs['garment_type'] = video_type
        return validate_video_selection(attrs)


class AnimateImageSerializer(serializers.Serializer):
    """Reuse an existing generated photo without an extra image-generation call."""
    source_image = serializers.ImageField()
    garment_type = serializers.ChoiceField(choices=GARMENT_TYPE_CHOICES)
    pose = serializers.CharField(required=False, allow_blank=True, max_length=100)
    camera_view = serializers.ChoiceField(choices=('front', 'side', 'close_up'), required=False)
    video_motion = serializers.CharField(required=False, max_length=64)

    def validate(self, attrs):
        return validate_video_selection(attrs)


def validate_video_selection(attrs):
    # Extra requirements belong to video, never the tested image serializer.
    if not attrs.get('garment_type'):
        raise serializers.ValidationError({'garment_type': 'Choose the garment type for this video.'})
    try:
        definition = get_definition(attrs['garment_type'])
        style = definition.resolve(attrs.get('video_motion'))
    except DefinitionUnavailable as exc:
        raise VideoDefinitionUnavailable(str(exc)) from exc
    except ValueError as exc:
        raise serializers.ValidationError({'video_motion': str(exc)}) from exc
    attrs['video_motion'] = style.id
    return attrs
