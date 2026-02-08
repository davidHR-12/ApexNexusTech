from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SolicitudCotizacion, Pedido, ItemPedido, 
    Pago, ActualizacionPedido
)

# =============================
# INLINES (Edición en la misma pantalla)
# =============================

class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 1
    autocomplete_fields = ['variante']

class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    readonly_fields = ('fecha_pago',)

class ActualizacionPedidoInline(admin.StackedInline):
    model = ActualizacionPedido
    extra = 0
    fields = ('mensaje', 'imagen', 'visible_cliente', 'usuario')

# =============================
# CONFIGURACIÓN DEL ADMIN
# =============================

@admin.register(SolicitudCotizacion)
class SolicitudCotizacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'estado', 'fecha_solicitud', 'precio_cotizado')
    list_filter = ('estado', 'fecha_solicitud')
    search_fields = ('usuario__email', 'descripcion')
    date_hierarchy = 'fecha_solicitud'
    
    fieldsets = (
        ('Cliente y Solicitud', {
            'fields': ('usuario', 'descripcion', 'estado')
        }),
        ('Multimedia y Referencias', {
            'fields': ('imagen_referencia', 'enlace_referencia', 'dimensiones_aprox')
        }),
        ('Respuesta de Cotización', {
            'fields': ('precio_cotizado', 'tiempo_estimado', 'notas_admin', 'fecha_respuesta')
        }),
    )

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'usuario', 'estado_pedido', 'progreso_pago', 
        'precio_total', 'ganancia_display', 'fecha_creacion'
    )
    list_filter = ('estado_pedido', 'fecha_creacion')
    search_fields = ('usuario__email', 'descripcion', 'id')
    inlines = [ItemPedidoInline, PagoInline, ActualizacionPedidoInline]
    
    readonly_fields = ('fecha_creacion',)

    # Organización del formulario de Pedido
    fieldsets = (
        ('Información Principal', {
            'fields': ('usuario', 'solicitud', 'estado_pedido', 'descripcion')
        }),
        ('Métricas de Producción', {
            'fields': (('peso_estimado_g', 'tiempo_estimado_h'), 'precio_kwh_usado')
        }),
        ('Finanzas del Pedido', {
            'fields': (('costo_material', 'costo_energia', 'otros_costos'), 'precio_total'),
            'description': 'Los costos se comparan con el precio total para calcular rentabilidad.'
        }),
        ('Seguimiento Temporal', {
            'fields': ('fecha_inicio_produccion', 'fecha_entrega', 'notas')
        }),
    )

    def progreso_pago(self, obj):
        """Muestra una etiqueta visual del estado de pago"""
        total = obj.precio_total
        pagado = obj.total_pagado
        
        if pagado <= 0:
            return format_html('<span style="color: red;">❌ Sin Pago</span>')
        if pagado < total:
            return format_html('<span style="color: orange;">⚠️ Parcial (${})</span>', pagado)
        return format_html('<span style="color: green;">✅ Pagado</span>')
    progreso_pago.short_description = "Estado de Pago"

    def ganancia_display(self, obj):
        """Muestra la ganancia estimada y el margen"""
        ganancia = obj.ganancia
        margen = obj.margen_porcentaje
        color = "green" if ganancia > 0 else "red"
        return format_html(
            '<span style="color: {}; font-weight: bold;">${} ({}%)</span>',
            color, ganancia, margen
        )
    ganancia_display.short_description = "Ganancia Est."

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'pedido', 'monto', 'metodo', 'fecha_pago', 'referencia')
    list_filter = ('metodo', 'fecha_pago')
    search_fields = ('pedido__id', 'referencia')