# importaciones de django
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.utils import timezone

# importaciones para verificar el correo electrónico
from django.http import HttpResponse
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import PermissionDenied
from .utils import email_verification_token

# importaciones del modelo y formulario
from .models import Usuario
from .forms import LoginForm, RegistroForm
from .forms import RegistroExpressClienteForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse

@login_required
@user_passes_test(lambda u: u.is_staff)
def api_crear_cliente_express(request):
    if request.method == 'POST':
        form = RegistroExpressClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            return JsonResponse({
                'success': True,
                'id': cliente.id,
                'nombre': cliente.get_full_name_or_user(),
                'email': cliente.email,
                'telefono': cliente.telefono,
            })
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    return JsonResponse({'success': False}, status=405)

# Vista de registro
def registro_view(request):
    """
    Maneja el registro de nuevos clientes.
    """
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            es_primer_usuario = not Usuario.objects.exists()
            user = form.save(commit=False)
            # Si el username está vacío, usamos el email
            if not user.username:
                user.username = user.email
            # Encriptamos la contraseña antes de guardar
            user.set_password(form.cleaned_data["password"])
            user.is_active = True

            # Si es el primer usuario, lo marcamos como administrador
            if es_primer_usuario:
                user.rol = "Admin"
                user.is_staff = True
                user.is_superuser = True
                user.is_email_verified = True
            else:  # Si no es el primer usuario, lo marcamos como cliente
                user.rol = "Cliente"
                user.is_staff = False
                user.is_superuser = False
                user.is_email_verified = False
            user.save()

            if not es_primer_usuario:
                # Generamos el token y el uid
                token = email_verification_token.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                # Construimos el link de verificación
                link = request.build_absolute_uri(
                    reverse(
                        "usuarios:verificar_email",
                        kwargs={"uidb64": uid, "token": token},
                    )
                )

                # Enviamos el correo electrónico
                subject = "Verifica tu cuenta"
                from_email = settings.EMAIL_HOST_USER
                to = [user.email]

                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Verificación de cuenta</h2>
                    <p>Hola,</p>
                    <p>Gracias por registrarte. Para activar tu cuenta haz clic en el botón:</p>

                    <a href="{link}"
                    style="
                    display:inline-block;
                    padding:12px 20px;
                    background-color:#22c55e;
                    color:white;
                    text-decoration:none;
                    border-radius:6px;
                    font-weight:bold;
                    ">
                    Verificar cuenta
                    </a>

                    <p style="margin-top:20px;">
                        Si no solicitaste este registro, puedes ignorar este correo.
                    </p>
                </body>
                </html>
                """

                email = EmailMultiAlternatives(subject, "", from_email, to)
                email.attach_alternative(html_content, "text/html")
                email.send()

                messages.success(
                    request, "Cuenta creada. Revisa tu correo para verificar tu cuenta."
                )
            else:
                messages.success(
                    request,
                    "Cuenta de administrador creada correctamente. Ya puedes iniciar sesión.",
                )
            return redirect("usuarios:login")
    else:
        form = RegistroForm()
    return render(
        request,
        "usuarios/registro.html",
        {
            "form": form,
            "creando_admin": not Usuario.objects.exists(),
        },
    )


# Vista para verificar el correo electrónico
def verificar_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Usuario.objects.get(pk=uid)
    except:
        user = None

    if user and email_verification_token.check_token(user, token):
        user.is_email_verified = True
        user.save()
        messages.success(
            request, "Cuenta verificada correctamente. Ya puedes iniciar sesión."
        )
        return redirect("usuarios:login")  # nombre de tu url de login
    else:
        return HttpResponse("El enlace es inválido o ha expirado")


def reenviar_verificacion(request):
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = Usuario.objects.get(email=email)

            # 1. Validación de tiempo (Anti-Spam)
            ahora = timezone.now()
            if user.last_verification_email:
                diferencia = (
                    ahora - user.last_verification_email).total_seconds()
                if diferencia < 120:
                    segundos_restantes = int(120 - diferencia)
                    messages.warning(
                        request,
                        f"Por favor, espera {segundos_restantes} segundos antes de solicitar otro reenvío.",
                    )
                    return redirect("usuarios:login")

            if user.is_email_verified:
                messages.info(request, "Esta cuenta ya está verificada.")
                return redirect("usuarios:login")

            # 2. Generación de Link y Envío (Tu lógica actual)
            token = email_verification_token.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            link = request.build_absolute_uri(
                reverse(
                    "usuarios:verificar_email", kwargs={"uidb64": uid, "token": token}
                )
            )

            subject = "Reenvío de verificación de cuenta"
            from_email = settings.EMAIL_HOST_USER

            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Verifica tu cuenta</h2>
                    <p>Haz clic en el botón para activar tu cuenta:</p>
                    <a href="{link}" style="display:inline-block; padding:12px 20px; background-color:#22c55e; color:white; text-decoration:none; border-radius:6px; font-weight:bold;">
                        Verificar cuenta
                    </a>
                </body>
            </html>
            """

            email_msg = EmailMultiAlternatives(
                subject, "", from_email, [user.email])
            email_msg.attach_alternative(html_content, "text/html")
            email_msg.send()

            # 3. ACTUALIZAR la base de datos con el momento del envío
            user.last_verification_email = ahora
            user.save(update_fields=["last_verification_email"])

            messages.success(
                request, "Se ha enviado un nuevo enlace de activación a tu correo."
            )

        except Usuario.DoesNotExist:
            # Mensaje genérico por seguridad
            messages.info(
                request, "Si el correo es válido, recibirás un enlace pronto."
            )

        return redirect("usuarios:login")

    return redirect("usuarios:login")


# Vista de login
def login_view(request):
    # Recuperamos el email de la sesión si existe (usando pop)
    email_no_verificado = request.session.pop("email_no_verificado", None)

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")

            # Intentamos autenticar
            try:
                user_auth = authenticate(
                    request, email=email, password=password)

                if user_auth is not None:
                    login(request, user_auth)
                    if user_auth.is_superuser or user_auth.is_staff:
                        return redirect("core:dashboard-admin")
                    return redirect("clientes:home")
                else:
                    # SI ES NONE, verificamos manualmente si el usuario existe y su clave es correcta
                    # pero simplemente no está verificado.
                    user_existente = Usuario.objects.filter(
                        email=email).first()

                    if user_existente and user_existente.check_password(password):
                        if not user_existente.is_email_verified:
                            messages.warning(
                                request, "Tu cuenta no ha sido verificada aún."
                            )
                            request.session["email_no_verificado"] = email
                            return redirect("usuarios:login")

                    # Si no es el caso anterior, es un error de login normal
                    messages.error(request, "Correo o contraseña incorrectos")

            except PermissionDenied:
                # Por si tu backend sí logra propagar la excepción
                messages.warning(
                    request, "Tu cuenta no ha sido verificada aún.")
                request.session["email_no_verificado"] = email
                return redirect("usuarios:login")

    else:
        form = LoginForm()

    return render(
        request,
        "usuarios/login.html",
        {
            "form": form,
            "email_no_verificado": email_no_verificado,
        },
    )
