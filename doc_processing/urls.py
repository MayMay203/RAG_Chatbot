# chat_user/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('process', DocumentProcessingView.as_view(), name='index'),
    path('toggle-active', MaterialActivationView.as_view(), name='toggle_material_active')
]