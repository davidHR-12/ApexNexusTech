from django import forms
from apps.core.utils import TailwindModelForm
from apps.pedidos.models import SolicitudCotizacion
from .models import PerfilCliente

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