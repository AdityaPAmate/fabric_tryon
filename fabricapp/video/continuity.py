"""Conservative outer-frame drift check, not a garment/identity quality score.

For a locked camera, the image edges should stay still while the central person
turns. Sample at 4 Hz, ignore letterboxing and compare blurred edge colours with
the first frame. Reject sustained large changes; small motion/compression passes.
This heuristic can miss subtle changes and can reject subjects moving at edges.
"""
from .errors import VideoError


def check_continuity(path):
    import cv2
    import numpy as np

    def invalid():
        return VideoError('invalid_video', 'Video could not be decoded as a short animation.', True)

    def descriptor(frame, box):
        y0, y1, x0, x1 = box
        small = cv2.resize(frame[y0:y1, x0:x1], (64, 64))
        small = cv2.GaussianBlur(small, (9, 9), 0)
        edges = np.concatenate((small[:, :12], small[:, -12:]), axis=1)
        return (edges.astype(float),
                cv2.cvtColor(edges, cv2.COLOR_BGR2HSV).astype(float),
                cv2.cvtColor(edges, cv2.COLOR_BGR2LAB).astype(float))

    cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG)
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        width, height = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if not (1 <= fps <= 120 and 1 <= count / fps <= 12 and
                0 < width * height <= 4096 * 4096):
            raise invalid()
        ok, first = cap.read()
        if not ok:
            raise invalid()
        lit = first.max(axis=2) > 12
        rows = np.flatnonzero(lit.mean(axis=1) > .1)
        cols = np.flatnonzero(lit.mean(axis=0) > .1)
        if not len(rows) or not len(cols):
            raise invalid()
        box = (rows[0], rows[-1] + 1, cols[0], cols[-1] + 1)
        baseline = descriptor(first, box)
        step = max(1, round(fps / 4))
        streak, samples, decoded = 0, 1, 1
        max_rgb = max_saturation = 0.0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            index = decoded
            decoded += 1
            if decoded > 1440 or frame.shape != first.shape:
                raise invalid()
            if index % step:
                continue
            rgb, hsv, lab = descriptor(frame, box)
            rgb_change = float(np.median(np.abs(rgb - baseline[0]).mean(axis=2)))
            saturation = float(np.median(np.abs(hsv[:, :, 1] - baseline[1][:, :, 1])))
            chroma = float(np.median(np.linalg.norm(lab[:, :, 1:] - baseline[2][:, :, 1:], axis=2)))
            max_rgb = max(max_rgb, rgb_change)
            max_saturation = max(max_saturation, saturation)
            samples += 1
            changed = rgb_change > 18 or (saturation >= 15 and chroma >= 5)
            streak = streak + 1 if changed else 0
            if streak >= 2:
                raise VideoError('video_continuity_failed',
                    'Video quality check detected a background or lighting change. '
                    'Your generated image is saved. Make a new video from that image.')
        if decoded < count - 2 or samples < 2:
            raise invalid()
        return {'check': 'outer-frame-v1', 'samples': samples,
                'max_rgb_change': round(max_rgb, 2),
                'max_saturation_change': round(max_saturation, 2)}
    finally:
        cap.release()
