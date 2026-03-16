from django import forms
from .models import Impresora, CardPublica, ConfiguracionSitio, ConfiguracionCalculadora, ConfiguracionFactura
from apps.core.utils import TailwindModelForm

from apps.usuarios.models import Usuario
import re


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


_FIELD_CLASS = (
    "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 "
    "text-white outline-none focus:border-[#10b981] transition-all"
)
class PerfilForm(forms.ModelForm):
    # Campo independiente — NO parte del model field directo
    email_nuevo = forms.EmailField(
        required=False,
        label="Email",
        widget=forms.EmailInput(attrs={"class": _FIELD_CLASS, "placeholder": "tu@correo.com"}),
    )

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "telefono"]  # ← email FUERA
        widgets = {
            "first_name": forms.TextInput(attrs={"class": _FIELD_CLASS, "placeholder": "Tu nombre"}),
            "last_name":  forms.TextInput(attrs={"class": _FIELD_CLASS, "placeholder": "Tu apellido"}),
            "telefono":   forms.TextInput(attrs={"class": _FIELD_CLASS, "placeholder": "809-000-0000"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-poblar con el email actual
        if self.instance and self.instance.pk:
            self.fields["email_nuevo"].initial = self.instance.email

    def clean_email_nuevo(self):
        email = self.cleaned_data.get("email_nuevo", "").strip().lower()
        if email and email != self.instance.email.lower():
            if Usuario.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Este correo ya está registrado en otra cuenta.")
            if Usuario.objects.filter(pending_email=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("Este correo ya está siendo verificado por otra cuenta.")
        return email

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono", "")
        if telefono and not re.match(r'^[0-9-]+$', telefono):
            raise forms.ValidationError("El teléfono solo debe contener números y guiones.")
        return telefono
 
 
class CambioPasswordForm(forms.Form):
    """
    Cambio de contraseña con validación de la actual.
    """
    password_actual  = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput(attrs={"class": _FIELD_CLASS, "placeholder": "••••••••"}),
    )
    password_nuevo   = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": _FIELD_CLASS, "placeholder": "Mínimo 8 caracteres"}),
    )
    password_confirm = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": _FIELD_CLASS, "placeholder": "Repite la nueva contraseña"}),
    )
 
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
 
    def clean_password_actual(self):
        pw = self.cleaned_data.get("password_actual")
        if not self.user.check_password(pw):
            raise forms.ValidationError("La contraseña actual no es correcta.")
        return pw
 
    def clean(self):
        cleaned = super().clean()
        nuevo   = cleaned.get("password_nuevo")
        confirm = cleaned.get("password_confirm")
        if nuevo and confirm and nuevo != confirm:
            raise forms.ValidationError("Las nuevas contraseñas no coinciden.")
        if nuevo and len(nuevo) < 8:
            raise forms.ValidationError("La nueva contraseña debe tener al menos 8 caracteres.")
        return cleaned
 