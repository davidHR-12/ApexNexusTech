from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'core'

urlpatterns = [
    path("", lambda request: redirect("dashboard/", permanent=False)),

    # Dashboard y generales
    path("dashboard/", views.dashboard_admin, name="dashboard_admin"),
    path("calculadora/", views.calculadora, name="calculadora"),

    # Configuración
    path("configuracion/", views.configuracion, name="configuracion"),
    path("configuracion/media/", views.gestionar_media_huerfana, name="config_media"),
    path("configuracion/impresoras/", views.lista_impresoras, name="lista_impresoras"),
    path("configuracion/impresora/<str:accion>/", views.gestionar_impresora, name="gestionar_impresora_crear"),
    path("configuracion/impresora/<str:accion>/<int:id_impresora>/", views.gestionar_impresora, name="gestionar_impresora_accion"),
    path("configuracion/cobros/", views.configuracion_pago, name="configuracion_pago"),
]