"""Exercise real source cropping and FFmpeg output without paid generations."""
import hashlib
from io import BytesIO
from pathlib import Path
from shutil import which
import tempfile
from unittest import skipUnless
from unittest.mock import patch

from django.test import SimpleTestCase
from PIL import Image

from fabricapp.test_video_continuity import animation_bytes
from fabricapp.video.collar import prepare_collar, render_commercial
from fabricapp.video.errors import VideoError


def source_bytes():
    image = Image.new('RGB', (400, 600))
    for x in range(400):
        image.paste((min(255, x), 170, 35), (x, 0, x + 1, 600))
    buffer = BytesIO()
    image.save(buffer, 'PNG')
    return buffer.getvalue()


class CollarCropTests(SimpleTestCase):
    def test_crop_keeps_original_pixels_and_has_horizontal_pan_margin(self):
        data = source_bytes()
        with patch('fabricapp.video.collar.find_face', return_value=(160, 60, 80, 90)):
            crop, width, bounds = prepare_collar(data)
        self.assertEqual(crop.tobytes(), Image.open(BytesIO(data)).crop(bounds).tobytes())
        self.assertGreater(crop.width, width)
        self.assertGreaterEqual(bounds[1], 60 + 90 * .75)

    def test_insufficient_or_off_frame_collar_does_not_guess_a_fixed_crop(self):
        for face in ((0, 20, 80, 90), (160, 550, 80, 90), (160, 60, 10, 15)):
            with self.subTest(face=face), \
                 patch('fabricapp.video.collar.find_face', return_value=face), \
                 self.assertRaises(VideoError) as error:
                prepare_collar(source_bytes())
            self.assertEqual(error.exception.code, 'collar_not_found')

    def test_blank_image_fails_actual_face_detection(self):
        with self.assertRaises(VideoError) as error:
            prepare_collar(source_bytes())
        self.assertEqual(error.exception.code, 'collar_not_found')


@skipUnless(which('ffmpeg'), 'FFmpeg is installed by the production Dockerfile')
class CollarRenderTests(SimpleTestCase):
    def test_eight_second_video_starts_with_real_collar_pan_then_provider_motion(self):
        import cv2
        with tempfile.TemporaryDirectory() as directory:
            provider = Path(directory) / 'provider.mp4'
            raw = animation_bytes(seconds=8)
            provider.write_bytes(raw)
            with patch('fabricapp.video.collar.find_face', return_value=(160, 60, 80, 90)):
                output, metadata = render_commercial(provider, source_bytes(), directory)
            self.assertEqual(hashlib.sha256(provider.read_bytes()).digest(), hashlib.sha256(raw).digest())
            cap = cv2.VideoCapture(str(output))
            try:
                self.assertEqual((cap.get(3), cap.get(4)), (540, 960))
                self.assertAlmostEqual(cap.get(7) / cap.get(5), 8, delta=.06)
                samples = []
                for seconds in (.1, 1.8, 2.5):
                    cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
                    ok, frame = cap.read()
                    self.assertTrue(ok)
                    samples.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)[480, 270].astype(int))
                # The opening is the source's green/gold collar, moving right
                # through the x gradient; the provider's centre is dark blue.
                self.assertGreater(samples[0][1], 150)
                self.assertLess(samples[0][2], 50)
                self.assertGreater(samples[1][0] - samples[0][0], 5)
                self.assertLess(samples[2][1], 85)
            finally:
                cap.release()
            self.assertEqual(metadata['opening_seconds'], 2)
            self.assertEqual(metadata['provider_start_seconds'], 2)

    def test_short_provider_video_is_not_padded_with_frozen_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = Path(directory) / 'short.mp4'
            provider.write_bytes(animation_bytes())
            with self.assertRaises(VideoError) as error:
                render_commercial(provider, source_bytes(), directory)
            self.assertEqual(error.exception.code, 'invalid_video')

    def test_encoder_failure_is_retryable_without_deleting_provider_clip(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            provider = Path(directory) / 'provider.mp4'
            raw = animation_bytes(seconds=8)
            provider.write_bytes(raw)
            with patch('fabricapp.video.collar.find_face', return_value=(160, 60, 80, 90)), \
                 patch('fabricapp.video.collar.subprocess.run', side_effect=subprocess.TimeoutExpired('ffmpeg', 120)), \
                 self.assertRaises(VideoError) as error:
                render_commercial(provider, source_bytes(), directory)
            self.assertEqual(error.exception.code, 'video_composition_failed')
            self.assertTrue(error.exception.retryable)
            self.assertEqual(provider.read_bytes(), raw)
