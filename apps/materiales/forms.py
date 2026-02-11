from django import forms
from django.core.exceptions import ValidationError
from .models import Material, EntradaInventario, Marca, TipoMaterial, Color, HistorialInventario


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

class MaterialForm(TailwindModelForm):
    marca_nombre = forms.CharField(max_length=100, label="Marca")
    tipo_nombre = forms.CharField(max_length=100, label="Tipo")
    color_nombre = forms.CharField(max_length=100, label="Color")
    color_hex = forms.CharField(max_length=7, initial="#10b981", required=False)

    class Meta:
        model = Material
        fields = ["costo_por_gramo", "stock_minimo"]

    def save(self, commit=True):
        marca_txt = self.cleaned_data['marca_nombre'].strip().capitalize()
        tipo_txt = self.cleaned_data['tipo_nombre'].strip().capitalize()
        color_txt = self.cleaned_data['color_nombre'].strip().capitalize()
        hex_txt = self.cleaned_data.get('color_hex', '#10b981')

        marca_obj, _ = Marca.objects.get_or_create(nombre__iexact=marca_txt, defaults={'nombre': marca_txt})
        tipo_obj, _ = TipoMaterial.objects.get_or_create(nombre__iexact=tipo_txt, defaults={'nombre': tipo_txt})
        
        # Buscar color por nombre (case-insensitive)
        color_obj = Color.objects.filter(nombre__iexact=color_txt).first()
        if not color_obj:
            color_obj = Color.objects.create(nombre=color_txt, codigo_hex=hex_txt)
        else:
            # Actualizar el hex si ya existe el color
            color_obj.codigo_hex = hex_txt
            color_obj.save()

        material, created = Material.objects.get_or_create(
            tipo=tipo_obj,
            marca=marca_obj,
            color=color_obj,
            defaults={
                "costo_por_gramo": self.cleaned_data["costo_por_gramo"],
                "stock_minimo": self.cleaned_data["stock_minimo"],
                "stock_actual": 0,
            },
        )
        material.just_created = created
        return material

class EditarMaterialForm(TailwindModelForm):
    es_perdida = forms.BooleanField(required=False)
    cantidad_perdida = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    color_hex = forms.CharField(max_length=7, required=False, label="Color Hex")
    
    class Meta:
        model = Material
        fields = ["costo_por_gramo", "stock_minimo"]

    def clean(self):
        cleaned_data = super().clean()
        es_perdida = cleaned_data.get("es_perdida")
        cantidad_p = cleaned_data.get("cantidad_perdida") or 0

        # Validación de pérdida con stock actual
        if es_perdida and self.instance.stock_actual <= 0:
            raise forms.ValidationError(
                "No se puede registrar una pérdida en un material que no tiene stock actual."
            )
            
        if es_perdida and cantidad_p > self.instance.stock_actual:
            raise forms.ValidationError(
                f"La pérdida ({cantidad_p}g) no puede ser mayor al stock disponible ({self.instance.stock_actual}g)."
            )

        return cleaned_data

    def save(self, commit=True):
        material = super().save(commit=False)
        es_perdida = self.cleaned_data.get("es_perdida")
        cantidad_p = self.cleaned_data.get("cantidad_perdida") or 0
        hex_txt = self.cleaned_data.get("color_hex", "").strip()

        # Manejar pérdida de stock
        if es_perdida and cantidad_p > 0:
            stock_viejo = material.stock_actual
            material.stock_actual -= cantidad_p
            
            # Registrar en historial
            HistorialInventario.objects.create(
                material=material,
                accion="Eliminación",
                cantidad_anterior=stock_viejo,
                cantidad_nueva=material.stock_actual,
                diferencia=-cantidad_p,
            )
        
        if commit:
            material.save()

            # Si viene un hex y el material tiene un objeto color asociado
            if hex_txt and material.color:
                color_obj = material.color
                color_obj.codigo_hex = hex_txt
                color_obj.save()
        return material


class EntradaInventarioForm(TailwindModelForm):
    class Meta:
        model = EntradaInventario
        fields = ["material", "cantidad_gramos", "costo_total"]

    def clean_cantidad_gramos(self):
        cantidad = self.cleaned_data.get("cantidad_gramos")
        if cantidad is not None and cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")
        return abs(cantidad)

    def clean_costo_total(self):
        costo = self.cleaned_data.get("costo_total")
        if costo is not None and costo < 0:
            raise forms.ValidationError("El costo no puede ser negativo.")
        return abs(costo)