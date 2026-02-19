from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

email_verification_token = PasswordResetTokenGenerator()


def send_verification_email(request, user):
    token = PasswordResetTokenGenerator().make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    verify_url = request.build_absolute_uri(
        reverse("usuarios:verificar_email", args=[uid, token])
    )

    subject = "Verifica tu cuenta"
    message = f"""
    Hola {user.get_full_name_or_user()},

    Para activar tu cuenta haz clic en el botón del siguiente enlace:

    {verify_url}

    Si no creaste esta cuenta, ignora este mensaje.
    """

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
