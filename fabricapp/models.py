from django.db import models
import uuid


class VideoJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=24, default='queued', db_index=True)
    payload = models.JSONField(default=dict)
    inputs = models.JSONField(default=dict)
    image_file = models.CharField(max_length=500, blank=True)
    image = models.JSONField(default=dict)
    source_photo_url = models.URLField(max_length=2000, blank=True)
    timing = models.JSONField(default=dict)
    polling_url = models.URLField(max_length=2000, blank=True)
    provider_video_url = models.URLField(max_length=2000, blank=True)
    video = models.JSONField(default=dict)
    motion_profile = models.JSONField(default=dict)
    profile_version = models.CharField(max_length=80)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=300, blank=True)
    provider_error = models.JSONField(default=dict, blank=True)
    retryable = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
