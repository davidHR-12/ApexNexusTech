from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'reportes'

urlpatterns = [
    path("", lambda request: redirect("dashboard-admin/", permanent=False)),
    path("dashboard-admin/", views.dashboard_admin, name="dashboard-admin"),

]
