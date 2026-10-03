from django.urls import path
from .views import inicio_api


urlpatterns = [
    path("", inicio_api, name="inicio-api"),
]
