from django.urls import path

from fabricapp.views import FabricTryOnView, health_check
from fabricapp.catalog import GenerateCatalogView
from django.views.generic import TemplateView

urlpatterns = [
    path('generate-catalog/', GenerateCatalogView.as_view(), name='generate-catalog'),
    path('catalog/', TemplateView.as_view(template_name='fabricapp/catalog.html'), name='catalog-page'),
    path('health/', health_check, name='health-check'),
    path('replace-fabric/', FabricTryOnView.as_view(), name='replace-fabric'),
]
