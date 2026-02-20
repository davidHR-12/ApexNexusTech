# apps/usuarios/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("email", "get_full_name_or_user", "rol", "is_email_verified", "is_manual", "is_active", "date_joined")
    list_filter = ("rol", "is_email_verified", "is_manual", "is_active", "is_superuser")
    search_fields = ("email", "first_name", "last_name", "username")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_login", "last_verification_email")

    fieldsets = (
        ("Credenciales", {"fields": ("email", "username", "password")}),
        ("Información personal", {"fields": ("first_name", "last_name", "telefono")}),
        ("Rol y estado", {"fields": ("rol", "is_active", "is_manual", "is_email_verified")}),
        ("Permisos", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("date_joined", "last_login", "last_verification_email")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "rol"),
        }),
    )