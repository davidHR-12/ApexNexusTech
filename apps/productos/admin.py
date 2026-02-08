from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import (
    Categoria, Producto, VarianteProducto, 
    ImagenProducto, ProduccionInterna
)

# =============================
# INLINES
# =============================

class VarianteProductoInline(admin.TabularInline):
    model = VarianteProducto
    extra = 1  # Número de filas vacías para nuevas variantes
    fields = ('material', 'stock_disponible', 'precio_adicional', 'codigo_sku', 'activa')
    readonly_fields = ('codigo_sku',) # Se autogenera al guardar

class ImagenProductoInline(admin.StackedInline):
    model = ImagenProducto
    extra = 1
    fields = ('imagen', 'orden', 'descripcion')

# =============================
# CONFIGURACIONES ADMIN
# =============================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden', 'activa', 'slug')
    list_editable = ('orden', 'activa')
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)} # Autocompleta el slug mientras escribes

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio_venta', 'stock_total', 'mostrar_en_web', 'destacado', 'activo')
    list_filter = ('categoria', 'mostrar_en_web', 'destacado', 'activo', 'fecha_creacion')
    search_fields = ('nombre', 'descripcion')
    list_editable = ('precio_venta', 'mostrar_en_web', 'destacado', 'activo')
    prepopulated_fields = {'slug': ('nombre',)}
    
    # Agregamos los Inlines para editar variantes y fotos dentro del producto
    inlines = [VarianteProductoInline, ImagenProductoInline]
    
    # Agrupamos campos en el formulario de edición
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'slug', 'categoria', 'descripcion', 'imagen')
        }),
        ('Precios y Costos', {
            'fields': ('precio_venta', 'material_base', 'peso_gramos', 'tiempo_impresion_horas')
        }),
        ('Visibilidad y Estado', {
            'fields': ('mostrar_en_web', 'destacado', 'activo')
        }),
    )

@admin.register(VarianteProducto)
class VarianteProductoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'producto', 'material', 'stock_disponible', 'precio_final', 'codigo_sku', 'activa')
    list_filter = ('material', 'activa', 'producto')
    search_fields = ('codigo_sku', 'producto__nombre')
    readonly_fields = ('codigo_sku',)

@admin.register(ProduccionInterna)
class ProduccionInternaAdmin(admin.ModelAdmin):
    list_display = ('variante', 'cantidad_producida', 'material', 'gramos_totales', 'costo_material', 'fecha')
    list_filter = ('fecha', 'material', 'variante__producto')
    search_fields = ('variante__producto__nombre', 'observaciones')
    readonly_fields = ('fecha',) 
    
    # Agrupamos para que sea más limpio
    fieldsets = (
        ('Detalles de Producción', {
            'fields': ('variante', 'cantidad_producida', 'fecha')
        }),
        ('Insumos', {
            'fields': ('material', 'gramos_por_pieza')
        }),
        ('Notas', {
            'fields': ('observaciones',)
        }),
    )