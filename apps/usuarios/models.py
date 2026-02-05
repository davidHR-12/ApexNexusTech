"""
Modelo de usuario personalizado para el sistema de impresión 3D
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado.
    Usa email como identificador principal en lugar de username.
    """

    # Email como identificador único para login
    email = models.EmailField(unique=True, verbose_name="Correo electrónico")

    # Username es opcional
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Nombre de usuario"
    )

    # Roles del sistema
    ROLES = (
        ("Admin", "Administrador"),
        ("Cliente", "Cliente"),
    )
    rol = models.CharField(
        max_length=10,
        choices=ROLES,
        default="Cliente",
        verbose_name="Rol"
    )

    # Campos adicionales
    telefono = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="Teléfono"
    )

    # Verificación de email
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name="Email verificado"
    )

    last_verification_email = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Último email de verificación"
    )

    # Configuramos Django para que pida el email al iniciar sesión
    USERNAME_FIELD = "email"
    # Campos que pide el comando createsuperuser aparte del email y password
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        """Auto-asignar rol de Admin a superusuarios"""
        if self.is_superuser:
            self.rol = "Admin"
            self.is_email_verified = True
        super().save(*args, **kwargs)

    def get_full_name_or_user(self):
        """Retorna nombre completo o username"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username or self.email.split('@')[0]

    def __str__(self):
        return f"{self.email} ({self.get_rol_display()})"

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["-date_joined"]
