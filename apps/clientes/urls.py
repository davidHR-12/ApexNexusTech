from django.urls import path
from . import views

"""
Definición de rutas para la aplicación de clientes.
"""

app_name = "clientes"

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.home, name="home"),
    path("proceso/", views.proceso, name="proceso"),
    path("productos/", views.productos, name="productos"),
    path("materiales/", views.guia_materiales, name="materiales"),
    path("productos/<int:pk>/", views.detalle_producto, name="detalle_producto"),
]
