"""
Stage: Request validation.
Defines what a valid API request looks like — which fields are
required, and which garment_type values are currently supported.
"""

from rest_framework import serializers

GARMENT_TYPE_CHOICES = [
    ("kurta", "Kurta"),
    ("kurti_pant", "Kurti + Pant"),
    ("pant", "Pant only"),
    ("saree", "Saree"),
    ("shirt", "Shirt"),
    ("frock", "Frock"),
]

# Only these have a working, tested pipeline right now.
# Others are listed above for API stability but are not built yet.
IMPLEMENTED_GARMENT_TYPES = {"kurta", "kurti_pant", "saree", "shirt", "pant"}


class FabricTryOnRequestSerializer(serializers.Serializer):
    person_image = serializers.ImageField(required=True)
    fabric_image = serializers.ImageField(required=True)
    garment_type = serializers.ChoiceField(
        choices=GARMENT_TYPE_CHOICES, required=True
    )
    options = serializers.JSONField(required=False, default=dict)

    def validate_garment_type(self, value):
        if value not in IMPLEMENTED_GARMENT_TYPES:
            raise serializers.ValidationError(
                f"garment_type '{value}' is not implemented yet."
            )
        return value

    def validate(self, data):
        # Garment-specific options validation can be added here later,
        # once a garment_type actually needs extra options.
        return data