from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'core'

urlpatterns = [
    path("", lambda request: redirect("dashboard/", permanent=False)),
    # --- DASHBOARD & GENERAL ---
    path("dashboard/", views.dashboard_admin, name="dashboard-admin"),
    path("calculadora/", views.calculadora, name="calculadora"),
    path("configuracion/", views.configuracion, name="configuracion"),
    path("configuracion/media/", views.gestionar_media_huerfana, name="config_media"),
]