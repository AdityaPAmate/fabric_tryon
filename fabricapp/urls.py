from django.urls import path

from .views import FabricTryOnView

urlpatterns = [
    path('replace-fabric/', FabricTryOnView.as_view(), name='replace-fabric'),
]