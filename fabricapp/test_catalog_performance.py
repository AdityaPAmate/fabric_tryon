"""Bounded overlap, request isolation and pixel-equivalent speed changes."""
import io
import threading
import time
from dataclasses import replace
from unittest.mock import Mock, patch

import numpy as np
from django.test import SimpleTestCase, override_settings
from PIL import Image

from fabricapp.ai.fabric.analysis_cache import AnalysisCache
from fabricapp.ai.fabric.fabric_colour import measure_fabric_colours, _measure_fabric_colours
from fabricapp.ai.providers.cloudflare_engine import GenerationResult, CloudflareGenerationError
from fabricapp.catalog_engine.contracts import CatalogDefinition, Shot, Layout, Panel
from fabricapp.catalog_engine.runner import generate_catalog, Services
from fabricapp.catalog_engine.registry import get_definition
from fabricapp.catalog_engine.renderer import render_catalog
from fabricapp.catalog_engine.swatch_composite import render_swatch_shot
from fabricapp.test_catalog_engine import data, picture


@override_settings(CATALOG_PERFORMANCE_ENABLED=True, CATALOG_GENERATION_WORKERS=2)
class CatalogSchedulingTests(SimpleTestCase):
    def definition(self):
        shots = tuple(Shot(key, key, 'pipeline', key,
                           dependencies=() if key == 'front' else ('front',), camera_view=key)
                      for key in ('front', 'side', 'back'))
        return CatalogDefinition('shirt', 'speed-test', shots, lambda *args: {},
            lambda _: Layout('speed-test', (288, 128),
                              tuple(Panel(key, (i*96, 0, (i+1)*96, 128), 'cover')
                                    for i, key in enumerate(('front', 'side', 'back')))))

    def test_independent_jobs_overlap_with_separate_streams_and_ordered_delivery(self):
        barrier = threading.Barrier(2)
        side_started = threading.Event()
        back_finished = threading.Event()
        front_generated = threading.Event()
        active, maximum = 0, 0
        lock = threading.Lock()
        calls = []
        def generate(**kwargs):
            nonlocal active, maximum
            view = kwargs['camera_view']
            if view == 'front':
                front_generated.set()
                return GenerationResult(picture(), 42)
            self.assertTrue(front_generated.is_set())
            source = kwargs['fabric_image']
            offset = 2 if view == 'side' else 5
            source.seek(offset)
            with lock:
                active += 1; maximum = max(maximum, active)
            barrier.wait(timeout=5)
            self.assertEqual(source.tell(), offset)
            if view == 'side':
                side_started.set()
                self.assertTrue(back_finished.wait(5))
                time.sleep(.02)
            else:
                back_finished.set()
            with lock:
                active -= 1; calls.append(view)
            return GenerationResult(picture(view == 'side' and 'blue' or 'green'), 42)
        def upload(payload):
            if not side_started.is_set():
                self.assertTrue(side_started.wait(5), 'Next generation must overlap front upload')
            return {'url': 'https://example.test/image.png'}
        original = data(garment_type='shirt')
        original['fabric_image'].seek(7)
        with patch('fabricapp.catalog_engine.runner.get_request_definition', return_value=self.definition()):
            events = list(generate_catalog(original, threading.Event(), Services(generate, None, upload)))
        self.assertEqual(events[-1]['status'], 'completed')
        self.assertEqual(maximum, 2)
        self.assertEqual(calls, ['back', 'side'])
        self.assertEqual([e['image']['view'] for e in events if e['event'] == 'image_ready'], ['front', 'side', 'back'])
        self.assertEqual(original['fabric_image'].tell(), 7)

    def test_first_quota_failure_does_not_start_speculative_calls(self):
        generate = Mock(side_effect=CloudflareGenerationError('quota', status_code=429))
        with patch('fabricapp.catalog_engine.runner.get_request_definition', return_value=self.definition()):
            events = list(generate_catalog(data(), threading.Event(), Services(generate, None, Mock())))
        generate.assert_called_once()
        self.assertEqual(events[-1]['status'], 'failed')
        self.assertEqual(events[-1]['failed_views'], ['front', 'side', 'back'])

    def test_cancel_during_first_generation_stops_following_jobs(self):
        stopped = threading.Event()
        def generate(**kwargs):
            stopped.set()
            return GenerationResult(picture(), 42)
        provider = Mock(side_effect=generate)
        with patch('fabricapp.catalog_engine.runner.get_request_definition', return_value=self.definition()):
            list(generate_catalog(data(), stopped, Services(provider, None, Mock())))
        provider.assert_called_once()


class CatalogAnalysisCacheTests(SimpleTestCase):
    def source(self, cache, colour='blue'):
        source = io.BytesIO(picture(colour))
        source._catalog_analysis_cache = cache
        source._catalog_source_key = 'fabric_image'
        return source

    def test_reuse_is_scoped_to_request_parameters_and_does_not_share_mutations(self):
        cache = AnalysisCache()
        first, second = self.source(cache), self.source(cache)
        first.seek(7); second.seek(11)
        with patch('fabricapp.ai.fabric.fabric_colour._measure_fabric_colours', wraps=_measure_fabric_colours) as measured:
            one = measure_fabric_colours(first)
            one['colours'][0]['name'] = 'caller mutation'
            two = measure_fabric_colours(second)
            self.assertNotEqual(two['colours'][0]['name'], 'caller mutation')
            self.assertEqual(measured.call_count, 1)
            measure_fabric_colours(second, palette_size=24)
            self.assertEqual(measured.call_count, 2)
            red = measure_fabric_colours(self.source(AnalysisCache(), 'red'))
            self.assertNotEqual(red['colours'][0]['hex'], two['colours'][0]['hex'])
        self.assertEqual(first.tell(), 7); self.assertEqual(second.tell(), 11)


class CatalogLosslessSpeedTests(SimpleTestCase):
    def assert_same_pixels(self, before, after):
        with Image.open(io.BytesIO(before)) as a, Image.open(io.BytesIO(after)) as b:
            self.assertEqual(a.size, b.size)
            self.assertEqual(a.convert('RGB').tobytes(), b.convert('RGB').tobytes())

    def test_render_and_composite_pixels_match_rollback_mode_for_different_fabrics(self):
        definition = get_definition('blazer', 'business-v1')
        shot = next(s for s in definition.shots if s.operation == 'swatch_composite')
        for colour in ('teal', 'ivory', 'pattern'):
            if colour == 'pattern':
                pixels = np.zeros((128, 96, 3), dtype=np.uint8)
                pixels[:] = (50, 90, 120)
                pixels[::4] = (220, 60, 80)
                pixels[:, ::7] = (200, 190, 90)
                buffer = io.BytesIO(); Image.fromarray(pixels).save(buffer, 'PNG')
                fabric = buffer.getvalue()
            else:
                fabric = picture(colour)
            request = data(fabric_image=io.BytesIO(fabric), garment_type='blazer')
            with override_settings(CATALOG_PERFORMANCE_ENABLED=False):
                original = render_swatch_shot(request, shot, np.array([40, 100, 120]))
            with override_settings(CATALOG_PERFORMANCE_ENABLED=True):
                changed = render_swatch_shot(request, shot, np.array([40, 100, 120]))
                repeated = render_swatch_shot(request, shot, np.array([40, 100, 120]))
            self.assert_same_pixels(original.image_bytes, changed.image_bytes)
            self.assert_same_pixels(changed.image_bytes, repeated.image_bytes)
        layout = Layout('encoding', (96, 128), (Panel('front', (0, 0, 96, 128)),))
        with override_settings(CATALOG_PERFORMANCE_ENABLED=False):
            original = render_catalog({'front': picture()}, b'', layout)
        with override_settings(CATALOG_PERFORMANCE_ENABLED=True):
            changed = render_catalog({'front': picture()}, b'', layout)
        self.assert_same_pixels(original, changed)

    @override_settings(CATALOG_PERFORMANCE_ENABLED=False)
    def test_rollback_flag_selects_previous_executor(self):
        with patch('fabricapp.catalog_engine.runner.generate_catalog_serial', return_value=iter([{'event': 'old'}])) as old:
            self.assertEqual(list(generate_catalog({}, threading.Event(), Services(None, None, None))), [{'event': 'old'}])
        old.assert_called_once()
