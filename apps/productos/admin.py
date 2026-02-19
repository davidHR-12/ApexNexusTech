from django.contrib import admin
from .models import (
    Categoria, Producto, VarianteProducto, 
    ImagenProducto, ProduccionInterna, VarianteMaterialDetalle
)

# =============================
# INLINES (La clave para el nuevo sistema)
# =============================

class MaterialDetalleInline(admin.TabularInline):
    """Permite agregar materiales directamente dentro de la Variante"""
    model = VarianteMaterialDetalle
    extra = 1

class VarianteProductoInline(admin.TabularInline):
    """Se usa dentro de Producto para ver sus variantes"""
    model = VarianteProducto
    extra = 1
    fields = ('stock_disponible', 'precio_adicional', 'codigo_sku', 'activa')
    readonly_fields = ('codigo_sku',)

class ImagenProductoInline(admin.StackedInline):
    model = ImagenProducto
    extra = 1

# =============================
# CONFIGURACIONES ADMIN
# =============================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden', 'activa', 'slug')
    list_editable = ('orden', 'activa')
    prepopulated_fields = {'slug': ('nombre',)}

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio_venta', 'stock_total', 'mostrar_en_web', 'activo')
    list_filter = ('categoria', 'mostrar_en_web', 'activo')
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}
    inlines = [VarianteProductoInline, ImagenProductoInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'slug', 'categoria', 'descripcion', 'imagen')
        }),
        ('Datos Técnicos', {
            'fields': ('precio_venta', 'tiempo_impresion_horas')
        }),
        ('Estado', {
            'fields': ('mostrar_en_web', 'destacado', 'activo')
        }),
    )

@admin.register(VarianteProducto)
class VarianteProductoAdmin(admin.ModelAdmin):
    # Ya no mostramos 'material' porque ahora son varios
    list_display = ('__str__', 'producto', 'stock_disponible', 'precio_final', 'codigo_sku', 'activa')
    list_filter = ('activa', 'producto')
    search_fields = ('codigo_sku', 'producto__nombre')
    readonly_fields = ('codigo_sku',)
    # Agregamos el inline de materiales para definirlos aquí mismo
    inlines = [MaterialDetalleInline]

@admin.register(ProduccionInterna)
class ProduccionInternaAdmin(admin.ModelAdmin):
    # Quitamos 'material' y 'costo_material' de la lista porque ahora son dinámicos
    list_display = ('variante', 'cantidad_producida', 'fecha')
    list_filter = ('fecha', 'variante__producto')
    readonly_fields = ('fecha',) 
    
    fieldsets = (
        ('Detalles de Producción', {
            'fields': ('variante', 'cantidad_producida', 'fecha')
        }),
        ('Notas', {
            'fields': ('observaciones',)
        }),
    )