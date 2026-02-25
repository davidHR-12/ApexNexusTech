from django import forms
from .models import Impresora, CardPublica, ConfiguracionSitio
from apps.core.utils import TailwindModelForm


# ════════════════════════════════════════════════════════════════════
# IMPRESORAS
# ════════════════════════════════════════════════════════════════════

class ImpresoraForm(TailwindModelForm):
    """Formulario para crear/editar impresoras 3D."""
    
    class Meta:
        model = Impresora
        fields = ['nombre', 'modelo', 'estado']

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        query = Impresora.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        
        if query.exists():
            raise forms.ValidationError(f"La impresora '{nombre}' ya está registrada.")
        return nombre


# ════════════════════════════════════════════════════════════════════
# CARDS PÚBLICAS
# ════════════════════════════════════════════════════════════════════

class CardPublicaForm(TailwindModelForm):
    """
    Formulario para crear/editar cards (materiales y proceso).
    Incluye soporte para imágenes.
    """
    
    class Meta:
        model = CardPublica
        fields = [
            'seccion', 'titulo', 'descripcion', 'imagen', 
            'orden', 'activo',
            'badge_texto', 'badge_color', 'tags',  # Solo materiales
            'paso_numero', 'es_paso_destacado'      # Solo proceso
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={
                'placeholder': 'Ej: PLA Premium, Paso 1, etc.'
            }),
            'descripcion': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe el contenido...'
            }),
            'tags': forms.TextInput(attrs={
                'placeholder': 'Ej: Fácil de Pintar, Eco-Friendly'
            }),
            'badge_texto': forms.TextInput(attrs={
                'placeholder': 'Ej: Estético, Industrial'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        titulo = cleaned_data.get('titulo')
        
        if not titulo:
            raise forms.ValidationError("El título es obligatorio.")
        
        return cleaned_data


# ════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN SIMPLIFICADA
# ════════════════════════════════════════════════════════════════════

class EstadisticasForm(TailwindModelForm):
    """Formulario para las estadísticas."""
    
    class Meta:
        model = ConfiguracionSitio
        fields = [
            'stat_piezas_numero',
            'stat_piezas_etiqueta',
            'stat_respuesta_numero',
            'stat_respuesta_etiqueta',
            'stat_materiales_numero',
            'stat_materiales_etiqueta',
            'stat_garantia_numero',
            'stat_garantia_etiqueta',
        ]


class MaterialesForm(TailwindModelForm):
    """Formulario para la sección de materiales."""
    
    class Meta:
        model = ConfiguracionSitio
        fields = [
            'mostrar_materiales_en_index',
            'mostrar_materiales_en_pagina',
        ]


class ProductosDestacadosForm(TailwindModelForm):
    """Formulario para productos destacados."""
    
    class Meta:
        model = ConfiguracionSitio
        fields = [
            'mostrar_seccion_productos_destacados',
            'max_productos_destacados',
        ]

    def clean_max_productos_destacados(self):
        cantidad = self.cleaned_data.get('max_productos_destacados')
        if cantidad and (cantidad < 1 or cantidad > 8):
            raise forms.ValidationError("La cantidad debe estar entre 1 y 8.")
        return cantidad


class ProcesoForm(TailwindModelForm):
    """Formulario para la sección de proceso."""
    
    class Meta:
        model = ConfiguracionSitio
        fields = [
            'proceso_titulo',
            'proceso_subtitulo',
        ]
        widgets = {
            'proceso_subtitulo': forms.Textarea(attrs={'rows': 2}),
        }


class ContactoForm(TailwindModelForm):
    """Formulario para contacto y WhatsApp."""
    
    class Meta:
        model = ConfiguracionSitio
        fields = [
            'whatsapp_numero',
            'mostrar_boton_whatsapp',
            'email_contacto',
            'ciudad_contacto',
        ]
        widgets = {
            'whatsapp_numero': forms.TextInput(attrs={
                'placeholder': '18095551234',
                'pattern': '[0-9]{10,}'
            }),
            'email_contacto': forms.EmailInput(),
        }

    def clean_whatsapp_numero(self):
        numero = self.cleaned_data.get('whatsapp_numero')
        if numero:
            if not numero.isdigit():
                raise forms.ValidationError("Solo dígitos, sin espacios ni guiones.")
            if len(numero) < 10:
                raise forms.ValidationError("Mínimo 10 dígitos.")
        return numero