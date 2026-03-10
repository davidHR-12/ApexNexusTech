from django.urls import path
from . import views

app_name = "pedidos"

urlpatterns = [
    path("pedidos/", views.pedidos_list, name="pedidos_lista"),
    path('pedidos/<int:pedido_id>/', views.pedido_detalle, name='pedido_detalle'),

    # Acciones de ítems
    path('pedidos/crear/', views.crear_pedido_manual, name='crear_pedido'),
    path('pedidos/<int:pedido_id>/agregar-item/', views.agregar_item_pedido, name='agregar_item'),
    path('pedidos/item/<int:item_id>/editar/', views.editar_item_pedido, name='editar_item'),
    path('pedidos/item/<int:item_id>/eliminar/', views.eliminar_item_pedido, name='eliminar_item'),
    path('pedidos/<int:pedido_id>/cambiar-estado/', views.cambiar_estado_pedido, name='cambiar_estado'),
    path('pedidos/item/<int:item_id>/asignar-impresora/', views.asignar_impresora_item, name='asignar_impresora'),

    # Notas
    path('pedido/<int:pedido_id>/notas/agregar/', views.agregar_nota_pedido, name='agregar_nota_pedido'),
    path('pedido/<int:pedido_id>/notas/modal/', views.editar_notas_modal, name='editar_notas_modal'),
    path('pedido/<int:pedido_id>/notas/guardar/', views.guardar_notas, name='editar_notas'),

    # ── PAGOS (NUEVAS) ──────────────────────────────────────────
    path('pedidos/<int:pedido_id>/registrar-pago/', views.registrar_pago, name='registrar_pago'),
    path('pedidos/<int:pedido_id>/comprobante/revisar/', views.revisar_comprobante, name='revisar_comprobante'),
    # ────────────────────────────────────────────────────────────

    # ── FALLOS DE IMPRESIÓN (NUEVAS) ──────────────────────────
    path('pedidos/<int:pedido_id>/registrar-fallo/', views.registrar_fallo_impresion, name='registrar_fallo'),
    # ────────────────────────────────────────────────────────────

    # ── FACTURAS ───────────────────────────────────────────────
    path('pedidos/<int:pedido_id>/factura/', views.generar_factura_pdf, name='generar_factura'),
    # ────────────────────────────────────────────────────────────

    # Solicitudes
    path('solicitudes/', views.solicitudes_list, name='solicitudes_list'),
    path('solicitudes/convertir/<int:solicitud_id>/', views.convertir_solicitud_a_pedido, name='convertir_solicitud'),
    path('solicitudes/<int:solicitud_id>/rechazar/', views.rechazar_solicitud, name='rechazar_solicitud'),
]