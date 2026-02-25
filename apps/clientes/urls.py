from django.urls import path
from . import views

"""
Definición de rutas para la aplicación de clientes.
"""

app_name = "clientes"

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.home, name="home"),
    path("proceso/", views.proceso_view, name="proceso"),
    path("productos/", views.productos, name="productos"),
    path("materiales/", views.materiales_view, name="materiales"),
    path("productos/<int:pk>/", views.detalle_producto, name="detalle_producto"),
    path('mis-pedidos/', views.mis_pedidos, name='mis_pedidos'),
    path('mis-pedidos/<int:pedido_id>/', views.detalle_pedido_cliente, name='detalle_pedido'),
    path('pedido/<int:pedido_id>/pago/', views.seleccionar_metodo_pago, name='seleccionar_metodo_pago'),
    path('pedido/<int:pedido_id>/comprobante/', views.subir_comprobante, name='subir_comprobante'),
    path("configuracion/", views.configuracion_cliente, name="configuracion"),
    path("crear-pedido/<int:variante_id>/", views.crear_pedido_catalogo, name="crear_pedido_catalogo"),
    path("solicitar/", views.solicitar_cotizacion, name="solicitar_cotizacion"),
    path("checkout/", views.checkout_paso_final, name="checkout_express"),
    path('carrito/actualizar/<int:variante_id>/<str:accion>/', views.actualizar_carrito, name='actualizar_carrito'),
    path("carrito/agregar/<int:variante_id>/", views.agregar_al_carrito, name="agregar_al_carrito"),
    path("checkout/confirmacion/", views.pedido_confirmado_invitado, name="pedido_confirmado_invitado"),
]