from django import forms
from .models import Impresora
from apps.core.utils import TailwindModelForm

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