from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import PerfilCliente

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def manejar_perfil_usuario(sender, instance, created, **kwargs):
    """
    Crea un PerfilCliente automáticamente cuando se crea un nuevo Usuario.
    También guarda el perfil si el usuario se actualiza.
    """
    if created:
        # Solo creamos el perfil si el rol es 'Cliente' 
        # (Opcional: puedes quitar el if si quieres perfil para todos)
        if instance.rol == "Cliente":
            PerfilCliente.objects.create(usuario=instance)
    else:
        # Si el usuario ya existe y tiene perfil, lo guardamos por si acaso
        if hasattr(instance, 'perfil_cliente'):
            instance.perfil_cliente.save()