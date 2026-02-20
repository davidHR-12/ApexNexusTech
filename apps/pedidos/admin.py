# apps/pedidos/admin.py
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import (
    SolicitudCotizacion, Pedido, ItemPedido, Pago,
    ActualizacionPedido, NotaPedido
)


# ============================================================
# INLINES
# ============================================================

class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    fields = ("variante", "descripcion", "cantidad", "precio_unitario", "gramos_por_unidad", "impresora_asignada")
    show_change_link = True


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    fields = ("monto", "metodo", "referencia", "fecha_pago", "comprobante")
    readonly_fields = ("fecha_pago",)


class ActualizacionInline(admin.TabularInline):
    model = ActualizacionPedido
    extra = 0
    fields = ("mensaje", "visible_cliente", "imagen", "fecha", "usuario")
    readonly_fields = ("fecha",)


class NotaPedidoInline(admin.TabularInline):
    model = NotaPedido
    extra = 0
    fields = ("contenido", "visible_para_cliente", "autor", "fecha_creacion")
    readonly_fields = ("fecha_creacion",)


# ============================================================
# SOLICITUDES DE COTIZACIÓN
# ============================================================

@admin.register(SolicitudCotizacion)
class SolicitudCotizacionAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "estado", "precio_cotizado", "fecha_solicitud", "fecha_respuesta")
    list_filter = ("estado", "fecha_solicitud")
    search_fields = ("usuario__email", "descripcion")
    ordering = ("-fecha_solicitud",)
    readonly_fields = ("fecha_solicitud",)
    list_editable = ("estado",)

    fieldsets = (
        ("Solicitud del cliente", {
            "fields": ("usuario", "descripcion", "imagen_referencia", "enlace_referencia", "dimensiones_aprox", "fecha_solicitud")
        }),
        ("Respuesta del administrador", {
            "fields": ("estado", "precio_cotizado", "tiempo_estimado", "notas_admin", "fecha_respuesta")
        }),
    )


# ============================================================
# PEDIDOS
# ============================================================

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id", "usuario", "estado_pedido", "precio_total",
        "estado_pago_col", "saldo_pendiente_col", "fecha_creacion"
    )
    list_filter = ("estado_pedido", "fecha_creacion")
    search_fields = ("usuario__email", "descripcion", "id")
    ordering = ("-fecha_creacion",)
    readonly_fields = (
        "fecha_creacion", "fecha_inicio_produccion", "fecha_entrega",
        "costo_total_produccion", "ganancia", "margen_porcentaje",
        "total_pagado", "saldo_pendiente", "esta_pagado", "porcentaje_progreso"
    )
    inlines = [ItemPedidoInline, PagoInline, NotaPedidoInline, ActualizacionInline]

    fieldsets = (
        ("Cliente y estado", {
            "fields": ("usuario", "solicitud", "estado_pedido", "stock_descontado")
        }),
        ("Descripción", {
            "fields": ("descripcion", "notas")
        }),
        ("Datos técnicos", {
            "fields": ("peso_estimado_g", "tiempo_estimado_h")
        }),
        ("Costos y precios", {
            "fields": (
                "precio_kwh_usado", "costo_material", "costo_energia",
                "otros_costos", "precio_total",
                "costo_total_produccion", "ganancia", "margen_porcentaje"
            )
        }),
        ("Pagos", {
            "fields": ("total_pagado", "saldo_pendiente", "esta_pagado")
        }),
        ("Fechas", {
            "fields": ("fecha_creacion", "fecha_inicio_produccion", "fecha_entrega"),
            "classes": ("collapse",)
        }),
    )

    # ----------------------------------------------------------------
    # REGLA Django 6: format_html SIEMPRE necesita al menos 1 argumento.
    # Para HTML completamente estático (sin variables) → usar mark_safe()
    # Para HTML con variables                          → usar format_html('...{}', var)
    # ----------------------------------------------------------------

    def estado_pago_col(self, obj):
        if obj.esta_pagado:
            return mark_safe('<span style="color:green;font-weight:bold;">✔ Pagado</span>')
        elif obj.total_pagado > 0:
            return format_html(
                '<span style="color:orange;font-weight:bold;">⏳ Parcial (RD$ {})</span>',
                obj.total_pagado
            )
        return mark_safe('<span style="color:red;font-weight:bold;">✗ Sin pago</span>')
    estado_pago_col.short_description = "Pago"

    def saldo_pendiente_col(self, obj):
        saldo = obj.saldo_pendiente
        if saldo <= 0:
            return mark_safe('<span style="color:green;">RD$ 0</span>')
        return format_html('<span style="color:red;">RD$ {}</span>', saldo)
    saldo_pendiente_col.short_description = "Saldo pendiente"


# ============================================================
# ITEMS, PAGOS, ACTUALIZACIONES
# ============================================================

@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "pedido", "cantidad", "precio_unitario", "subtotal_col", "impresora_asignada")
    list_filter = ("pedido__estado_pedido",)
    search_fields = ("pedido__id", "descripcion", "variante__producto__nombre")
    ordering = ("-pedido__fecha_creacion",)

    def subtotal_col(self, obj):
        return format_html("RD$ {}", obj.subtotal)
    subtotal_col.short_description = "Subtotal"


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "monto", "metodo", "referencia", "fecha_pago")
    list_filter = ("metodo", "fecha_pago")
    search_fields = ("pedido__id", "referencia")
    ordering = ("-fecha_pago",)
    readonly_fields = ("fecha_pago",)


@admin.register(ActualizacionPedido)
class ActualizacionPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "usuario", "visible_cliente", "fecha")
    list_filter = ("visible_cliente", "fecha")
    search_fields = ("pedido__id", "mensaje")
    ordering = ("-fecha",)
    readonly_fields = ("fecha",)


@admin.register(NotaPedido)
class NotaPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "autor", "visible_para_cliente", "fecha_creacion")
    list_filter = ("visible_para_cliente",)
    search_fields = ("pedido__id", "contenido")
    ordering = ("-fecha_creacion",)
    readonly_fields = ("fecha_creacion",)