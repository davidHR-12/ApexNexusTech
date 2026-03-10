from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'reportes'

urlpatterns = [
    path('reportes/', views.dashboard, name='dashboard'),
    path('reportes/ventas/',    views.reporte_ventas,      name='ventas'),
    path('reportes/inventario/',views.reporte_inventario,  name='inventario'),
    path('reportes/ventas/exportar/',    views.exportar_ventas_excel,  name='exportar_ventas'),
    path('reportes/inventario/exportar/',views.exportar_inventario_excel, name='exportar_inventario'),


]
