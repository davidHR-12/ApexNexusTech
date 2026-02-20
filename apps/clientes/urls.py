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
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('mis-pedidos/<int:pedido_id>/', views.detalle_pedido_cliente, name='detalle_pedido'),
    path("perfil/", views.mi_perfil, name="perfil"),
    path("crear-pedido/<int:variante_id>/", views.crear_pedido_catalogo, name="crear_pedido_catalogo"),
    path("solicitar/", views.solicitar_cotizacion, name="solicitar_cotizacion"),
    path("checkout/", views.checkout_paso_final, name="checkout_express"),
    path('carrito/actualizar/<int:variante_id>/<str:accion>/', views.actualizar_carrito, name='actualizar_carrito'),
    path("carrito/agregar/<int:variante_id>/", views.agregar_al_carrito, name="agregar_al_carrito"),
    # Se corrige el 'name' para que coincida con el redirect de la vista
    path("checkout/confirmacion/", views.pedido_confirmado_invitado, name="pedido_confirmado_invitado"),
]