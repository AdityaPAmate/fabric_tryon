"""Sequential dependency-aware executor; garment behavior comes from definitions."""
import io
import logging
from dataclasses import dataclass
from typing import Callable
from uuid import uuid4

from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.validation import validate_definition
from fabricapp.catalog_engine.renderer import render_catalog
from fabricapp.ai.providers.cloudflare_engine import CloudflareGenerationError

logger = logging.getLogger('fabricapp')


@dataclass(frozen=True)
class Services:
    generate: Callable
    edit: Callable
    upload: Callable


def generate_catalog(data, stopped, services):
    definition = get_definition(data['garment_type'], data.get('catalog_edition'))
    layout = validate_definition(definition, data.get('catalog_product'))
    plan = definition.shots
    catalog_id = uuid4().hex
    views = [shot.key for shot in plan]
    yield {'event': 'started', 'catalog_id': catalog_id, 'total': len(plan), 'views': views,
           'catalog_edition': definition.edition, 'layout': layout.version}
    shot_bytes, seeds = {}, {}
    images, failed = [], []
    data['fabric_image'].seek(0)
    swatch_bytes = data['fabric_image'].read()
    data['fabric_image'].seek(0)
    blocked = False
    for index, shot in enumerate(plan):
        if stopped.is_set():
            return
        missing = [key for key in shot.dependencies if key not in shot_bytes]
        if blocked or missing:
            failed.append(shot.key)
            yield {'event': 'image_failed', 'view': shot.key,
                   'error': ('generation_unavailable' if blocked else
                             'front_reference_failed' if 'front' in missing else 'dependency_failed'),
                   'missing_dependencies': missing}
            continue
        yield {'event': 'generating', 'view': shot.key, 'index': index + 1, 'total': len(plan)}
        try:
            for key in ('person_image', 'fabric_image', 'face_image'):
                if data.get(key):
                    data[key].seek(0)
            if shot.operation == 'pipeline':
                shot_data = {key: value for key, value in data.items()
                             if key not in ('catalog_edition', 'catalog_product')}
                shot_data['options'] = {**data.get('options', {}), **shot.pipeline_options}
                generation = services.generate(**shot_data, camera_view=shot.camera_view)
            else:
                source = shot.reference.read_bytes() if shot.reference else shot_bytes[shot.dependencies[0]]
                seed = (seeds[shot.dependencies[0]] if shot.dependencies else data.get('seed', 42))
                config = definition.build_config(data, shot, seed)
                reference_args = {}
                if shot.identity_from == 'request':
                    reference_args = {'face_image': data.get('person_image') or data.get('face_image'),
                                      'face_choice': data.get('face_choice')}
                elif shot.identity_from:
                    reference_args = {'face_image': io.BytesIO(shot_bytes[shot.identity_from])}
                if shot.scenario == 'pose_reference':
                    reference_args['pose_reference_path'] = shot.reference
                generation = services.edit(
                    person_image=io.BytesIO(source), fabric_image=data['fabric_image'],
                    garment_type=data['garment_type'], garment_style=data.get('garment_style'),
                    scenario=shot.scenario, options=data.get('options', {}), prompt_config=config,
                    **reference_args,
                )
            # A generated dependency survives even if its delivery upload fails.
            shot_bytes[shot.key] = generation.image_bytes
            seeds[shot.key] = generation.effective_seed
            image = {'view': shot.key, **services.upload(generation.image_bytes),
                     'generation_seed': generation.effective_seed, 'generation': generation.diagnostics,
                     'framing': shot.framing,
                     'reference_template': shot.reference.name if shot.reference else None}
            images.append(image)
            yield {'event': 'image_ready', 'image': image, 'completed': len(images), 'total': len(plan)}
        except Exception as exc:
            logger.exception('Catalog shot failed: %s', shot.key)
            failed.append(shot.key)
            failure = exc.failure_type if isinstance(exc, CloudflareGenerationError) else None
            blocked = blocked or failure in ('allocation_exhausted', 'authentication_error') or (
                isinstance(exc, CloudflareGenerationError) and exc.status_code in (401, 403, 429))
            yield {'event': 'image_failed', 'view': shot.key, 'error': failure or 'image_generation_or_upload_failed',
                   'provider_code': getattr(exc, 'provider_code', None),
                   'generation': getattr(exc, 'diagnostics', None)}
    if stopped.is_set():
        return
    collage, collage_error = None, None
    if not failed:
        yield {'event': 'composing'}
        try:
            payload = render_catalog(shot_bytes, swatch_bytes, layout)
            collage = {**services.upload(payload), 'view': 'catalog', 'layout': layout.version,
                       'source_views': views, 'includes_original_swatch': layout.swatch_box is not None}
            yield {'event': 'collage_ready', 'image': collage}
        except Exception:
            logger.exception('Catalog composition or upload failed')
            collage_error = 'collage_composition_or_upload_failed'
    else:
        collage_error = 'required_views_missing'
    yield {'event': 'complete', 'status': 'completed' if collage else ('partial' if images else 'failed'),
           'catalog_id': catalog_id, 'catalog_edition': definition.edition,
           'images': images, 'failed_views': failed, 'total': len(plan),
           'collage': collage, 'collage_error': collage_error}
