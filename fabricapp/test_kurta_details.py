"""Real MP4 framing checks, with synthetic motion and no provider calls."""
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase
from PIL import Image

from fabricapp.video import kurta_details
from fabricapp.video.errors import VideoError
from fabricapp.video.registry import select_profile
from fabricapp.video.rendering import preflight, renderer_name


class KurtaDetailsTests(SimpleTestCase):
    def photo(self):
        output = io.BytesIO()
        Image.new('RGB', (240, 320), 'green').save(output, 'PNG')
        return output.getvalue()

    def test_region_estimates_stay_within_image_and_do_not_modify_it(self):
        image = Image.new('RGB', (1000, 1400), 'green')
        original = image.tobytes()
        with patch('fabricapp.video.kurta_details.find_face', return_value=(450, 100, 100, 130)):
            for x, y, w, h in kurta_details.detail_boxes(image):
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x + w, image.width)
                self.assertLessEqual(y + h, image.height)
        self.assertEqual(image.tobytes(), original)

    def test_preflight_checks_face_and_ffmpeg_before_provider_submission(self):
        profile = select_profile({'garment_type': 'kurta'})
        self.assertEqual(renderer_name(profile), 'kurta_details')
        with patch('fabricapp.video.kurta_details.find_face', side_effect=VideoError('collar_not_found', 'No face')), \
             patch('fabricapp.video.kurta_details.ffmpeg_path') as executable:
            with self.assertRaises(VideoError) as caught:
                preflight(profile, self.photo())
        self.assertEqual(caught.exception.code, 'kurta_details_not_found')
        executable.assert_not_called()

    def test_only_verified_padding_matching_source_aspect_is_removed(self):
        import numpy as np
        frame = np.zeros((640, 360, 3), dtype=np.uint8)
        frame[80:560] = 120
        self.assertEqual(kurta_details.content_box(frame, (300, 400)), (0, 80, 360, 480))
        frame[:] = 120
        self.assertEqual(kurta_details.content_box(frame, (300, 400)), (0, 0, 360, 640))

    def test_render_has_sleeve_then_neckline_and_eight_seconds_of_motion(self):
        import cv2
        import numpy as np
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            path = Path(directory) / 'provider.mp4'
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 24, (240, 320))
            self.assertTrue(writer.isOpened())
            try:
                for index in range(192):
                    frame = np.full((320, 240, 3), (40, 160, 40), dtype=np.uint8)
                    frame[150:280, 20:95] = (20, 20, 230)  # red sleeve region
                    frame[90:155, 95:170] = (230, 20, 20)  # blue neckline region
                    frame[290:305, 100+index%10:110+index%10] = 230
                    writer.write(frame)
            finally:
                writer.release()
            with patch('fabricapp.video.kurta_details.find_face', return_value=(100, 40, 40, 50)):
                output, meta = kurta_details.render(path, self.photo(), directory)
            self.assertEqual(meta['walk_start_seconds'], 3.5)
            capture = cv2.VideoCapture(str(output))
            try:
                self.assertEqual(capture.get(cv2.CAP_PROP_FRAME_COUNT), 192)
                self.assertEqual(capture.get(cv2.CAP_PROP_FPS), 24)
                self.assertEqual(capture.get(cv2.CAP_PROP_FRAME_WIDTH), 540)
                self.assertEqual(capture.get(cv2.CAP_PROP_FRAME_HEIGHT), 720)
                samples = []
                for second in (.5, 2.5, 7.5):
                    capture.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
                    ok, frame = capture.read()
                    self.assertTrue(ok)
                    samples.append(frame[360, 270].astype(int))
                self.assertGreater(samples[0][2], samples[0][0] + 100)
                self.assertGreater(samples[1][0], samples[1][2] + 100)
                self.assertGreater(samples[2][1], samples[2][0] + 80)
            finally:
                capture.release()
