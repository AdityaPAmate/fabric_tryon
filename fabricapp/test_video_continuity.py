import tempfile
from pathlib import Path
from django.test import SimpleTestCase
from fabricapp.video.continuity import check_continuity
from fabricapp.video.errors import VideoError


def animation_bytes(change=None, letterbox=True, *, seconds=2):
    """Real MP4 fixture: central subject motion, optionally a peripheral change."""
    import cv2
    import numpy as np
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'sample.mp4'
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 24, (96, 128))
        if not writer.isOpened():
            raise RuntimeError('MP4 test encoder unavailable')
        try:
            for index in range(round(24 * seconds)):
                frame = np.full((128, 96, 3), (120, 130, 145), dtype=np.uint8)
                if index >= 24:
                    if change == 'cut':
                        frame[:] = (210, 70, 30)
                    elif change == 'saturation':
                        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                        hsv[:, :, 1] += 60
                        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
                    elif change == 'exposure':
                        frame += 60
                    elif change == 'small':
                        frame += 3
                # Motion stays within the centre, leaving the same background.
                x = 35 + (index % 8)
                frame[25:105, x:x + 20] = (50, 65, 90)
                if letterbox:
                    frame[:8] = 0
                    frame[-8:] = 0
                writer.write(frame)
        finally:
            writer.release()
        return path.read_bytes()


class VideoContinuityTests(SimpleTestCase):
    def check(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.mp4'
            path.write_bytes(payload)
            return check_continuity(path)

    def test_subject_motion_letterboxing_and_small_colour_noise_pass(self):
        for letterbox, change in ((True, None), (False, None), (True, 'small')):
            with self.subTest(letterbox=letterbox, change=change):
                result = self.check(animation_bytes(change, letterbox))
                self.assertEqual(result['check'], 'outer-frame-v2')
                self.assertEqual(result['status'], 'passed')
                self.assertGreater(result['samples'], 2)

    def test_scene_saturation_and_exposure_changes_require_review(self):
        for change in ('cut', 'saturation', 'exposure'):
            with self.subTest(change=change):
                result = self.check(animation_bytes(change))
                self.assertEqual(result['status'], 'review_required')
                self.assertGreater(result['samples'], 2)

    def test_mp4_header_alone_is_not_a_valid_video(self):
        with self.assertRaises(VideoError) as error:
            self.check(b'\x00\x00\x00\x18ftypisom' + b'\0' * 32)
        self.assertEqual(error.exception.code, 'invalid_video')

    def test_expected_zoom_out_is_not_certified_by_a_locked_edge_check(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sample.mp4'
            path.write_bytes(animation_bytes('cut'))
            self.assertEqual(check_continuity(path)['status'], 'review_required')
            result = check_continuity(path, camera_motion='zoom_out')
            self.assertEqual(result['status'], 'not_applicable')
            self.assertEqual(result['reason'], 'camera_motion')
            self.assertEqual(result['camera_motion'], 'zoom_out')
            # A camera-motion declaration must not bypass decode validation.
            path.write_bytes(b'\x00\x00\x00\x18ftypisom' + b'\0' * 32)
            with self.assertRaises(VideoError):
                check_continuity(path, camera_motion='zoom_out')
