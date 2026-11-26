from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase
from fabricapp.video.errors import VideoError
from fabricapp.video.storage import validate_download_url, store_video
from fabricapp.test_video_continuity import animation_bytes

VIDEO = 'https://gimmeclip.com/api/v0/clips/' + 'c' * 64 + '/file'

class VideoStorageTests(SimpleTestCase):
    def test_only_provider_clip_endpoint_is_accepted(self):
        validate_download_url(VIDEO)
        for url in ['https://localhost/video.mp4', 'http://gimmeclip.com/video.mp4', 'https://cdn.example/video.mp4']:
            with self.subTest(url=url), self.assertRaises(VideoError):
                validate_download_url(url)

    def response(self, payload):
        response = MagicMock()
        response.status_code = 200
        response.iter_content.return_value = [payload]
        response.__enter__.return_value = response
        return response

    def test_streams_mp4_to_stable_cloudinary_id(self):
        response = self.response(animation_bytes())
        with patch('fabricapp.video.storage.GimmeclipClient') as client, \
             patch('fabricapp.video.storage.cloudinary.uploader.upload', return_value={'secure_url': 'https://cdn.example/stored.mp4'}) as upload:
            client.return_value.download.return_value = response
            result = store_video(VIDEO, 'test-job')
        self.assertEqual(result['url'], 'https://cdn.example/stored.mp4')
        self.assertEqual(upload.call_args.kwargs['resource_type'], 'video')
        self.assertEqual(upload.call_args.kwargs['public_id'], 'test-job')
        client.return_value.download.assert_called_once_with(VIDEO)
        self.assertEqual(result['continuity']['check'], 'outer-frame-v2')
        for stage in ('download_seconds', 'validation_seconds', 'render_seconds', 'final_upload_seconds'):
            self.assertGreaterEqual(result['timing'][stage], 0)

    def test_scene_drift_is_available_for_review_without_altering_the_clip(self):
        payload = animation_bytes('saturation')
        with patch('fabricapp.video.storage.GimmeclipClient') as client, \
             patch('fabricapp.video.storage.cloudinary.uploader.upload') as upload:
            client.return_value.download.return_value = self.response(payload)
            seen = []
            def store(content, **kwargs):
                seen.append(content.read())
                return {'secure_url':'https://cdn.example/review.mp4'}
            upload.side_effect = store
            result = store_video(VIDEO, 'test-job')
        self.assertEqual(result['continuity']['status'], 'review_required')
        self.assertEqual(result['url'], 'https://cdn.example/review.mp4')
        self.assertEqual(seen, [payload])

    def test_zoom_out_plan_preserves_clip_bytes_and_reports_check_as_not_applicable(self):
        payload = animation_bytes('saturation')
        seen = []
        with patch('fabricapp.video.storage.GimmeclipClient') as client, \
             patch('fabricapp.video.storage.cloudinary.uploader.upload') as upload:
            client.return_value.download.return_value = self.response(payload)
            def store(content, **kwargs):
                seen.append(content.read())
                return {'secure_url': 'https://cdn.example/catwalk.mp4'}
            upload.side_effect = store
            result = store_video(VIDEO, 'catwalk-job', profile={'camera_motion': 'zoom_out'})
        self.assertEqual(result['continuity']['status'], 'not_applicable')
        self.assertEqual(result['continuity']['reason'], 'camera_motion')
        self.assertEqual(seen, [payload])

    def test_html_output_is_not_uploaded(self):
        with patch('fabricapp.video.storage.GimmeclipClient') as client, \
             patch('fabricapp.video.storage.cloudinary.uploader.upload') as upload:
            client.return_value.download.return_value = self.response(b'<html>bad gateway</html>')
            with self.assertRaises(VideoError) as caught:
                store_video(VIDEO, 'test-job')
        self.assertEqual(caught.exception.code, 'invalid_video')
        upload.assert_not_called()
