"""Compatibility exports for the original blazer material API."""
from fabricapp.ai.fabric.fabric_material import (
    FABRIC_TYPES, MATERIAL_PROMPTS, MATERIAL_COLOUR_RULE,
    validate_fabric_type, material_prompt,
)

__all__ = ["FABRIC_TYPES", "MATERIAL_PROMPTS", "MATERIAL_COLOUR_RULE",
           "validate_fabric_type", "material_prompt"]
