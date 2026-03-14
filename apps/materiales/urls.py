from django.urls import path
from . import views

app_name = "materiales"

urlpatterns = [
    # --- 1. RUTAS ESTÁTICAS / FIJAS ---
    path("materiales/", views.material_list, name="lista_materiales"),
    path("materiales/nuevo/", views.crear_material, name="crear_material"),
    path("materiales/registro-entrada/", views.registrar_entrada, name="registrar_entrada"),
    
    # API AJAX (Fijas)
    path("materiales/buscar-material-ajax/", views.buscar_material_ajax, name="buscar_material_ajax"),
    path("materiales/buscar-atributo-ajax/", views.buscar_atributo_ajax, name="buscar_atributo_ajax"),

    # --- 2. RUTAS CON ID (Números) ---
    # Gestión de Materiales
    path("materiales/<int:material_id>/editar/", views.editar_material, name="editar_material"),
    path("materiales/<int:material_id>/eliminar/", views.eliminar_material, name="eliminar_material"),
    path("materiales/<int:material_id>/toggle-activo/", views.toggle_material_activo, name="toggle_material_activo"),
    
    # Atributos (Marcas, Colores, Tipos)
    path("materiales/gestionar-atributo/<str:modelo_tipo>/<int:objeto_id>/", views.gestionar_atributo, name="gestionar_atributo"),
    path("materiales/atributos/<str:tipo_atrib>/<int:id_atrib>/eliminar/", views.eliminar_atributo, name="eliminar_atributo"),

    # API IDs (JSON
    path("api/materiales/<int:material_id>/", views.obtener_material_json, name="obtener_material_json"),
    path("api/materiales/<int:material_id>/precio/", views.obtener_precio_material, name="obtener_precio_material"),
    path("materiales/api/archivados/", views.obtener_materiales_archivados,  name="materiales_archivados"),
]