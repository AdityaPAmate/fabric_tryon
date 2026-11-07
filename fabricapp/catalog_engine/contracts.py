"""Small immutable catalog definitions; no HTTP or provider work here."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Shot:
    key: str
    description: str
    operation: str  # pipeline, anchor_edit, template_edit, crop
    framing: str
    dependencies: tuple[str, ...] = ()
    reference: Path | None = None
    identity_from: str | None = None  # request, or an earlier shot key
    scenario: str = "person_photo"
    camera_view: str | None = None
    pipeline_options: dict = field(default_factory=dict)
    identity_crop: tuple[float, float, float, float] | None = None
    reference_role: str = "template"
    composition_crop: tuple[float, float, float, float] | None = None
    source_crop: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class Panel:
    shot: str
    box: tuple[int, int, int, int]
    fit: str = "contain"


@dataclass(frozen=True)
class Text:
    value: str
    position: tuple[int, int]
    size: int
    width: int
    fill: str = "#242424"
    font: str = "sans"
    anchor: str = "lt"


@dataclass(frozen=True)
class Layout:
    version: str
    size: tuple[int, int]
    panels: tuple[Panel, ...]
    swatch_box: tuple[int, int, int, int] | None = None
    texts: tuple[Text, ...] = ()
    lines: tuple[tuple[int, int, int, int], ...] = ()
    background: str = "white"


@dataclass(frozen=True)
class CatalogDefinition:
    garment: str
    edition: str
    shots: tuple[Shot, ...]
    build_config: Callable
    layout: Callable
    product_fields: tuple[str, ...] = ()
    validate_request: Callable | None = None
