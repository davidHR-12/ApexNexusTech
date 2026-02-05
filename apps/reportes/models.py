"""
Modelos para reportes y analytics (opcional)

Esta app principalmente contendrá vistas y lógica de negocio para generar reportes.
Los modelos aquí son para guardar reportes generados o configuraciones.
"""
from django.db import models
from django.conf import settings


class ReporteGuardado(models.Model):
    """
    Permite guardar configuraciones de reportes frecuentes.
    """
    TIPOS_REPORTE = (
        ("Ventas", "Reporte de ventas"),
        ("Gastos", "Reporte de gastos"),
        ("Inventario", "Reporte de inventario"),
        ("Rentabilidad", "Análisis de rentabilidad"),
        ("Pedidos", "Reporte de pedidos"),
    )

    nombre = models.CharField(
        max_length=200,
        verbose_name="Nombre del reporte"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_REPORTE,
        verbose_name="Tipo"
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )

    # Configuración del reporte (JSON)
    configuracion = models.JSONField(
        default=dict,
        help_text="Filtros y parámetros del reporte",
        verbose_name="Configuración"
    )

    # Metadatos
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Creado por"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    es_publico = models.BooleanField(
        default=False,
        help_text="¿Otros usuarios pueden ver este reporte?",
        verbose_name="Público"
    )

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    class Meta:
        verbose_name = "Reporte Guardado"
        verbose_name_plural = "Reportes Guardados"
        ordering = ["-fecha_creacion"]


class ConfiguracionDashboard(models.Model):
    """
    Configuración personalizada del dashboard por usuario.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Usuario"
    )

    # Widgets visibles
    mostrar_ventas_dia = models.BooleanField(default=True)
    mostrar_pedidos_pendientes = models.BooleanField(default=True)
    mostrar_stock_bajo = models.BooleanField(default=True)
    mostrar_ultimos_gastos = models.BooleanField(default=True)
    mostrar_grafico_ventas = models.BooleanField(default=True)

    # Preferencias
    periodo_grafico_ventas = models.CharField(
        max_length=20,
        choices=(
            ("semana", "Última semana"),
            ("mes", "Último mes"),
            ("trimestre", "Último trimestre"),
        ),
        default="mes",
        verbose_name="Período de gráfico de ventas"
    )

    def __str__(self):
        return f"Dashboard de {self.usuario.email}"

    class Meta:
        verbose_name = "Configuración de Dashboard"
        verbose_name_plural = "Configuraciones de Dashboard"
