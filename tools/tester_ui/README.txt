Fabric TryOn Tester - optional video

Run the existing server.py to serve this UI on http://localhost:5500.
Choose Single image, Catalog, or Generate video. Existing image settings stay available.
Set the backend API URL; video also requires its VIDEO_API_TOKEN (not GIMMECLIP_API_KEY).
Video mode generates the selected photo first, then an 8-second video.
The live total timer and video generation timer appear above the result.
Use Make video from this image to animate a selected generated photo without regenerating it.
Stop waiting cancels polling only. Inspect/resume the saved job UUID against the same backend.
Retry reuses saved work when the backend marks the failure retryable.

Backend setup and API details: Desktop/fabric_tryon/docs/video_generation.md.
