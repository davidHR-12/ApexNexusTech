from django.urls import path
from . import views

app_name = "productos"

urlpatterns = [
    # --- INVENTARIO: PRODUCTOS ---
    path("inventario/productos/", views.product_list, name="lista_productos"),
    path("inventario/productos/nuevo/", views.crear_producto, name="crear_producto"),
    path(
        "inventario/productos/<int:producto_id>/editar/",
        views.editar_producto,
        name="editar_producto",
    ),
    path(
        "inventario/productos/producto/<str:slug>/",
        views.producto_detalle,
        name="producto_detalle",
    ),
    # API Productos (JSON)
    path(
        "inventario/productos/api/<int:pk>/",
        views.obtener_producto_json,
        name="obtener_producto_json",
    ),
    path(
        "inventario/productos/api/eliminar-imagen/<int:imagen_id>/",
        views.eliminar_imagen_producto,
        name="eliminar_imagen_producto",
    ),
    # --- INVENTARIO: CATEGORÍAS ---
    # Gestión de Categorías
    path(
        "inventario/productos/categorias/crear/",
        views.crear_categoria,
        name="crear_categoria",
    ),
    path(
        "inventario/productos/categorias/<int:categoria_id>/editar/",
        views.editar_categoria,
        name="editar_categoria",
    ),
    path(
        "inventario/productos/categorias/<int:categoria_id>/eliminar/",
        views.eliminar_categoria,
        name="eliminar_categoria",
    ),
    # Vistas y API Categorías
    path(
        "inventario/productos/categoria/<str:slug>/",
        views.categoria_detalle,
        name="categoria_detalle",
    ),
    path(
        "inventario/productos/categorias/api/<int:pk>/",
        views.obtener_categoria_json,
        name="obtener_categoria_json",
    ),
    # --- PRODUCCIÓN Y VARIANTES ---

    path(
        "inventario/productos/variantes/crear/",
        views.crear_variante_json,
        name="crear_variante",
    ),
    path(
        "inventario/productos/variantes/obtener/<int:producto_id>/",
        views.obtener_variantes_producto,
        name="obtener_variantes_producto",
    ),
    path(
        "inventario/productos/variantes/eliminar/<int:variante_id>/",
        views.eliminar_variante_json,
        name="eliminar_variante",
    ),
]