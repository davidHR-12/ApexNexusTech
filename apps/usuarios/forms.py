from django import forms
from .models import Usuario
import uuid
import re

class TailwindModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "rounded border-gray-700 text-[#10b981] focus:ring-[#10b981] bg-gray-900"
            elif isinstance(field.widget, (forms.FileInput, forms.ClearableFileInput)):
                field.widget.attrs["class"] = "w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-gray-800 file:text-emerald-400 hover:file:bg-gray-700"
            else:
                field.widget.attrs["class"] = "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981]"

class RegistroExpressClienteForm(TailwindModelForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        
        if telefono:
            # Permitimos números y guiones, pero nada más.
            # La regex r'^[0-9-]+$' significa: desde el inicio hasta el fin, 
            # solo se aceptan dígitos del 0 al 9 y el carácter '-'
            if not re.match(r'^[0-9-]+$', telefono):
                raise forms.ValidationError("El teléfono solo debe contener números y guiones.")
        
        return telefono

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rol = "Cliente"
        user.is_manual = True
        user.is_email_verified = False
        
        if not user.email:
            temp_id = uuid.uuid4().hex[:8]
            user.email = f"manual_{temp_id}@imp3d.com"
        
        user.username = user.email
        user.set_unusable_password() 
        
        if commit:
            user.save()
        return user

class CompraRapidaForm(forms.Form):
    """
    Formulario combinado para crear un usuario y su perfil de cliente
    en un solo paso durante la compra.
    """
    nombre = forms.CharField(max_length=150, label="Nombre")
    apellido = forms.CharField(max_length=150, label="Apellido")
    telefono = forms.CharField(max_length=20, label="Teléfono / WhatsApp")
    email = forms.EmailField(required=False, label="Email (Opcional)")
    
    # Campos de dirección para el envío
    direccion = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Calle, No. Casa, Sector...'}),
        label="Dirección de Envío"
    )
    ciudad = forms.CharField(max_length=100, initial="Santo Domingo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicamos estilos Tailwind a todos los campos
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "w-full bg-[#0f172a] border border-gray-700 rounded-xl px-4 py-3 text-white outline-none focus:border-[#10b981]"
            })

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono and not re.match(r'^[0-9-]+$', telefono):
            raise forms.ValidationError("El teléfono solo debe contener números y guiones.")
        return telefono

    def verificar_reincidencia(self):
        """
        Retorna el usuario si el teléfono ya existe en la base de datos.
        Esto nos servirá para decidir si pedimos verificación.
        """
        telefono = self.cleaned_data.get('telefono')
        return Usuario.objects.filter(telefono=telefono).first()

class LoginForm(forms.Form):
    """
    Formulario de inicio de sesión estándar.
    """

    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(
            attrs={"class": "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all", "placeholder": "tu@correo.com"}
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all", "placeholder": "********"}
        ),
    )


class RegistroForm(forms.ModelForm):
    """
    Formulario de registro para nuevos usuarios.
    Incluye campos de nombre real y validación de contraseña.
    """

    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all", "placeholder": "Mínimo 8 caracteres"}
        ),
    )
    confirm_password = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all", "placeholder": "Repite tu contraseña"}
        ),
    )

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "username", "email", "telefono"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all",
                    "placeholder": "Tu nombre",
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all",
                    "placeholder": "Tu apellido",
                    "autocomplete": "family-name",
                }
            ),
            "username": forms.TextInput(
                attrs={
                    "class": "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all",
                    "placeholder": "Tu apodo (Opcional)",
                    "autocomplete": "username",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all",
                    "placeholder": "ejemplo@correo.com",
                    "autocomplete": "email",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all", 
                    "placeholder": "809-000-0000",
                    "autocomplete": "tel"
                }
            ),
        }

    def clean_telefono(self):
        """Valida que el teléfono solo contenga números y guiones."""
        telefono = self.cleaned_data.get('telefono')
        
        if telefono:
            # Regex que permite solo dígitos y guiones
            if not re.match(r'^[0-9-]+$', telefono):
                raise forms.ValidationError("El teléfono solo debe contener números y guiones.")
        
        return telefono

    def clean(self):
        """Valida que las contraseñas coincidan."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        
        return cleaned_data
