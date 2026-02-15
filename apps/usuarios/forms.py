from django import forms
from .models import Usuario
import uuid

class RegistroExpressClienteForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'telefono']

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono and not telefono.isdigit():
            raise forms.ValidationError("El teléfono solo debe contener números.")
        return telefono

    def save(self, commit=True):
        user = super().save(commit=False)
        user.rol = "Cliente"
        user.is_manual = True
        user.is_email_verified = False
        # Generamos un username aleatorio si no se provee email
        if not user.email:
            temp_id = uuid.uuid4().hex[:8]
            user.email = f"manual_{temp_id}@imp3d.com"
        
        user.username = user.email
        # Password aleatorio e inaccesible para que no puedan loguearse
        user.set_unusable_password() 
        
        if commit:
            user.save()
        return user

# ESTILO ÚNICO PARA FORMULARIOS
INPUT_CLASSES = "w-full bg-[#334155] border border-gray-600 rounded-xl p-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-[#10b981] focus:border-transparent outline-none transition-all"


class LoginForm(forms.Form):
    """
    Formulario de inicio de sesión estándar.
    """

    email = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "tu@correo.com"}
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "********"}
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
            attrs={"class": INPUT_CLASSES, "placeholder": "Mínimo 8 caracteres"}
        ),
    )
    confirm_password = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(
            attrs={"class": INPUT_CLASSES, "placeholder": "Repite tu contraseña"}
        ),
    )

    class Meta:
        model = Usuario
        # Añadimos first_name y last_name a la lista
        fields = ["first_name", "last_name", "username", "email", "telefono"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Tu nombre",
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Tu apellido",
                    "autocomplete": "family-name",
                }
            ),
            "username": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "Tu apodo (Opcional)",
                    "autocomplete": "username", # Cambiado de nickname a username para mejor soporte
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": INPUT_CLASSES,
                    "placeholder": "ejemplo@correo.com",
                    "autocomplete": "email",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": INPUT_CLASSES, 
                    "placeholder": "809-000-0000",
                    "autocomplete": "tel"
                }
            ),
        }

    def clean(self):
        """Valida que las contraseñas coincidan."""
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data
