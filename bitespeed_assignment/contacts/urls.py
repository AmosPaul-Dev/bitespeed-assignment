from django.urls import path
from .views import IdentifyView

urlpatterns = [
    path('', IdentifyView.as_view(), name='identify'),
]
