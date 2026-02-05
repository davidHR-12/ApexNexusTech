from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

"""
Rutas de autenticación y registro de usuarios.
"""

app_name = "usuarios"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.registro_view, name="register"),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="clientes:index"),
        name="logout",
    ),
    path(
        "verificar-email/<str:uidb64>/<str:token>/",
        views.verificar_email,
        name="verificar_email",
    ),
    path(
        "reenviar-verificacion/",
        views.reenviar_verificacion,
        name="reenviar_verificacion",
    ),
]
