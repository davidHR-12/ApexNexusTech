from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'core'

urlpatterns = [
    path("", lambda request: redirect("dashboard/", permanent=False)),

    # Dashboard y generales
    path("dashboard/", views.dashboard_admin, name="dashboard_admin"),
    path('calculadora/', views.calculadora, name='calculadora'),
    path('calculadora/calcular/', views.calcular_ajax, name='calcular_ajax'),

    # Configuración
    path("configuracion/", views.configuracion, name="configuracion"),
    path("configuracion/media/", views.gestionar_media_huerfana, name="config_media"),
    path("configuracion/impresoras/", views.lista_impresoras, name="lista_impresoras"),
    path("configuracion/impresora/<str:accion>/", views.gestionar_impresora, name="gestionar_impresora_crear"),
    path("configuracion/impresora/<str:accion>/<int:id_impresora>/", views.gestionar_impresora, name="gestionar_impresora_accion"),
    path("configuracion/cobros/", views.configuracion_pago, name="configuracion_pago"),
    path('configuracion/sitio-publico/', views.configuracion_sitio_publico, name='configuracion_sitio_publico'),
    path('configuracion/cards/crear/', views.crear_card, name='crear_card'),
    path('configuracion/cards/<int:card_id>/editar/', views.editar_card, name='editar_card'),
    path('configuracion/cards/<int:card_id>/eliminar/', views.eliminar_card, name='eliminar_card'),
    path('configuracion/cards/reordenar/', views.reordenar_cards, name='reordenar_cards'),
    path('configuracion/factura/', views.configurar_factura, name='configurar_factura'),
    path('configuracion/calculadora/', views.configurar_calculadora, name='configurar_calculadora'),
    path("configuracion/mi-perfil/", views.mi_perfil, name="mi_perfil"),
    path("configuracion/confirmar-email/<str:uidb64>/<str:token>/", views.confirmar_email_nuevo, name="confirmar_email_nuevo"),

]