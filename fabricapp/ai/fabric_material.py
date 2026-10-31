"""Shared swatch material contract and garment-specific surface instructions."""

FABRIC_TYPES = ("unspecified", "cotton", "silk", "velvet")
SUPPORTED_GARMENTS = frozenset(("blazer", "shirt", "kurta", "kurti_pant", "pant", "saree"))

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
    if fabric_type != "unspecified" and (use_garment_image or garment_type not in SUPPORTED_GARMENTS):
        return "cotton, silk and velvet require a supported garment_type and fabric_image; they cannot be used with garment_image."
    return None


def fabric_target(garment_type, garment_style=None, garment_details=None, pose=None):
    target = {"blazer": "jacket", "shirt": "shirt", "kurta": "kurta",
              "kurti_pant": "kurti", "pant": "trousers", "saree": "saree body and pallu"}[garment_type]
    if garment_type == "kurta":
        target = {"sherwani": "sherwani", "pathani": "pathani kurta",
                  "jodhpuri": "jodhpuri jacket"}.get(garment_style, target)
    if (garment_type in ("kurta", "kurti_pant")
            and "with_dupatta" in (garment_details or []) and pose != "pallu_on_head"):
        target += " and the selected matching dupatta"
    return target


def material_prompt(fabric_type="unspecified", garment_type="blazer", garment_style=None,
                    garment_details=None, pose=None):
    if fabric_type == "unspecified":
        return ""
    if garment_type == "blazer":
        return MATERIAL_PROMPTS[fabric_type] + MATERIAL_COLOUR_RULE
    target = fabric_target(garment_type, garment_style, garment_details, pose)
    surface = {
        "cotton": "a fine visible woven surface, a predominantly matte finish, soft diffuse highlights and natural cotton creases",
        "silk": "a fine smooth surface, restrained lustrous sheen and smooth flowing fold highlights",
        "velvet": "a dense short plush pile, soft directional nap, angle-dependent velvety sheen and rich fold shadows",
    }[fabric_type]
    construction = (
        "TROUSER CONSTRUCTION: the selected garment remains full-length formal trousers, "
        "with a waistband, a crotch, two separate trouser legs and two ankle hems. "
        "Keep the separate top already described. Preserve the requested person's "
        "gender, age, body build and camera framing while changing this trouser surface. "
        if garment_type == "pant" else ""
    )
    return (f"MATERIAL: use {fabric_type} fabric for the {target}, with {surface}. "
            "Keep the garment construction, fit, coverage and drape already described. "
            "This material choice controls surface texture and light response only; "
            "preserve the swatch's original colour family, pattern, border and motif scale. "
            f"Apply this material only to the {target}; all separate garments follow their existing outfit descriptions. "
            + construction)
