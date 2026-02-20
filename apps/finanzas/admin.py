# apps/finanzas/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Gasto, Ingreso, PresupuestoMensual, CuentaPorCobrar


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "tipo", "monto", "fecha", "proveedor", "es_automatico", "es_recurrente")
    list_filter = ("tipo", "es_recurrente", "fecha")
    search_fields = ("descripcion", "proveedor", "numero_factura")
    ordering = ("-fecha", "-id")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")
    date_hierarchy = "fecha"

    fieldsets = (
        ("Información principal", {
            "fields": ("descripcion", "monto", "fecha", "tipo")
        }),
        ("Proveedor y factura", {
            "fields": ("proveedor", "numero_factura", "comprobante")
        }),
        ("Configuración", {
            "fields": ("es_recurrente", "entrada_inventario", "notas")
        }),
        ("Auditoría", {
            "fields": ("fecha_creacion", "fecha_actualizacion"),
            "classes": ("collapse",)
        }),
    )

    def es_automatico(self, obj):
        if obj.es_automatico:
            return format_html('<span style="color:blue;">🔄 Auto</span>')
        return format_html('<span style="color:gray;">Manual</span>')
    es_automatico.short_description = "Origen"


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "fuente", "monto", "fecha", "cliente", "pago")
    list_filter = ("fuente", "fecha")
    search_fields = ("descripcion", "cliente__email")
    ordering = ("-fecha",)
    date_hierarchy = "fecha"


@admin.register(PresupuestoMensual)
class PresupuestoMensualAdmin(admin.ModelAdmin):
    list_display = ("mes", "tipo_gasto", "monto_presupuestado", "gasto_real_display", "diferencia_display", "porcentaje_display")
    list_filter = ("tipo_gasto", "mes")
    ordering = ("-mes", "tipo_gasto")

    def gasto_real_display(self, obj):
        return f"RD$ {obj.gasto_real()}"
    gasto_real_display.short_description = "Gasto real"

    def diferencia_display(self, obj):
        dif = obj.diferencia()
        color = "green" if dif >= 0 else "red"
        return format_html('<span style="color:{};">RD$ {}</span>', color, dif)
    diferencia_display.short_description = "Diferencia"

    def porcentaje_display(self, obj):
        pct = obj.porcentaje_usado()
        color = "red" if pct > 100 else ("orange" if pct > 80 else "green")
        return format_html('<span style="color:{};">{}%</span>', color, pct)
    porcentaje_display.short_description = "% Usado"


@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = ("pedido", "estado", "monto_total", "monto_pagado", "monto_pendiente_display", "fecha_emision", "fecha_vencimiento", "esta_vencida")
    list_filter = ("estado", "fecha_vencimiento")
    search_fields = ("pedido__id",)
    ordering = ("fecha_vencimiento",)

    def monto_pendiente_display(self, obj):
        pendiente = obj.monto_pendiente
        color = "red" if pendiente > 0 else "green"
        return format_html('<span style="color:{};">RD$ {}</span>', color, pendiente)
    monto_pendiente_display.short_description = "Pendiente"

    def esta_vencida(self, obj):
        if obj.esta_vencida:
            return format_html('<span style="color:red;font-weight:bold;">⚠ Vencida</span>')
        return format_html('<span style="color:green;">✔ Vigente</span>')
    esta_vencida.short_description = "Vencimiento"