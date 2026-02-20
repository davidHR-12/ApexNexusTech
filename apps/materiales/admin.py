# apps/materiales/admin.py
from django.contrib import admin
from .models import TipoMaterial, Marca, Color, Material, EntradaInventario, HistorialInventario, ConsumoMaterial


@admin.register(TipoMaterial)
class TipoMaterialAdmin(admin.ModelAdmin):
    list_display = ("nombre", "descripcion")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "pais_origen")
    search_fields = ("nombre",)
    ordering = ("nombre",)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo_hex", "color_preview")
    search_fields = ("nombre",)
    ordering = ("nombre",)

    def color_preview(self, obj):
        from django.utils.html import format_html
        if obj.codigo_hex:
            return format_html(
                '<div style="width:24px;height:24px;border-radius:50%;background:{};border:1px solid #ccc;display:inline-block;"></div>',
                obj.codigo_hex
            )
        return "-"
    color_preview.short_description = "Color"


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tipo", "marca", "color", "stock_actual", "stock_minimo", "costo_por_gramo", "necesita_reposicion", "activo")
    list_filter = ("tipo", "marca", "activo")
    search_fields = ("tipo__nombre", "marca__nombre", "color__nombre")
    ordering = ("tipo__nombre", "marca__nombre", "color__nombre")
    readonly_fields = ("stock_actual",)

    def necesita_reposicion(self, obj):
        from django.utils.html import format_html
        if obj.necesita_reposicion:
            return format_html('<span style="color:red;font-weight:bold;">⚠ Bajo stock</span>')
        return format_html('<span style="color:green;">✔ OK</span>')
    necesita_reposicion.short_description = "Stock"


@admin.register(EntradaInventario)
class EntradaInventarioAdmin(admin.ModelAdmin):
    list_display = ("material", "cantidad_gramos", "costo_total", "fecha", "proveedor", "numero_factura")
    list_filter = ("material__tipo", "material__marca", "fecha")
    search_fields = ("material__tipo__nombre", "material__marca__nombre", "proveedor", "numero_factura")
    ordering = ("-fecha",)
    readonly_fields = ("fecha",)


@admin.register(HistorialInventario)
class HistorialInventarioAdmin(admin.ModelAdmin):
    list_display = ("fecha", "material", "accion", "diferencia", "cantidad_anterior", "cantidad_nueva")
    list_filter = ("accion", "fecha")
    search_fields = ("material__tipo__nombre", "material__marca__nombre")
    ordering = ("-fecha",)
    readonly_fields = ("fecha", "material", "entrada", "accion", "cantidad_nueva", "cantidad_anterior", "diferencia")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ConsumoMaterial)
class ConsumoMaterialAdmin(admin.ModelAdmin):
    list_display = ("material", "gramos_usados", "pedido", "fecha")
    list_filter = ("material__tipo", "fecha")
    search_fields = ("material__tipo__nombre", "material__marca__nombre")
    ordering = ("-fecha",)
    readonly_fields = ("fecha",)