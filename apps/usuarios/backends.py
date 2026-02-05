from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied
from .models import Usuario


class EmailVerifiedBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return None

        # 1. PRIMERO verificamos la contraseña
        if user.check_password(password):
            # 2. DESPUÉS verificamos si es cliente y si está verificado
            if user.rol == "Cliente" and not user.is_email_verified:
                # Lanzamos la excepción para que la vista la capture
                raise PermissionDenied("Email no verificado")
            return user

        return None
