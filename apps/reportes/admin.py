# apps/reportes/admin.py
from django.contrib import admin
from .models import ReporteGuardado, ConfiguracionDashboard


@admin.register(ReporteGuardado)
class ReporteGuardadoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "usuario", "es_publico", "fecha_creacion")
    list_filter = ("tipo", "es_publico", "fecha_creacion")
    search_fields = ("nombre", "descripcion", "usuario__email")
    ordering = ("-fecha_creacion",)
    readonly_fields = ("fecha_creacion",)


@admin.register(ConfiguracionDashboard)
class ConfiguracionDashboardAdmin(admin.ModelAdmin):
    list_display = ("usuario", "periodo_grafico_ventas", "mostrar_ventas_dia", "mostrar_pedidos_pendientes")
    search_fields = ("usuario__email",)