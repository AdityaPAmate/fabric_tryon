from django.urls import path

from .views import FabricTryOnView, health_check

urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('replace-fabric/', FabricTryOnView.as_view(), name='replace-fabric'),
]
