from django.contrib import admin
from django.utils.html import format_html
from .models import TipoMaterial, Marca, Color, Material, EntradaInventario, HistorialInventario, ConsumoMaterial

# =============================
# CONFIGURACIONES BÁSICAS
# =============================

@admin.register(TipoMaterial)
class TipoMaterialAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'pais_origen')
    search_fields = ('nombre',)

@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_hex', 'color_preview')
    search_fields = ('nombre',)

    def color_preview(self, obj):
        if obj.codigo_hex:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #000; border-radius: 50%;"></div>',
                obj.codigo_hex
            )
        return "N/A"
    color_preview.short_description = "Vista previa"

# =============================
# GESTIÓN DE INVENTARIO
# =============================

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'marca', 'color', 'stock_actual_display', 'stock_minimo', 'costo_por_gramo', 'activo')
    list_filter = ('tipo', 'marca', 'activo')
    search_fields = ('tipo__nombre', 'marca__nombre', 'color__nombre')
    list_editable = ('stock_minimo', 'activo')

    def stock_actual_display(self, obj):
        """Colorea el stock si está por debajo del mínimo"""
        color = "red" if obj.necesita_reposicion else "green"
        return format_html(
            '<b style="color: {};">{}g</b>',
            color, obj.stock_actual
        )
    stock_actual_display.short_description = "Stock Actual"

@admin.register(EntradaInventario)
class EntradaInventarioAdmin(admin.ModelAdmin):
    list_display = ('material', 'cantidad_gramos', 'costo_total', 'fecha', 'proveedor')
    list_filter = ('fecha', 'material__marca', 'proveedor')
    search_fields = ('material__tipo__nombre', 'material__color__nombre', 'numero_factura')
    readonly_fields = ('fecha',)
    
    fieldsets = (
        ('Detalle de Compra', {
            'fields': ('material', 'cantidad_gramos', 'costo_total', 'proveedor', 'numero_factura')
        }),
        ('Información Adicional', {
            'fields': ('notas', 'fecha')
        }),
    )

@admin.register(ConsumoMaterial)
class ConsumoMaterialAdmin(admin.ModelAdmin):
    list_display = ('material', 'gramos_usados', 'fecha', 'destino_display')
    list_filter = ('fecha', 'material__tipo')
    search_fields = ('material__color__nombre', 'notas')
    readonly_fields = ('fecha',)

    def destino_display(self, obj):
        return f"Pedido #{obj.pedido.id}" if obj.pedido else "Producción Interna"
    destino_display.short_description = "Destino"

@admin.register(HistorialInventario)
class HistorialInventarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'material', 'accion', 'cantidad_anterior', 'diferencia', 'cantidad_nueva')
    list_filter = ('accion', 'fecha', 'material')
    search_fields = ('material__tipo__nombre', 'material__color__nombre')
    
    # El historial debe ser mayormente de solo lectura para evitar manipulaciones
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False