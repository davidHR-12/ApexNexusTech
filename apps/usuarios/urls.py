from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "usuarios"

urlpatterns = [
    # --- 1. FLUJO DE ACCESO ---
    path("acceder/", views.login_view, name="login"),
    path("registro/", views.registro_view, name="register"),
    path("salir/", auth_views.LogoutView.as_view(next_page="clientes:index"), name="logout"),

    # --- 2. FLUJO DE VERIFICACIÓN ---
    path("verificar-email/<str:uidb64>/<str:token>/",views.verificar_email, name="verificar_email"),
    path("reenviar-verificacion/",views.reenviar_verificacion,name="reenviar_verificacion"),

    # --- 3. API CLIENTES EXPRESS ---
    path('api/crear-cliente-express/', views.api_crear_cliente_express, name='api_crear_cliente_express'),
]
