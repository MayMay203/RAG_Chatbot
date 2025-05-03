# chat_user/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('message', MessageView.as_view(), name='messages'),
]