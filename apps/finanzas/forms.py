from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Gasto,
)

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

class GastoForm(TailwindModelForm):
    class Meta:
        model = Gasto
        fields = ["descripcion", "monto", "fecha", "tipo", "notas"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"})}