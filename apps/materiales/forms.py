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
    # Definimos campos de texto para capturar lo que viene de HTMX/Inputs
    marca_nombre = forms.CharField(max_length=100, label="Marca")
    tipo_nombre = forms.CharField(max_length=100, label="Tipo")
    color_nombre = forms.CharField(max_length=100, label="Color")

    class Meta:
        model = Material
        # Solo dejamos los campos numéricos directos del modelo
        fields = [
            "costo_por_gramo",
            "stock_minimo",
        ]

    def save(self, commit=True):
        # 1. Extraer nombres limpios
        marca_txt = self.cleaned_data['marca_nombre'].strip()
        tipo_txt = self.cleaned_data['tipo_nombre'].strip()
        color_txt = self.cleaned_data['color_nombre'].strip()

        # 2. Lógica Get or Create para los objetos relacionados
        marca_obj, _ = Marca.objects.get_or_create(nombre=marca_txt)
        tipo_obj, _ = TipoMaterial.objects.get_or_create(nombre=tipo_txt)
        color_obj, _ = Color.objects.get_or_create(nombre=color_txt)

        # 3. Crear o recuperar el Material
        # Usamos self.instance para mantener la funcionalidad de ModelForm
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
        
        # Guardamos un flag temporal para que la vista sepa si enviará success o warning
        material.just_created = created
        
        return material

class EditarMaterialForm(TailwindModelForm):
    es_perdida = forms.BooleanField(required=False)
    cantidad_perdida = forms.DecimalField(required=False, min_value=0, max_digits=10, decimal_places=2)
    
    class Meta:
        model = Material
        fields = ["costo_por_gramo", "stock_minimo"]

    def clean(self):
        cleaned_data = super().clean()
        es_perdida = cleaned_data.get("es_perdida")
        cantidad_p = cleaned_data.get("cantidad_perdida") or 0

        # BLINDAJE: Si marca pérdida pero el stock actual es 0
        if es_perdida and self.instance.stock_actual <= 0:
            raise forms.ValidationError(
                "No se puede registrar una pérdida en un material que no tiene stock actual."
            )
            
        # BLINDAJE: Si la pérdida es mayor a lo que hay (opcional, si prefieres lanzar error en vez de limitar)
        if es_perdida and cantidad_p > self.instance.stock_actual:
            raise forms.ValidationError(
                f"La pérdida ({cantidad_p}g) no puede ser mayor al stock disponible ({self.instance.stock_actual}g)."
            )

        return cleaned_data

    def save(self, commit=True):
        material = super().save(commit=False)
        es_perdida = self.cleaned_data.get("es_perdida")
        cantidad_p = self.cleaned_data.get("cantidad_perdida") or 0

        if es_perdida and cantidad_p > 0:
            stock_viejo = material.stock_actual
            material.stock_actual -= cantidad_p
            
            # Registramos en historial (dentro del save para que sea atómico)
            HistorialInventario.objects.create(
                material=material,
                accion="Eliminación",
                cantidad_anterior=stock_viejo,
                cantidad_nueva=material.stock_actual,
                diferencia=-cantidad_p,
            )
        
        if commit:
            material.save()
        return material


class EntradaInventarioForm(TailwindModelForm):
    class Meta:
        model = EntradaInventario
        fields = ["material", "cantidad_gramos", "costo_total"]