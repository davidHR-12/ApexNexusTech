from django import forms
from apps.core.utils import TailwindModelForm
from apps.usuarios.models import Usuario
from apps.pedidos.models import SolicitudCotizacion
from .models import PerfilCliente
import re

class PerfilClienteForm(TailwindModelForm):
    class Meta:
        model = PerfilCliente
        fields = ['empresa', 'direccion', 'ciudad', 'codigo_postal', 'recibir_notificaciones']

class SolicitudCotizacionForm(TailwindModelForm):
    """
    Formulario para piezas personalizadas.
    Basado fielmente en apps.pedidos.models.SolicitudCotizacion
    """
    class Meta:
        model = SolicitudCotizacion
        fields = [
            'descripcion', 
            'imagen_referencia', 
            'enlace_referencia', 
            'dimensiones_aprox'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'placeholder': 'Cuéntanos qué quieres imprimir...'}),
            'dimensiones_aprox': forms.TextInput(attrs={'placeholder': 'Ej: 15cm de alto o escala 1:12'}),
            'enlace_referencia': forms.URLInput(attrs={'placeholder': 'Link de Thingiverse, Printables, etc.'}),
        }

class GuestCheckoutForm(forms.Form):
    """
    Checkout sin cuenta. NO crea usuarios.
    El correo es real y obligatorio para enviar confirmación.
    """
    nombre = forms.CharField(max_length=150, label="Nombre")
    apellido = forms.CharField(max_length=150, label="Apellido")
    telefono = forms.CharField(max_length=20, label="Teléfono / WhatsApp")
    email = forms.EmailField(label="Correo electrónico", 
                             help_text="Te enviaremos la confirmación de tu pedido aquí.")
    direccion = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Calle, No. Casa, Sector...'}),
        label="Dirección de Envío"
    )
    ciudad = forms.CharField(max_length=100, initial="Santo Domingo", label="Ciudad")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981] transition-all"
            })

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono and not re.match(r'^[0-9-]+$', telefono):
            raise forms.ValidationError("El teléfono solo debe contener números y guiones.")
        return telefono