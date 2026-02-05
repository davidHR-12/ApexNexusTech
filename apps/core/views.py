from django.shortcuts import render
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from apps.pedidos.models import Pago
from apps.finanzas.models import Gasto
from apps.materiales.models import Material
from apps.pedidos.models import Pedido

def dashboard_admin(request):
    """
    Vista principal del dashboard administrativo.
    Muestra resumen de ingresos, gastos, utilidad y alertas de stock.
    """
    ahora = timezone.now()
    ingresos_mes = Pago.objects.filter(
        fecha_pago__month=ahora.month, fecha_pago__year=ahora.year
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    gastos_mes = Gasto.objects.filter(
        fecha__month=ahora.month, fecha__year=ahora.year
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    materiales = Material.objects.all().order_by("-stock_actual")
    total_gramos = materiales.aggregate(Sum("stock_actual"))[
        "stock_actual__sum"] or 0

    context = {
        "ingresos_mes": ingresos_mes,
        "gastos_mes": gastos_mes,
        "utilidad_neta": ingresos_mes - gastos_mes,
        "pedidos_activos": Pedido.objects.exclude(
            estado_pedido__in=["Entregado", "Cancelado"]
        ).count(),
        "total_kg": total_gramos / 1000,
        "materiales": materiales,
    }
    return render(request, "core/dashboard_admin.html", context)

def calculadora(request):
    return render(request, "core/calculadora.html")

def configuracion(request):
    return render(request, "core/configuracion.html")
