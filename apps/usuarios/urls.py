from django.urls import path,reverse_lazy  
from django.contrib.auth import views as auth_views
from . import views
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from .forms import CustomPasswordResetForm, CustomSetPasswordForm
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

        path(
        "reset/",
        PasswordResetView.as_view(
            template_name="usuarios/reset_password_request.html",
            form_class=CustomPasswordResetForm,
            # No usamos email_template_name porque nuestro form.send_mail lo ignora
            email_template_name="emails/reset_password.html",
            success_url=reverse_lazy("usuarios:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "reset/enviado/",
        PasswordResetDoneView.as_view(
            template_name="usuarios/reset_password_sent.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="usuarios/reset_password_confirm.html",
            form_class=CustomSetPasswordForm,
            # Tras confirmar, redirige a la página de éxito
            post_reset_login=False,
            success_url=reverse_lazy("usuarios:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/listo/",
        PasswordResetCompleteView.as_view(
            template_name="usuarios/reset_password_complete.html",
        ),
        name="password_reset_complete",
    ),
]

