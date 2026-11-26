"""Small, immutable video definitions. No image/catalog dependencies."""
from dataclasses import dataclass


@dataclass(frozen=True)
class VideoStyle:
    id: str
    label: str
    version: str
    prompt: str
    help: str
    seconds: int = 8
    renderer: str = 'passthrough'
    allow_cuts: bool = False
    camera_motion: str = 'locked'

    def __post_init__(self):
        if not self.id or not self.version or not 3 <= len(self.prompt) <= 300:
            raise ValueError('A video style needs an ID, version and 3–300 character prompt.')
        if self.seconds not in (4, 6, 8):
            raise ValueError('Gimmeclip animation supports 4, 6 or 8 seconds.')
        if self.renderer not in ('passthrough', 'shirt_collar'):
            raise ValueError('Unknown video renderer.')
        if self.renderer == 'shirt_collar' and (self.seconds != 8 or not self.allow_cuts):
            raise ValueError('The existing shirt collar composition needs eight seconds and cuts.')
        if self.camera_motion not in ('locked', 'zoom_out'):
            raise ValueError('Unknown camera motion.')

    def profile(self, garment_type):
        # JSON snapshot: workers/retries never resolve a newer definition.
        result = {'garment_type': garment_type, 'version': self.version,
                  'motion': self.id, 'seconds': self.seconds, 'prompt': self.prompt,
                  'renderer': self.renderer}
        if self.allow_cuts:
            result['multi_shot'] = True
        if self.renderer == 'shirt_collar':
            result['source_collar_opening'] = True  # saved-job compatibility
        if self.camera_motion != 'locked':
            result['camera_motion'] = self.camera_motion
        return result


@dataclass(frozen=True)
class GarmentVideoDefinition:
    garment_type: str
    label: str
    default_style: str
    styles: tuple[VideoStyle, ...]
    source_hint: str
    compatibility_styles: tuple[VideoStyle, ...] = ()

    def __post_init__(self):
        if not 1 <= len(self.styles) <= 2:
            raise ValueError('Publish one or at most two video styles per garment.')
        # User explicitly retained the existing third shirt option until selection.
        if self.compatibility_styles and (self.garment_type != 'shirt' or
                tuple(s.id for s in self.compatibility_styles) != ('shirt_commercial',)):
            raise ValueError('Only the existing third shirt option has compatibility status.')
        ids = [s.id for s in self.all_styles]
        if len(ids) != len(set(ids)) or self.default_style not in [s.id for s in self.styles]:
            raise ValueError('Style IDs must be unique and include the default.')
        if self.garment_type != 'shirt' and any(s.renderer == 'shirt_collar' for s in self.all_styles):
            raise ValueError('A collar composition belongs to shirts only.')

    @property
    def all_styles(self):
        return self.styles + self.compatibility_styles

    def resolve(self, style_id=None):
        style_id = style_id or self.default_style
        for style in self.all_styles:
            if style.id == style_id:
                return style
        raise ValueError(f'Video style {style_id!r} is not available for {self.garment_type}.')

    def options(self):
        return {'garment_type': self.garment_type, 'label': self.label,
                'default_style': self.default_style, 'source_hint': self.source_hint,
                'styles': [{'id': s.id, 'label': s.label, 'seconds': s.seconds,
                            'help': s.help, 'version': s.version,
                            'camera_motion': s.camera_motion,
                            'compatibility': s in self.compatibility_styles}
                           for s in self.all_styles]}
