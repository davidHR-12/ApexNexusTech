"""
Modelos para gestión de perfiles de clientes
"""
from django.db import models
from django.conf import settings


class PerfilCliente(models.Model):
    """
    Información adicional del cliente más allá del usuario base.
    Extiende el modelo Usuario con datos específicos del negocio.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_cliente',
        verbose_name="Usuario"
    )

    # Información de contacto extendida
    empresa = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Empresa"
    )

    direccion = models.TextField(
        blank=True,
        verbose_name="Dirección"
    )

    ciudad = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ciudad"
    )

    codigo_postal = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="Código Postal"
    )

    # Información del negocio
    notas = models.TextField(
        blank=True,
        help_text="Notas internas sobre el cliente",
        verbose_name="Notas"
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro"
    )

    # Preferencias
    recibir_notificaciones = models.BooleanField(
        default=True,
        verbose_name="Recibir notificaciones por email"
    )

    def __str__(self):
        return f"Perfil de {self.usuario.email}"

    def get_direccion_completa(self):
        """Retorna la dirección formateada"""
        partes = [self.direccion, self.ciudad, self.codigo_postal]
        return ", ".join([p for p in partes if p])

    class Meta:
        verbose_name = "Perfil de Cliente"
        verbose_name_plural = "Perfiles de Clientes"
        ordering = ["-fecha_registro"]


class HistorialCliente(models.Model):
    """
    Log de interacciones importantes con el cliente
    (útil para seguimiento comercial)
    """
    TIPOS_INTERACCION = (
        ("Llamada", "Llamada telefónica"),
        ("Email", "Correo electrónico"),
        ("Reunion", "Reunión presencial"),
        ("Nota", "Nota interna"),
    )

    cliente = models.ForeignKey(
        PerfilCliente,
        on_delete=models.CASCADE,
        related_name='historial',
        verbose_name="Cliente"
    )

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_INTERACCION,
        verbose_name="Tipo de interacción"
    )

    descripcion = models.TextField(
        verbose_name="Descripción"
    )

    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha"
    )

    usuario_registra = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interacciones_registradas',
        verbose_name="Registrado por"
    )

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.cliente} ({self.fecha.date()})"

    class Meta:
        verbose_name = "Historial de Cliente"
        verbose_name_plural = "Historial de Clientes"
        ordering = ["-fecha"]
