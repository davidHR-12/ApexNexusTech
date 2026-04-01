from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('reportes/', views.dashboard, name='dashboard'),
    path('reportes/ventas/', views.reporte_ventas, name='ventas'),
    path('reportes/inventario/', views.reporte_inventario, name='inventario'),
    path('reportes/ventas/exportar/', views.exportar_ventas_excel, name='exportar_ventas'),
    path('reportes/inventario/exportar/', views.exportar_inventario_excel, name='exportar_inventario'),
    path('reportes/exportar/ejecutivo/', views.exportar_reporte_ejecutivo, name='exportar_reporte_ejecutivo'),
    path('reportes/operativo/', views.reporte_operativo, name='operativo'),

]
