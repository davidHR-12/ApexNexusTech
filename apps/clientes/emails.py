"""
Utilidades de correo electrónico para la app clientes.
"""
import logging
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _get_config():
    try:
        from apps.core.models import ConfiguracionFactura
        config = ConfiguracionFactura.obtener()
        if config:
            return config
    except Exception:
        pass

    class _Default:
        nombre_negocio = "A.N.T Studio"
        slogan         = "Apex · Nexus · Technology"
        email          = getattr(settings, "DEFAULT_FROM_EMAIL", "")
        telefono       = ""
        logo           = None
    return _Default()


def _logo_url(config):
    if not getattr(config, "logo", None):
        return None
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    if not site_url:
        return None
    try:
        return f"{site_url}{config.logo.url}"
    except Exception:
        return None


def enviar_confirmacion_pedido_guest(pedido):
    if not pedido.guest_email:
        return

    config = _get_config()
    items = (
        pedido.items
        .filter(item_padre__isnull=True)
        .select_related("variante__producto")
        .prefetch_related("componentes")
    )
    filas_items = []
    for item in items:
        nombre = item.variante.producto.nombre if item.variante else (item.descripcion or "Producto personalizado")
        filas_items.append({"nombre": nombre, "cantidad": item.cantidad, "subtotal": item.subtotal})

    context = {
        "pedido": pedido, "filas_items": filas_items,
        "nombre": pedido.guest_nombre or "Cliente",
        "config": config, "logo_url": _logo_url(config),
    }
    html_content = render_to_string("emails/confirmacion_pedido_guest.html", context)
    subject = f"✅ Pedido #{pedido.id:04d} recibido — {config.nombre_negocio}"
    try:
        msg = EmailMultiAlternatives(subject, "", settings.DEFAULT_FROM_EMAIL, [pedido.guest_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info("Confirmación enviada a %s (Pedido #%s)", pedido.guest_email, pedido.id)
    except Exception as exc:
        logger.error("Error al enviar confirmación (Pedido #%s): %s", pedido.id, exc)


def enviar_email_verificacion(user, link, es_reenvio=False):
    config = _get_config()
    context = {
        "user": user, "link": link,
        "config": config, "logo_url": _logo_url(config),
        "es_reenvio": es_reenvio,
    }
    html_content = render_to_string("emails/verificacion_cuenta.html", context)
    subject = f"{'Reenvío: ' if es_reenvio else ''}Verifica tu cuenta — {config.nombre_negocio}"
    try:
        msg = EmailMultiAlternatives(subject, "", settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info("Verificación enviada a %s", user.email)
    except Exception as exc:
        logger.error("Error al enviar verificación a %s: %s", user.email, exc)


def enviar_reset_password(user, link):
    """
    Envía el correo de recuperación de contraseña.
    Llamado desde CustomPasswordResetForm en apps/usuarios/forms.py.
    Django genera el link con uid + token seguros — expira en 72 horas
    (configurable con PASSWORD_RESET_TIMEOUT en settings, valor en segundos).
    """
    config = _get_config()
    context = {
        "user": user, "link": link,
        "config": config, "logo_url": _logo_url(config),
    }
    html_content = render_to_string("emails/reset_password.html", context)
    subject = f"🔑 Recupera tu contraseña — {config.nombre_negocio}"
    try:
        msg = EmailMultiAlternatives(subject, "", settings.DEFAULT_FROM_EMAIL, [user.email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info("Reset password enviado a %s", user.email)
    except Exception as exc:
        logger.error("Error al enviar reset a %s: %s", user.email, exc)

def enviar_confirmacion_email_nuevo(user, email_nuevo, link):
    """
    Notifica al usuario que solicitó cambiar su email.
    Se envía al NUEVO correo (el que aún no está confirmado).
    """
    config = _get_config()
    context = {
        "user":       user,
        "email_nuevo": email_nuevo,
        "link":       link,
        "config":     config,
        "logo_url":   _logo_url(config),
    }
    html_content = render_to_string("emails/confirmar_email_nuevo.html", context)
    subject = f"✉ Confirma tu nuevo correo — {config.nombre_negocio}"
    try:
        msg = EmailMultiAlternatives(subject, "", settings.DEFAULT_FROM_EMAIL, [email_nuevo])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        logger.info("Confirmación de email nuevo enviada a %s (usuario %s)", email_nuevo, user.pk)
    except Exception as exc:
        logger.error("Error al enviar confirmación de email nuevo a %s: %s", email_nuevo, exc)
 