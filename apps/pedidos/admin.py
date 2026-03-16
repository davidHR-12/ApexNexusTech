from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import now
from django.db.models import Sum, Count
from django.urls import reverse
from decimal import Decimal

from .models import (
    SolicitudCotizacion,
    Pedido,
    ItemPedido,
    Pago,
    ActualizacionPedido,
    NotaPedido,
    PerdidaMaterial,
    ConfiguracionPago,
)


# =============================
# INLINES
# =============================


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    fk_name = "pedido"
    extra = 0
    fields = (
        "variante",
        "descripcion",
        "cantidad",
        "precio_unitario",
        "gramos_por_unidad",
        "costo_material_unitario",
        "material_personalizado",
        "impresora_asignada",
        "fallo_registrado",
    )
    autocomplete_fields = ["variante", "material_personalizado", "impresora_asignada"]
    show_change_link = True
    verbose_name = "Ítem del pedido"
    verbose_name_plural = "Ítems del pedido"

    def get_queryset(self, request):
        # Solo mostrar ítems raíz (sin padre) en el inline del pedido
        return super().get_queryset(request).filter(item_padre__isnull=True)


class ComponenteItemInline(admin.TabularInline):
    """Componentes de un ítem contenedor (piezas de producción)."""
    model = ItemPedido
    fk_name = "item_padre"
    extra = 0
    fields = (
        "descripcion",
        "cantidad",
        "precio_unitario",
        "gramos_por_unidad",
        "costo_material_unitario",
        "material_personalizado",
        "impresora_asignada",
        "fallo_registrado",
    )
    autocomplete_fields = ["material_personalizado", "impresora_asignada"]
    verbose_name = "Componente de producción"
    verbose_name_plural = "Componentes de producción"


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    fields = ("monto", "metodo", "referencia", "comprobante", "notas", "fecha_pago")
    readonly_fields = ("fecha_pago",)
    show_change_link = True


class NotaPedidoInline(admin.TabularInline):
    model = NotaPedido
    fk_name = "pedido"
    extra = 1
    fields = ("contenido", "tipo", "visible_para_cliente", "autor", "fecha_creacion")
    readonly_fields = ("fecha_creacion",)


class ActualizacionPedidoInline(admin.TabularInline):
    model = ActualizacionPedido
    extra = 0
    fields = ("mensaje", "imagen", "visible_cliente", "usuario", "fecha")
    readonly_fields = ("fecha",)


class PerdidaMaterialInline(admin.TabularInline):
    model = PerdidaMaterial
    extra = 0
    fields = ("material", "gramos_perdidos", "motivo", "registrado_por", "fecha")
    readonly_fields = ("fecha",)


# =============================
# SOLICITUD DE COTIZACIÓN
# =============================


@admin.register(SolicitudCotizacion)
class SolicitudCotizacionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "descripcion_corta",
        "estado_badge",
        "tiene_imagen",
        "tiene_enlace",
        "fecha_solicitud",
    )
    list_filter = ("estado", "fecha_solicitud")
    search_fields = ("usuario__email", "usuario__first_name", "descripcion")
    readonly_fields = ("fecha_solicitud", "vista_imagen_referencia")
    ordering = ("-fecha_solicitud",)
    list_per_page = 25

    fieldsets = (
        ("Cliente", {
            "fields": ("usuario",),
        }),
        ("Detalles de la solicitud", {
            "fields": (
                "descripcion",
                "dimensiones_aprox",
                "imagen_referencia",
                "vista_imagen_referencia",
                "enlace_referencia",
            ),
        }),
        ("Gestión", {
            "fields": ("estado", "fecha_solicitud"),
        }),
    )

    @admin.display(description="Descripción")
    def descripcion_corta(self, obj):
        return obj.descripcion[:80] + "…" if len(obj.descripcion) > 80 else obj.descripcion

    @admin.display(description="Estado")
    def estado_badge(self, obj):
        colores = {
            "Pendiente": "#f59e0b",
            "Completada": "#10b981",
            "Rechazada": "#ef4444",
        }
        color = colores.get(obj.estado, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:12px;font-size:12px;font-weight:600;">{}</span>',
            color,
            obj.get_estado_display(),
        )

    @admin.display(description="Imagen", boolean=True)
    def tiene_imagen(self, obj):
        return bool(obj.imagen_referencia)

    @admin.display(description="Enlace", boolean=True)
    def tiene_enlace(self, obj):
        return bool(obj.enlace_referencia)

    @admin.display(description="Vista previa de imagen")
    def vista_imagen_referencia(self, obj):
        if obj.imagen_referencia:
            return format_html(
                '<img src="{}" style="max-height:200px;max-width:400px;'
                'border-radius:6px;border:1px solid #e5e7eb;" />',
                obj.imagen_referencia.url,
            )
        return "—"


# =============================
# PEDIDO
# =============================


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre_cliente",
        "email_cliente",
        "estado_badge",
        "precio_total",
        "total_pagado_display",
        "saldo_pendiente_display",
        "esta_pagado_badge",
        "porcentaje_progreso",
        "fecha_creacion",
    )
    list_filter = (
        "estado_pedido",
        "metodo_pago_preferido",
        "comprobante_estado",
        "stock_descontado",
        "fecha_creacion",
    )
    search_fields = (
        "id",
        "usuario__email",
        "usuario__first_name",
        "guest_email",
        "guest_nombre",
        "descripcion",
    )
    readonly_fields = (
        "fecha_creacion",
        "nombre_cliente",
        "email_cliente",
        "telefono_cliente",
        "costo_total_produccion",
        "ganancia",
        "margen_porcentaje",
        "total_pagado",
        "saldo_pendiente",
        "esta_pagado",
        "porcentaje_progreso",
        "vista_comprobante_cliente",
    )
    ordering = ("-fecha_creacion",)
    list_per_page = 25
    save_on_top = True
    date_hierarchy = "fecha_creacion"

    inlines = [
        ItemPedidoInline,
        PagoInline,
        ActualizacionPedidoInline,
        NotaPedidoInline,
        PerdidaMaterialInline,
    ]

    fieldsets = (
        ("Cliente", {
            "fields": (
                "usuario",
                "nombre_cliente",
                "email_cliente",
                "telefono_cliente",
            ),
        }),
        ("Datos de invitado (si aplica)", {
            "classes": ("collapse",),
            "fields": (
                "guest_nombre",
                "guest_email",
                "guest_telefono",
                "guest_direccion",
                "guest_ciudad",
            ),
        }),
        ("Descripción y estado", {
            "fields": (
                "descripcion",
                "solicitud",
                "estado_pedido",
                "stock_descontado",
                "notas",
            ),
        }),
        ("Costos y precios", {
            "fields": (
                "peso_estimado_g",
                "costo_material",
                "otros_costos",
                "precio_total",
                "costo_total_produccion",
                "ganancia",
                "margen_porcentaje",
            ),
        }),
        ("Pagos", {
            "fields": (
                "metodo_pago_preferido",
                "comprobante_cliente",
                "vista_comprobante_cliente",
                "comprobante_estado",
                "total_pagado",
                "saldo_pendiente",
                "esta_pagado",
            ),
        }),
        ("Fechas", {
            "fields": (
                "fecha_creacion",
                "fecha_inicio_produccion",
                "fecha_entrega",
            ),
        }),
    )

    # ── Acciones masivas ──────────────────────────────────────────────────────

    actions = [
        "marcar_confirmado",
        "marcar_en_produccion",
        "marcar_listo",
        "marcar_entregado",
        "marcar_cancelado",
    ]

    @admin.action(description="✅ Marcar como Confirmado")
    def marcar_confirmado(self, request, queryset):
        actualizado = queryset.update(estado_pedido="Confirmado")
        self.message_user(request, f"{actualizado} pedido(s) marcado(s) como Confirmado.")

    @admin.action(description="🔧 Marcar como En Producción")
    def marcar_en_produccion(self, request, queryset):
        actualizado = queryset.update(estado_pedido="En_Produccion", fecha_inicio_produccion=now())
        self.message_user(request, f"{actualizado} pedido(s) marcado(s) como En Producción.")

    @admin.action(description="📦 Marcar como Listo para entrega")
    def marcar_listo(self, request, queryset):
        actualizado = queryset.update(estado_pedido="Listo")
        self.message_user(request, f"{actualizado} pedido(s) marcado(s) como Listo.")

    @admin.action(description="🏁 Marcar como Entregado")
    def marcar_entregado(self, request, queryset):
        actualizado = queryset.update(estado_pedido="Entregado", fecha_entrega=now())
        self.message_user(request, f"{actualizado} pedido(s) marcado(s) como Entregado.")

    @admin.action(description="❌ Marcar como Cancelado")
    def marcar_cancelado(self, request, queryset):
        actualizado = queryset.update(estado_pedido="Cancelado")
        self.message_user(request, f"{actualizado} pedido(s) cancelado(s).")

    # ── Columnas personalizadas ───────────────────────────────────────────────

    @admin.display(description="Estado")
    def estado_badge(self, obj):
        colores = {
            "En_Espera":     "#f59e0b",
            "Confirmado":    "#3b82f6",
            "En_Produccion": "#8b5cf6",
            "Listo":         "#10b981",
            "Entregado":     "#6b7280",
            "Cancelado":     "#ef4444",
        }
        color = colores.get(obj.estado_pedido, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;'
            'border-radius:12px;font-size:12px;font-weight:600;">{}</span>',
            color,
            obj.get_estado_pedido_display(),
        )

    @admin.display(description="Pagado", ordering="precio_total")
    def total_pagado_display(self, obj):
        return f"${obj.total_pagado:,.2f}"

    @admin.display(description="Saldo")
    def saldo_pendiente_display(self, obj):
        saldo = obj.saldo_pendiente
        color = "#ef4444" if saldo > 0 else "#10b981"
        saldo_str = f"${saldo:,.2f}"
        return format_html('<span style="color:{};font-weight:600;">{}</span>', color, saldo_str)

    @admin.display(description="Pagado", boolean=True)
    def esta_pagado_badge(self, obj):
        return obj.esta_pagado

    @admin.display(description="Progreso %")
    def porcentaje_progreso(self, obj):
        pct = obj.porcentaje_progreso
        return format_html(
            '<div style="background:#e5e7eb;border-radius:6px;width:80px;height:12px;">'
            '<div style="background:#6366f1;width:{}%;height:100%;border-radius:6px;"></div>'
            "</div> {}%",
            pct, pct,
        )

    @admin.display(description="Comprobante cliente")
    def vista_comprobante_cliente(self, obj):
        if obj.comprobante_cliente:
            return format_html(
                '<img src="{}" style="max-height:150px;max-width:300px;'
                'border-radius:6px;border:1px solid #e5e7eb;" />',
                obj.comprobante_cliente.url,
            )
        return "—"


# =============================
# ITEM DE PEDIDO
# =============================


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido_link",
        "variante",
        "descripcion",
        "cantidad",
        "precio_unitario",
        "subtotal_display",
        "gramos_totales_display",
        "impresora_asignada",
        "fallo_registrado",
        "es_contenedor",
        "es_componente",
    )
    list_filter = ("fallo_registrado", "impresora_asignada")
    search_fields = (
        "pedido__id",
        "variante__nombre",
        "descripcion",
    )
    autocomplete_fields = ["variante", "material_personalizado", "impresora_asignada"]
    readonly_fields = ("es_contenedor", "es_componente", "subtotal", "gramos_totales")
    list_per_page = 30
    inlines = [ComponenteItemInline]

    @admin.display(description="Pedido")
    def pedido_link(self, obj):
        url = reverse("admin:pedidos_pedido_change", args=[obj.pedido.pk])
        return format_html('<a href="{}">Pedido #{}</a>', url, obj.pedido.pk)

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        return f"${obj.subtotal:,.2f}"

    @admin.display(description="Gramos totales")
    def gramos_totales_display(self, obj):
        return f"{obj.gramos_totales:,.2f} g"


# =============================
# PAGO
# =============================


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido_link",
        "monto",
        "metodo",
        "referencia",
        "tiene_comprobante",
        "fecha_pago",
    )
    list_filter = ("metodo", "fecha_pago")
    search_fields = ("pedido__id", "referencia", "pedido__usuario__email")
    readonly_fields = ("fecha_pago", "vista_comprobante")
    ordering = ("-fecha_pago",)
    date_hierarchy = "fecha_pago"

    @admin.display(description="Pedido")
    def pedido_link(self, obj):
        url = reverse("admin:pedidos_pedido_change", args=[obj.pedido.pk])
        return format_html('<a href="{}">Pedido #{}</a>', url, obj.pedido.pk)

    @admin.display(description="Comprobante", boolean=True)
    def tiene_comprobante(self, obj):
        return bool(obj.comprobante)

    @admin.display(description="Vista comprobante")
    def vista_comprobante(self, obj):
        if obj.comprobante:
            return format_html(
                '<img src="{}" style="max-height:200px;max-width:400px;'
                'border-radius:6px;border:1px solid #e5e7eb;" />',
                obj.comprobante.url,
            )
        return "—"


# =============================
# NOTA DE PEDIDO
# =============================


@admin.register(NotaPedido)
class NotaPedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido_link",
        "tipo",
        "autor",
        "contenido_corto",
        "visible_para_cliente",
        "fecha_creacion",
    )
    list_filter = ("tipo", "visible_para_cliente", "fecha_creacion")
    search_fields = ("pedido__id", "contenido", "autor__email")
    readonly_fields = ("fecha_creacion",)
    ordering = ("-fecha_creacion",)

    @admin.display(description="Pedido")
    def pedido_link(self, obj):
        url = reverse("admin:pedidos_pedido_change", args=[obj.pedido.pk])
        return format_html('<a href="{}">Pedido #{}</a>', url, obj.pedido.pk)

    @admin.display(description="Contenido")
    def contenido_corto(self, obj):
        return obj.contenido[:100] + "…" if len(obj.contenido) > 100 else obj.contenido


# =============================
# ACTUALIZACIÓN DE PEDIDO
# =============================


@admin.register(ActualizacionPedido)
class ActualizacionPedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido_link",
        "mensaje_corto",
        "visible_cliente",
        "tiene_imagen",
        "usuario",
        "fecha",
    )
    list_filter = ("visible_cliente", "fecha")
    search_fields = ("pedido__id", "mensaje", "usuario__email")
    readonly_fields = ("fecha", "vista_imagen")
    ordering = ("-fecha",)

    @admin.display(description="Pedido")
    def pedido_link(self, obj):
        url = reverse("admin:pedidos_pedido_change", args=[obj.pedido.pk])
        return format_html('<a href="{}">Pedido #{}</a>', url, obj.pedido.pk)

    @admin.display(description="Mensaje")
    def mensaje_corto(self, obj):
        return obj.mensaje[:80] + "…" if len(obj.mensaje) > 80 else obj.mensaje

    @admin.display(description="Imagen", boolean=True)
    def tiene_imagen(self, obj):
        return bool(obj.imagen)

    @admin.display(description="Vista imagen")
    def vista_imagen(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="max-height:200px;max-width:400px;'
                'border-radius:6px;border:1px solid #e5e7eb;" />',
                obj.imagen.url,
            )
        return "—"


# =============================
# PÉRDIDA DE MATERIAL
# =============================


@admin.register(PerdidaMaterial)
class PerdidaMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido_link",
        "material",
        "gramos_perdidos",
        "motivo_corto",
        "registrado_por",
        "fecha",
    )
    list_filter = ("material", "fecha")
    search_fields = ("pedido__id", "material__nombre", "motivo")
    readonly_fields = ("fecha",)
    ordering = ("-fecha",)
    date_hierarchy = "fecha"

    @admin.display(description="Pedido")
    def pedido_link(self, obj):
        url = reverse("admin:pedidos_pedido_change", args=[obj.pedido.pk])
        return format_html('<a href="{}">Pedido #{}</a>', url, obj.pedido.pk)

    @admin.display(description="Motivo")
    def motivo_corto(self, obj):
        return obj.motivo[:80] + "…" if len(obj.motivo) > 80 else obj.motivo or "—"


# =============================
# CONFIGURACIÓN DE PAGO
# =============================


@admin.register(ConfiguracionPago)
class ConfiguracionPagoAdmin(admin.ModelAdmin):
    list_display = (
        "banco",
        "titular",
        "numero_cuenta",
        "tipo_cuenta",
        "telefono_pago",
        "porcentaje_anticipo",
        "activo",
    )
    list_filter = ("activo",)
    search_fields = ("banco", "titular", "numero_cuenta")
    fieldsets = (
        ("Datos bancarios", {
            "fields": (
                "banco",
                "titular",
                "numero_cuenta",
                "tipo_cuenta",
                "cedula",
            ),
        }),
        ("Configuración de pago", {
            "fields": (
                "telefono_pago",
                "porcentaje_anticipo",
                "instrucciones_adicionales",
            ),
        }),
        ("Estado", {
            "fields": ("activo",),
        }),
    )