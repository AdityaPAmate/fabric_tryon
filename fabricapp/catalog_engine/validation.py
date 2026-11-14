"""Reject broken catalog definitions before spending provider calls."""


def validate_definition(definition, product=None):
    shots = definition.shots
    if not shots:
        raise ValueError("Catalog must declare at least one shot")
    seen = set()
    for shot in shots:
        if not shot.key or shot.key in seen:
            raise ValueError("Catalog shot keys must be nonempty and unique")
        if shot.operation not in {"pipeline", "anchor_edit", "template_edit", "crop", "reference", "swatch_composite"}:
            raise ValueError(f"Unknown operation for {shot.key}")
        if shot.reference_role not in {'template', 'composition', 'layout'}:
            raise ValueError(f"Unknown reference role for {shot.key}")
        if shot.reference_role == 'composition' and (
            shot.operation != 'anchor_edit' or shot.scenario != 'person_pose' or
            not shot.reference or not shot.reference.is_file()
        ):
            raise ValueError(f"Composition reference needs an anchor and pose generation: {shot.key}")
        if any(key not in seen for key in shot.dependencies):
            raise ValueError(f"Dependencies must precede {shot.key}")
        if shot.garment_from and (shot.operation != 'template_edit' or shot.garment_from not in shot.dependencies
                                  or not shot.source_crop):
            raise ValueError(f"Garment crop needs a template and dependency: {shot.key}")
        if shot.identity_from not in (None, "request"):
            if shot.identity_from not in shot.dependencies:
                raise ValueError(f"Identity source must be a dependency: {shot.key}")
        if shot.identity_crop:
            left, top, right, bottom = shot.identity_crop
            if not shot.identity_from or not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
                raise ValueError(f"Invalid identity crop for {shot.key}")
        if shot.composition_crop:
            left, top, right, bottom = shot.composition_crop
            if shot.reference_role != 'composition' or not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
                raise ValueError(f"Invalid composition crop for {shot.key}")
        if shot.operation == 'crop' or shot.garment_from:
            if not shot.dependencies or not shot.source_crop:
                raise ValueError(f"Crop needs a source and bounds: {shot.key}")
            left, top, right, bottom = shot.source_crop
            if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
                raise ValueError(f"Invalid source crop for {shot.key}")
        if shot.operation == "anchor_edit" and not shot.dependencies:
            raise ValueError(f"Anchor edit needs a dependency: {shot.key}")
        if shot.operation in {"template_edit", "reference", "swatch_composite"} and (not shot.reference or not shot.reference.is_file()):
            raise ValueError(f"Missing reference asset for {shot.key}")
        if shot.operation == 'swatch_composite' and not shot.reference_mask:
            raise ValueError(f"Missing swatch mask for {shot.key}")
        if shot.reference_mask and (shot.operation not in ('reference', 'swatch_composite') or
                                    not shot.reference_mask.is_file()):
            raise ValueError(f"Invalid reference mask for {shot.key}")
        if shot.composite_backdrop and (shot.operation != 'swatch_composite' or not shot.composite_backdrop.is_file()):
            raise ValueError(f"Invalid composite backdrop for {shot.key}")
        if shot.composite_relief and (shot.operation != 'swatch_composite' or not shot.composite_relief.is_file()):
            raise ValueError(f"Invalid composite relief for {shot.key}")
        if shot.operation == "pipeline" and not shot.camera_view:
            raise ValueError(f"Pipeline shot needs a camera view: {shot.key}")
        seen.add(shot.key)
    layout = definition.layout(product or {})
    keys = [panel.shot for panel in layout.panels]
    if len(keys) != len(set(keys)) or set(keys) != seen:
        raise ValueError("Layout panels must match the shot plan exactly")
    width, height = layout.size
    boxes = [panel.box for panel in layout.panels]
    if layout.swatch_box:
        boxes.append(layout.swatch_box)
    for left, top, right, bottom in boxes:
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError("Layout rectangle is outside the canvas")
    if any(panel.fit not in {"contain", "cover"} for panel in layout.panels):
        raise ValueError("Unknown panel fit mode")
    from fabricapp.catalog_engine.renderer import _font
    try:
        for kind in {text.font for text in layout.texts}:
            _font(kind, 20)
    except OSError as exc:
        raise ValueError("Missing catalog font asset") from exc
    for index, box in enumerate(boxes):
        for other in boxes[index + 1:]:
            if max(box[0], other[0]) < min(box[2], other[2]) and max(box[1], other[1]) < min(box[3], other[3]):
                raise ValueError("Catalog image panels overlap")
    return layout
