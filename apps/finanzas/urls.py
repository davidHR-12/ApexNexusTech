from django.urls import path
from . import views

app_name = "finanzas"

urlpatterns = [
    path("gastos/", views.gastos_list, name="gastos"),
    path("gastos/crear/", views.crear_gasto, name="crear_gasto"),
    path('gastos/dashboard/', views.dashboard_finanzas, name='dashboard_finanzas'),
    path("gastos/detalle/<int:gasto_id>/", views.gasto_detalle, name="gasto_detalle"),
    path('gastos/editar/<int:gasto_id>/', views.editar_gasto, name='editar_gasto'),
    path('gastos/eliminar/<int:gasto_id>/', views.eliminar_gasto, name='eliminar_gasto'),
    path("gastos/api/<int:gasto_id>/", views.gasto_detalle_api, name="gasto_detalle_api"),
    path('gastos/por-mes/', views.gastos_por_mes, name='gastos_por_mes'),
]