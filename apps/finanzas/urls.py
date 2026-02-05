from django.urls import path
from . import views

app_name = "finanzas"

urlpatterns = [
    path("gastos/", views.gastos_list, name="gastos"),
    path("gastos/crear/", views.crear_gasto, name="crear_gasto"),
]