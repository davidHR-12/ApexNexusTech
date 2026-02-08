from django.contrib import admin
from django.utils.html import format_html
from .models import Gasto, Ingreso, PresupuestoMensual, CuentaPorCobrar

# =============================
# GASTOS E INGRESOS
# =============================

@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'monto', 'tipo', 'fecha', 'es_automatico_display', 'es_recurrente')
    list_filter = ('tipo', 'fecha', 'es_recurrente')
    search_fields = ('descripcion', 'proveedor', 'numero_factura')
    readonly_fields = ('entrada_inventario',) # Para no romper la relación automática

    def es_automatico_display(self, obj):
        return obj.es_automatico
    es_automatico_display.boolean = True
    es_automatico_display.short_description = "Automático"

@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'monto', 'fuente', 'fecha', 'cliente')
    list_filter = ('fuente', 'fecha')
    search_fields = ('descripcion', 'cliente__email', 'cliente__first_name')
    readonly_fields = ('pago',)

# =============================
# PRESUPUESTOS Y ANÁLISIS
# =============================

@admin.register(PresupuestoMensual)
class PresupuestoMensualAdmin(admin.ModelAdmin):
    list_display = ('mes_display', 'tipo_gasto', 'monto_presupuestado', 'gasto_real_display', 'diferencia_display', 'progreso_display')
    list_filter = ('mes', 'tipo_gasto')
    
    def mes_display(self, obj):
        return obj.mes.strftime('%B %Y')
    mes_display.short_description = "Mes"

    def gasto_real_display(self, obj):
        return f"${obj.gasto_real()}"
    gasto_real_display.short_description = "Gasto Real"

    def diferencia_display(self, obj):
        diff = obj.diferencia()
        color = "green" if diff >= 0 else "red"
        return format_html('<span style="color: {}; font-weight: bold;">${}</span>', color, diff)
    diferencia_display.short_description = "Ahorro/Exceso"

    def progreso_display(self, obj):
        porcentaje = obj.porcentaje_usado()
        color = "#28a745" # Verde
        if porcentaje > 80: color = "#ffc107" # Amarillo
        if porcentaje > 100: color = "#dc3545" # Rojo
        
        return format_html(
            '''
            <div style="width: 100px; background: #eee; border-radius: 4px;">
                <div style="width: {}px; background: {}; height: 10px; border-radius: 4px;"></div>
            </div>
            <small>{}%</small>
            ''',
            min(int(porcentaje), 100), color, porcentaje
        )
    progreso_display.short_description = "% Usado"

# =============================
# CUENTAS POR COBRAR
# =============================

@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'monto_total', 'monto_pendiente_display', 'estado', 'fecha_vencimiento', 'vencimiento_status')
    list_filter = ('estado', 'fecha_vencimiento')
    search_fields = ('pedido__id', 'notas')
    
    def monto_pendiente_display(self, obj):
        return f"${obj.monto_pendiente}"
    monto_pendiente_display.short_description = "Pendiente"

    def vencimiento_status(self, obj):
        if obj.estado == "Cobrado":
            return format_html('<span style="color: green;">Pagado</span>')
        if obj.esta_vencida:
            return format_html('<span style="color: red; font-weight: bold;">VENCIDA</span>')
        return "Al día"
    vencimiento_status.short_description = "Estado de Pago"


admin.site.site_header = "Control de Impresión 3D"
admin.site.site_title = "Panel Administrativo"
admin.site.index_title = "Bienvenido a la Gestión del Negocio"