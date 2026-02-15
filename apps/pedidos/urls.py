from django.urls import path
from . import views

app_name = "pedidos"

urlpatterns = [
    path("pedidos/", views.pedidos_list, name="pedidos_lista"),
    path('pedidos/<int:pedido_id>/', views.pedido_detalle, name='pedido_detalle'),

    # Acciones (Endpoints POST)
    path('pedidos/crear/', views.crear_pedido_manual, name='crear_pedido'),
    path('pedidos/<int:pedido_id>/agregar-item/', views.agregar_item_pedido, name='agregar_item'),
    path('pedidos/item/<int:item_id>/editar/', views.editar_item_pedido, name='editar_item'),
    path('pedidos/item/<int:item_id>/eliminar/', views.eliminar_item_pedido, name='eliminar_item'),
    path('pedidos/<int:pedido_id>/cambiar-estado/', views.cambiar_estado_pedido, name='cambiar_estado'),
    path('pedidos/item/<int:item_id>/asignar-impresora/', views.asignar_impresora_item, name='asignar_impresora'),
]