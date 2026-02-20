# apps/productos/admin.py
from django.contrib import admin
from .models import (
    Categoria, Producto, VarianteProducto, VarianteMaterialDetalle,
    ImagenProducto, ProduccionInterna
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "orden", "activa", "slug")
    list_filter = ("activa",)
    search_fields = ("nombre",)
    prepopulated_fields = {"slug": ("nombre",)}
    ordering = ("orden", "nombre")
    list_editable = ("orden", "activa")


class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 0
    fields = ("imagen", "orden", "descripcion")


class VarianteMaterialDetalleInline(admin.TabularInline):
    model = VarianteMaterialDetalle
    extra = 1
    fields = ("material", "gramos_usados")


class VarianteProductoInline(admin.TabularInline):
    model = VarianteProducto
    extra = 0
    fields = ("activa", "es_default", "stock_disponible", "precio_adicional", "tiempo_impresion_horas", "codigo_sku")
    show_change_link = True


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio_venta", "stock_total", "mostrar_en_web", "activo", "fecha_creacion")
    list_filter = ("categoria", "mostrar_en_web", "activo", "destacado")
    search_fields = ("nombre", "descripcion")
    prepopulated_fields = {"slug": ("nombre",)}
    ordering = ("-fecha_creacion",)
    readonly_fields = ("fecha_creacion", "fecha_modificacion")
    list_editable = ("mostrar_en_web", "activo")
    inlines = [VarianteProductoInline, ImagenProductoInline]

    fieldsets = (
        ("Información básica", {"fields": ("nombre", "slug", "categoria", "descripcion", "imagen")}),
        ("Precios", {"fields": ("precio_venta",)}),
        ("Configuración", {"fields": ("mostrar_en_web", "destacado", "activo")}),
        ("Auditoría", {"fields": ("fecha_creacion", "fecha_modificacion"), "classes": ("collapse",)}),
    )

    def stock_total(self, obj):
        return obj.stock_total
    stock_total.short_description = "Stock total"


@admin.register(VarianteProducto)
class VarianteProductoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "producto", "stock_disponible", "precio_adicional", "precio_final", "tiempo_impresion_horas", "activa", "es_default")
    list_filter = ("activa", "es_default", "producto__categoria")
    search_fields = ("producto__nombre", "codigo_sku")
    ordering = ("producto__nombre",)
    readonly_fields = ("firma_materiales", "codigo_sku")
    list_editable = ("activa", "stock_disponible")
    inlines = [VarianteMaterialDetalleInline]

    def precio_final(self, obj):
        return f"RD$ {obj.precio_final}"
    precio_final.short_description = "Precio final"


@admin.register(ProduccionInterna)
class ProduccionInternaAdmin(admin.ModelAdmin):
    list_display = ("variante", "cantidad_producida", "costo_total_produccion", "fecha")
    list_filter = ("fecha", "variante__producto__categoria")
    search_fields = ("variante__producto__nombre",)
    ordering = ("-fecha",)
    readonly_fields = ("fecha", "costo_total_produccion")

    def has_change_permission(self, request, obj=None):
        return False