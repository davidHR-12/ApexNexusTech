from django.urls import path

from .views import inicio_api, ProductoCatalogoListView


urlpatterns = [
    path("", inicio_api, name="inicio-api"),
    path("productos/", ProductoCatalogoListView.as_view(), name="productos-catalogo"),
]