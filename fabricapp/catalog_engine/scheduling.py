"""Bounded catalog jobs: preserve dependencies, overlap network waits, order delivery."""
import io
import logging
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from copy import deepcopy
from contextlib import nullcontext
from math import gcd
from threading import Lock
from uuid import uuid4

from django.conf import settings

from fabricapp.ai.fabric.analysis_cache import AnalysisCache
from fabricapp.ai.providers.cloudflare_engine import CloudflareGenerationError
from fabricapp.catalog_engine.contracts import CatalogFabricMismatch
from fabricapp.catalog_engine.registry import get_request_definition
from fabricapp.catalog_engine.renderer import render_catalog
from fabricapp.catalog_engine.validation import validate_definition
from fabricapp.timing import timed_stage

logger = logging.getLogger('fabricapp')
INPUTS = ('person_image', 'fabric_image', 'garment_image', 'face_image')


def _snapshot(data):
    snapshots = {}
    for key in INPUTS:
        source = data.get(key)
        if source is not None:
            position = source.tell()
            try:
                source.seek(0)
                snapshots[key] = source.read()
            finally:
                source.seek(position)
    return snapshots


def _job_data(data, snapshots, cache):
    result = {**data, 'options': deepcopy(data.get('options') or {})}
    for key, payload in snapshots.items():
        source = io.BytesIO(payload)
        source._catalog_analysis_cache = cache
        source._catalog_source_key = key
        result[key] = source
    return result


def _produce(data, shot, definition, shot_bytes, seeds, services, timings, stopped, processing_gate):
    from dataclasses import replace
    from fabricapp.catalog_engine.runner import generate_shot
    with timed_stage('catalog_shot_generate', **timings):
        with processing_gate if shot.operation in ('swatch_composite', 'product_source', 'crop') else nullcontext():
            generation = generate_shot(data, shot, definition, shot_bytes, seeds, services)
        if definition.validate_shot and not definition.validate_shot(data, shot, generation):
            if stopped.is_set():
                return None
            retry = {**data, 'seed': generation.effective_seed ^ 1, '_catalog_fabric_retry': True}
            generation = generate_shot(retry, shot, definition, shot_bytes, seeds, services)
            if not definition.validate_shot(data, shot, generation):
                raise CatalogFabricMismatch('Generated cloth does not match the supplied fabric.')
            generation = replace(generation, diagnostics={
                **(generation.diagnostics or {}), 'catalog_fabric_retry_count': 1})
    if definition.finish_shot:
        with timed_stage('catalog_shot_finish', **timings):
            with processing_gate:
                generation = definition.finish_shot(data, shot, generation)
    return generation


def _upload(payload, services, timings):
    with timed_stage('catalog_shot_upload', **timings):
        return services.upload(payload)


def _failure(shot, exc):
    return {'event': 'image_failed', 'view': shot.key,
            'error': getattr(exc, 'failure_type', None) or 'image_generation_or_upload_failed',
            'provider_code': getattr(exc, 'provider_code', None),
            'generation': getattr(exc, 'diagnostics', None)}


def generate_catalog(data, stopped, services, definition=None):
    definition = definition or get_request_definition(data)
    layout = validate_definition(definition, data.get('catalog_product'))
    catalog_id = uuid4().hex
    timings = {'catalog_id': catalog_id, 'catalog_edition': definition.edition,
               'garment': data.get('garment_type'), 'style': data.get('garment_style')}
    with timed_stage('catalog_total', **timings):
        yield from _run(data, stopped, services, definition, layout, timings)


def _run(data, stopped, services, definition, layout, timings):
    plan = definition.shots
    views = [shot.key for shot in plan]
    yield {'event': 'started', 'catalog_id': timings['catalog_id'], 'total': len(plan),
           'views': views, 'catalog_edition': definition.edition, 'layout': layout.version}
    if stopped.is_set():
        return
    snapshots = _snapshot(data)
    cache = AnalysisCache()
    processing_gate = Lock()
    workers = max(1, min(2, getattr(settings, 'CATALOG_GENERATION_WORKERS', 2)))
    pending = list(range(len(plan)))
    producing, uploading, events = {}, {}, {}
    shot_bytes, seeds, images = {}, {}, []
    generation_failed, failed = set(), []
    blocked, first_resolved, next_delivery = False, False, 0

    # Keep the slot occupied until any already-started call finishes on cancel.
    # At most two generation/processing jobs and one upload are active.
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='catalog-shot') as pool, \
            ThreadPoolExecutor(max_workers=1, thread_name_prefix='catalog-upload') as uploads:
        while pending or producing or uploading:
            if stopped.is_set():
                for future in (*producing, *uploading):
                    future.cancel()
                return
            for index in list(pending):
                shot = plan[index]
                missing = [key for key in shot.dependencies if key not in shot_bytes]
                if blocked or any(key in generation_failed for key in missing):
                    pending.remove(index)
                    generation_failed.add(shot.key)
                    events[index] = {'event': 'image_failed', 'view': shot.key,
                                     'error': 'generation_unavailable' if blocked else
                                     'front_reference_failed' if 'front' in missing else 'dependency_failed',
                                     'missing_dependencies': missing}
                    continue
                if len(producing) >= workers or (index and not first_resolved) or missing:
                    continue
                pending.remove(index)
                yield {'event': 'generating', 'view': shot.key, 'index': index + 1, 'total': len(plan)}
                stage = {**timings, 'view': shot.key, 'operation': shot.operation}
                future = pool.submit(_produce, _job_data(data, snapshots, cache), shot,
                                     definition, dict(shot_bytes), dict(seeds), services, stage, stopped, processing_gate)
                producing[future] = index

            if producing or uploading:
                done, _ = wait((*producing, *uploading), timeout=.1, return_when=FIRST_COMPLETED)
                for future in sorted(done, key=lambda f: producing.get(f, uploading.get(f))):
                    if future in producing:
                        index = producing.pop(future)
                        shot = plan[index]
                        first_resolved = first_resolved or index == 0
                        try:
                            generation = future.result()
                            if generation is None or stopped.is_set():
                                return
                            # Dependencies use local bytes, independent of upload completion.
                            shot_bytes[shot.key] = generation.image_bytes
                            seeds[shot.key] = generation.effective_seed
                            stage = {**timings, 'view': shot.key, 'operation': shot.operation}
                            upload = uploads.submit(_upload, generation.image_bytes, services, stage)
                            uploading[upload] = index
                            events[index] = {'event': 'pending_upload', 'image': {
                                'view': shot.key, 'operation': shot.operation,
                                'generation_seed': generation.effective_seed,
                                'generation': generation.diagnostics, 'framing': shot.framing,
                                'reference_role': shot.reference_role if shot.reference else None,
                                'reference_template': shot.reference.name if shot.reference else None}}
                        except Exception as exc:
                            logger.exception('Catalog shot failed: %s', shot.key)
                            generation_failed.add(shot.key)
                            events[index] = _failure(shot, exc)
                            failure = getattr(exc, 'failure_type', None)
                            blocked = blocked or failure in ('allocation_exhausted', 'authentication_error') or (
                                isinstance(exc, CloudflareGenerationError) and exc.status_code in (401, 403, 429))
                    else:
                        index = uploading.pop(future)
                        try:
                            uploaded = future.result()
                            events[index] = {'event': 'image_ready',
                                             'image': {**events[index]['image'], **uploaded}}
                        except Exception as exc:
                            logger.exception('Catalog upload failed: %s', plan[index].key)
                            events[index] = _failure(plan[index], exc)
            # Clients receive stable panel ordering even if work finishes out of order.
            while next_delivery in events and events[next_delivery]['event'] != 'pending_upload':
                event = events.pop(next_delivery)
                if event['event'] == 'image_ready':
                    images.append(event['image'])
                    event.update(completed=len(images), total=len(plan))
                else:
                    failed.append(plan[next_delivery].key)
                next_delivery += 1
                yield event

    if stopped.is_set():
        return
    collage, collage_error = None, None
    if not failed:
        yield {'event': 'composing'}
        try:
            swatch = snapshots.get('fabric_image', b'') if layout.swatch_box else b''
            with timed_stage('catalog_collage_render', **timings):
                payload = render_catalog(shot_bytes, swatch, layout)
            with timed_stage('catalog_collage_upload', **timings):
                uploaded = services.upload(payload)
            collage = {**uploaded, 'view': 'catalog', 'layout': layout.version,
                       'width': layout.size[0], 'height': layout.size[1],
                       'aspect_ratio': f'{layout.size[0] // gcd(*layout.size)}:{layout.size[1] // gcd(*layout.size)}',
                       'source_views': views, 'includes_original_swatch': layout.swatch_box is not None}
            yield {'event': 'collage_ready', 'image': collage}
        except Exception:
            logger.exception('Catalog composition or upload failed')
            collage_error = 'collage_composition_or_upload_failed'
    else:
        collage_error = 'required_views_missing'
    yield {'event': 'complete', 'status': 'completed' if collage else ('partial' if images else 'failed'),
           'catalog_id': timings['catalog_id'], 'catalog_edition': definition.edition,
           'images': images, 'failed_views': failed, 'total': len(plan),
           'collage': collage, 'collage_error': collage_error}
