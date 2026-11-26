from django.urls import path

from fabricapp.views import FabricTryOnView, health_check
from fabricapp.catalog import GenerateCatalogView
from django.views.generic import TemplateView

from fabricapp.video.views import GenerateTryOnVideoView, AnimateImageView, VideoJobView, RetryVideoJobView
from fabricapp.video.views import VideoOptionsView

urlpatterns = [
    path('video-options/', VideoOptionsView.as_view(), name='video-options'),
    path('generate-tryon-video/', GenerateTryOnVideoView.as_view(), name='generate-tryon-video'),
    path('animate-image/', AnimateImageView.as_view(), name='animate-image'),
    path('video-jobs/<uuid:job_id>/', VideoJobView.as_view(), name='video-job'),
    path('video-jobs/<uuid:job_id>/retry/', RetryVideoJobView.as_view(), name='retry-video-job'),
    path('generate-catalog/', GenerateCatalogView.as_view(), name='generate-catalog'),
    path('catalog/', TemplateView.as_view(template_name='fabricapp/catalog.html'), name='catalog-page'),
    path('health/', health_check, name='health-check'),
    path('replace-fabric/', FabricTryOnView.as_view(), name='replace-fabric'),
]
