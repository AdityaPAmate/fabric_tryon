import tempfile
from pathlib import Path
from django.test import SimpleTestCase
from fabricapp.video.continuity import check_continuity
from fabricapp.video.errors import VideoError


def animation_bytes(change=None, letterbox=True):
    """Real MP4 fixture: central subject motion, optionally a peripheral change."""
    import cv2
    import numpy as np
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'sample.mp4'
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), 24, (96, 128))
        if not writer.isOpened():
            raise RuntimeError('MP4 test encoder unavailable')
        try:
            for index in range(48):
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
                self.assertEqual(result['check'], 'outer-frame-v1')
                self.assertGreater(result['samples'], 2)

    def test_scene_saturation_and_exposure_changes_are_rejected(self):
        for change in ('cut', 'saturation', 'exposure'):
            with self.subTest(change=change), self.assertRaises(VideoError) as error:
                self.check(animation_bytes(change))
            self.assertEqual(error.exception.code, 'video_continuity_failed')
            self.assertFalse(error.exception.retryable)

    def test_mp4_header_alone_is_not_a_valid_video(self):
        with self.assertRaises(VideoError) as error:
            self.check(b'\x00\x00\x00\x18ftypisom' + b'\0' * 32)
        self.assertEqual(error.exception.code, 'invalid_video')
