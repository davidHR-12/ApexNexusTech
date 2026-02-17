from django import forms
from .models import Impresora

class TailwindModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "rounded border-gray-700 text-[#10b981] focus:ring-[#10b981] bg-gray-900"
            else:
                field.widget.attrs["class"] = "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981]"

class ImpresoraForm(TailwindModelForm):
    class Meta:
        model = Impresora
        fields = ['nombre', 'modelo', 'estado']

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        # Verificamos si ya existe
        if Impresora.objects.filter(nombre__iexact=nombre).exists():
            # Personalizamos el mensaje con f-string
            raise forms.ValidationError(f"La impresora '{nombre}' ya está registrada en el sistema.")
        return nombre