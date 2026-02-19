from django.urls import path
from . import views

app_name = "productos"

urlpatterns = [
    # --- 1. RUTAS ESTÁTICAS / FIJAS (Sin variables o parámetros) ---
    path("productos/", views.product_list, name="productos_index"),

    # Crear productos base
    path("productos/nuevo/", views.crear_producto_base, name="crear_producto_base_general"),
    # Crear productos base por categoría
    path("productos/nuevo/<int:categoria_id>/", views.crear_producto_base, name="crear_producto_base"),

    # Crear categorías
    path("categorias/crear/", views.crear_categoria, name="crear_categoria"),

    # Eliminar imágenes de productos
    path("api/productos/eliminar-imagenes/", views.eliminar_imagenes_producto_bulk, name="eliminar_imagenes_producto_bulk"),
    # Reactivar múltiples productos
    path("productos/reactivar-multiples/", views.reactivar_multiples_productos, name="reactivar_multiples"),
    # Buscar material variante
    path("api/buscar-material-variante/", views.buscar_material_variante, name="buscar_material_variante"),

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
    path("productos/variante/<int:variante_id>/toggle-activo/", views.toggle_variante_activo, name="toggle_variante_activo"),
    path("productos/variantes/reactivar-multiples/", views.reactivar_multiples_variantes, name="reactivar_multiples_variantes"),
    path("productos/variante/<int:variante_id>/editar/", views.editar_variante, name="editar_variante"),
    path("productos/<int:producto_id>/variantes-archivadas/", views.obtener_variantes_archivadas, name="obtener_variantes_archivadas"),
    
    # API IDs
    path("api/productos/<int:pk>/", views.obtener_producto_json, name="obtener_producto_json"),
    path("api/categorias/<int:categoria_id>/", views.obtener_categoria_json, name="obtener_categoria_json"),
    path("api/productos/archivados/<int:categoria_id>/", views.obtener_productos_archivados, name="api_productos_archivados"),
    path("api/variante/<int:variante_id>/precio/", views.obtener_precio_variante, name="obtener_precio_variante"),
    

    # --- 3. RUTAS CON SLUG (Comodines de texto) ---
    path("productos/<str:slug>/", views.producto_detalle, name="producto_detalle"),
    path("categorias/<str:slug>/", views.categoria_detalle, name="categoria_detalle"),
]