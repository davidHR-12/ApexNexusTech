from django.urls import path
from . import views

app_name = "materiales"

urlpatterns = [
    path("inventario/materiales/", views.material_list, name="lista_materiales"),
    path("inventario/materiales/nuevo/", views.crear_material, name="crear_material"),
    path(
        "inventario/materiales/<int:material_id>/editar/",
        views.editar_material,
        name="editar_material",
    ),
    path(
        "inventario/materiales/registro-entrada/",
        views.registrar_entrada,
        name="registrar_entrada",
    ),
    # API Materiales (JSON)
    path(
        "inventario/materiales/api/<int:material_id>/",
        views.obtener_material_json,
        name="obtener_material_json",
    ),
    path(
        "inventario/materiales/buscar_material_ajax/",
        views.buscar_material_ajax,
        name="buscar_material_ajax",
    ),
    path(
        "inventario/materiales/buscar_atributo_ajax/",
        views.buscar_atributo_ajax,
        name="buscar_atributo_ajax",
    ),
    path(
        "inventario/materiales/gestionar_atributo/<str:modelo_tipo>/<int:objeto_id>/",
        views.gestionar_atributo,
        name="gestionar_atributo",
    ),
]