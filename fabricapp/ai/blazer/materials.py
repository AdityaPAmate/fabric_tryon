"""Optional blazer surface instructions; unspecified keeps existing prompts."""

FABRIC_TYPES = ("unspecified", "cotton", "silk", "velvet")

MATERIAL_PROMPTS = {
    "cotton": (
        "MATERIAL: the jacket is cotton, with a fine visible woven surface, "
        "a predominantly matte finish and soft diffuse highlights. Use natural "
        "cotton creases while retaining the selected blazer's tailored structure. "
    ),
    "silk": (
        "MATERIAL: the jacket is silk, with a fine smooth surface, a soft "
        "controlled lustrous sheen and smooth flowing fold highlights. Keep "
        "the sheen restrained and the selected blazer's tailored structure intact. "
    ),
    "velvet": (
        "MATERIAL: the jacket is velvet, with a dense short plush pile and "
        "a soft directional nap. Render angle-dependent velvety sheen and "
        "rich fold shadows, with visible pile variation across the lapels "
        "and sleeves, retaining the selected blazer's tailored structure. "
    ),
}

MATERIAL_COLOUR_RULE = (
    "This material choice controls surface texture and light response only; "
    "preserve the swatch's original colour family, pattern and motif scale. "
    "The material applies to the jacket only; the other garments follow "
    "their separate outfit descriptions. "
)


def validate_fabric_type(fabric_type, garment_type, use_garment_image=False):
    if fabric_type not in FABRIC_TYPES:
        return "fabric_type must be one of: " + ", ".join(FABRIC_TYPES) + "."
    if fabric_type != "unspecified" and (use_garment_image or garment_type != "blazer"):
        return "cotton, silk and velvet are currently supported only with blazer fabric_image requests."
    return None


def material_prompt(fabric_type="unspecified"):
    if fabric_type == "unspecified":
        return ""
    return MATERIAL_PROMPTS[fabric_type] + MATERIAL_COLOUR_RULE
