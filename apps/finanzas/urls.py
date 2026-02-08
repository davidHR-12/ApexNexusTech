from django.urls import path
from . import views

app_name = "finanzas"

urlpatterns = [
    path("gastos/", views.gastos_list, name="gastos"),
    path("gastos/crear/", views.crear_gasto, name="crear_gasto"),
    path('gastos/editar/<int:gasto_id>/', views.editar_gasto, name='editar_gasto'),
    path("gastos/api/<int:gasto_id>/", views.gasto_detalle_api, name="gasto_detalle_api"),
]