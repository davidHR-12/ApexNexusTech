from django.urls import path
from . import views

app_name = "productos"

urlpatterns = [
    # --- 1. RUTAS ESTÁTICAS / FIJAS (Sin variables o parámetros) ---
    path("productos/", views.product_list, name="productos_index"),
    path("productos/nuevo/", views.crear_producto_base, name="crear_producto_base"),
    path("categorias/crear/", views.crear_categoria, name="crear_categoria"),
    path("api/productos/eliminar-imagenes/", views.eliminar_imagenes_producto_bulk, name="eliminar_imagenes_producto_bulk"),
    path("productos/reactivar-multiples/", views.reactivar_multiples_productos, name="reactivar_multiples"),

    # --- 2. RUTAS CON ID (Números) ---
    # Productos
    path("productos/<int:producto_id>/editar/", views.editar_producto_base, name="editar_producto_base"),
    path("productos/<int:producto_id>/eliminar/", views.eliminar_producto_base, name="eliminar_producto_base"),
    path("productos/<int:producto_id>/reactivar/", views.reactivar_producto, name="reactivar_producto"),


    # Categorías
    path("categorias/<int:categoria_id>/editar/", views.editar_categoria, name="editar_categoria"),
    path("categorias/<int:categoria_id>/eliminar/", views.eliminar_categoria, name="eliminar_categoria"),

    # Variantes y Producción
    path("variantes/crear/<int:producto_id>/", views.crear_variante, name="crear_variante"),
    path("variantes/registrar/<int:variante_id>/", views.registrar_produccion, name="registrar_produccion"),
    path("variantes/obtener/<int:producto_id>/", views.obtener_variantes_producto, name="obtener_variantes_producto"),
    path("variantes/eliminar/<int:variante_id>/", views.eliminar_variante_json, name="eliminar_variante_json"),
    
    # API IDs
    path("api/productos/<int:pk>/", views.obtener_producto_json, name="obtener_producto_json"),
    path("api/categorias/<int:categoria_id>/", views.obtener_categoria_json, name="obtener_categoria_json"),
    path("api/productos/archivados/<int:categoria_id>/", views.obtener_productos_archivados, name="api_productos_archivados"),

    # --- 3. RUTAS CON SLUG (Comodines de texto) ---
    path("productos/<str:slug>/", views.producto_detalle, name="producto_detalle"),
    path("categorias/<str:slug>/", views.categoria_detalle, name="categoria_detalle"),
]