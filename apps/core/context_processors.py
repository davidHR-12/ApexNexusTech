from apps.pedidos.models import SolicitudCotizacion


def solicitudes_kpi(request):
    """
    Inyecta el conteo de solicitudes pendientes en TODOS los templates.
    Así el circulito rojo del sidebar funciona en cualquier vista admin.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return {}

    count = SolicitudCotizacion.objects.filter(estado="Pendiente").count()

    return {
        "kpis": {
            "solicitudes_nuevas": count,
        }
    }