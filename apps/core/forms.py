from django import forms
from .models import Impresora, CardPublica, ConfiguracionSitio, ConfiguracionCalculadora, ConfiguracionFactura
from apps.core.utils import TailwindModelForm


# ════════════════════════════════════════════════════════════════════
# IMPRESORAS
# ════════════════════════════════════════════════════════════════════

class ImpresoraForm(TailwindModelForm):
    class Meta:
        model  = Impresora
        fields = ['nombre', 'modelo']

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        query  = Impresora.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise forms.ValidationError(f"La impresora '{nombre}' ya está registrada.")
        return nombre


# ════════════════════════════════════════════════════════════════════
# CARDS PÚBLICAS
# ════════════════════════════════════════════════════════════════════

class CardPublicaForm(TailwindModelForm):
    class Meta:
        model  = CardPublica
        fields = [
            'seccion', 'titulo', 'descripcion', 'imagen',
            'orden', 'activo',
            'badge_texto', 'badge_color', 'tags',
            'paso_numero', 'es_paso_destacado',
        ]
        widgets = {
            'titulo':      forms.TextInput(attrs={'placeholder': 'Ej: PLA Premium, Paso 1, etc.'}),
            'descripcion': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe el contenido...'}),
            'tags':        forms.TextInput(attrs={'placeholder': 'Ej: Fácil de Pintar, Eco-Friendly'}),
            'badge_texto': forms.TextInput(attrs={'placeholder': 'Ej: Estético, Industrial'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('titulo'):
            raise forms.ValidationError("El título es obligatorio.")
        return cleaned_data


# ════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DEL SITIO
# ════════════════════════════════════════════════════════════════════

class EstadisticasForm(TailwindModelForm):
    class Meta:
        model  = ConfiguracionSitio
        fields = [
            'stat_piezas_numero',     'stat_piezas_etiqueta',
            'stat_respuesta_numero',  'stat_respuesta_etiqueta',
            'stat_materiales_numero', 'stat_materiales_etiqueta',
            'stat_garantia_numero',   'stat_garantia_etiqueta',
        ]


class MaterialesForm(TailwindModelForm):
    class Meta:
        model  = ConfiguracionSitio
        fields = ['mostrar_materiales_en_index', 'mostrar_materiales_en_pagina']


class ProductosDestacadosForm(TailwindModelForm):
    class Meta:
        model  = ConfiguracionSitio
        fields = ['mostrar_seccion_productos_destacados', 'max_productos_destacados']

    def clean_max_productos_destacados(self):
        cantidad = self.cleaned_data.get('max_productos_destacados')
        if cantidad and not (1 <= cantidad <= 8):
            raise forms.ValidationError("La cantidad debe estar entre 1 y 8.")
        return cantidad


class ProcesoForm(TailwindModelForm):
    class Meta:
        model   = ConfiguracionSitio
        fields  = ['proceso_titulo', 'proceso_subtitulo']
        widgets = {'proceso_subtitulo': forms.Textarea(attrs={'rows': 2})}


class ContactoForm(TailwindModelForm):
    class Meta:
        model  = ConfiguracionSitio
        fields = [
            'whatsapp_numero', 'instagram_url',
            'mostrar_boton_whatsapp', 'mostrar_boton_instagram',
            'email_contacto', 'ciudad_contacto',
        ]
        widgets = {
            'whatsapp_numero': forms.TextInput(attrs={'placeholder': '18095551234', 'pattern': '[0-9]{10,}'}),
            'email_contacto':  forms.EmailInput(),
            'instagram_url':   forms.URLInput(attrs={'placeholder': 'https://www.instagram.com/ant_printer_3d/'}),
        }

    def clean_instagram_url(self):
        url = self.cleaned_data.get('instagram_url')
        if url and not url.startswith('https://www.instagram.com/'):
            raise forms.ValidationError("La URL debe comenzar con 'https://www.instagram.com/'.")
        return url

    def clean_whatsapp_numero(self):
        numero = self.cleaned_data.get('whatsapp_numero')
        if numero:
            if not numero.isdigit():
                raise forms.ValidationError("Solo dígitos, sin espacios ni guiones.")
            if len(numero) < 10:
                raise forms.ValidationError("Mínimo 10 dígitos.")
        return numero


# ════════════════════════════════════════════════════════════════════
# CALCULADORA
# ════════════════════════════════════════════════════════════════════

_CALC_FIELDS = [
    'precio_kg', 'precio_kwh', 'consumo_watts',
    'vida_util_horas', 'precio_repuestos',
    'margen_error_porcentaje', 'multiplicador_ganancia',
]

class ConfiguracionCalculadoraForm(TailwindModelForm):
    class Meta:
        model   = ConfiguracionCalculadora
        fields  = _CALC_FIELDS
        widgets = {f: forms.NumberInput(attrs={'step': '0.01'}) for f in _CALC_FIELDS}


# ════════════════════════════════════════════════════════════════════
# FACTURA
# ════════════════════════════════════════════════════════════════════

class ConfiguracionFacturaForm(TailwindModelForm):
    class Meta:
        model   = ConfiguracionFactura
        fields  = [
            'nombre_negocio', 'slogan', 'rnc',
            'telefono', 'email', 'direccion',
            'logo', 'footer_texto', 'nota_legal',
        ]
        widgets = {
            'footer_texto': forms.Textarea(attrs={'rows': 2}),
            'nota_legal':   forms.Textarea(attrs={'rows': 2}),
        }