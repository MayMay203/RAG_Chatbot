from django.urls import path
from .views import *

urlpatterns = [
    path('process', DocumentProcessingView.as_view(), name='index'),
    path('toggle-active', DocumentActivationView.as_view(), name='toggle_material_active'),
    path('delete-material', DocumentDeleteActionView.as_view(), name='delete-material'),
]