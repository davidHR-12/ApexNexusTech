from django import forms
from .models import Categoria, Producto, ProduccionInterna
from django.core.exceptions import ValidationError

# Widget para permitir múltiples archivos en la galería
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


# Clase base para aplicar estilos de Tailwind rápidamente
class TailwindModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = (
                    "rounded border-gray-700 text-[#10b981] focus:ring-[#10b981] bg-gray-900"
                )
            else:
                field.widget.attrs["class"] = (
                    "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981]"
                )
class ProductoForm(TailwindModelForm):
    class Meta:
        model = Producto
        fields = [
            "nombre",
            "categoria",
            "descripcion",
            "precio_venta",
            "material_base",
            "peso_gramos",
            "imagen",
            "mostrar_en_web",
        ]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2})}


class CategoriaForm(TailwindModelForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion", "imagen"]


class ProduccionInternaForm(TailwindModelForm):
    class Meta:
        model = ProduccionInterna
        fields = [
            "variante",
            "cantidad_producida",
            "material",
            "gramos_por_pieza",
            "observaciones",
        ]
        widgets = {"observaciones": forms.Textarea(attrs={"rows": 2})}

    def clean(self):
        cd = super().clean()
        material = cd.get("material")
        if material and cd.get("cantidad_producida") and cd.get("gramos_por_pieza"):
            total = cd["cantidad_producida"] * cd["gramos_por_pieza"]
            if material.stock_actual < total:
                raise ValidationError(
                    f"Stock insuficiente. Necesitas {total}g y solo hay {material.stock_actual}g."
                )
        return cd

