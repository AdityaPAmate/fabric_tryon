"""Lazy video-only allowlist; a broken garment cannot stop image/catalog URLs."""
import logging
from importlib import import_module

logger = logging.getLogger(__name__)
GARMENT_MODULES = {
    'shirt': 'fabricapp.video.garments.shirt',
    'saree': 'fabricapp.video.garments.saree',
    'kurta': 'fabricapp.video.garments.kurta',
    'kurti_pant': 'fabricapp.video.garments.kurti_pant',
    'pant': 'fabricapp.video.garments.pant',
    'blazer': 'fabricapp.video.garments.blazer',
}


class DefinitionUnavailable(RuntimeError):
    pass


def get_definition(garment_type):
    try:
        module = GARMENT_MODULES[garment_type]
    except (KeyError, TypeError):
        raise ValueError('Choose an explicit supported garment_type for video generation.') from None
    try:
        definition = import_module(module).DEFINITION
        if definition.garment_type != garment_type:
            raise ValueError('Video definition does not match its registry key.')
        return definition
    except Exception as exc:
        logger.exception('Video definition unavailable for %s', garment_type)
        raise DefinitionUnavailable(f'Video configuration is unavailable for {garment_type}.') from exc


def select_profile(data):
    definition = get_definition(data.get('garment_type'))
    return definition.resolve(data.get('video_motion')).profile(definition.garment_type)
