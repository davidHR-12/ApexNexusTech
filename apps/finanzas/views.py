from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .forms import GastoForm
from .models import Gasto
# Create your views here.

@login_required
def gastos_list(request):
    """
    Muestra la lista de gastos operativos y formulario para agregar nuevos.
    """
    gastos = Gasto.objects.all().order_by("-fecha", "-id")
    return render(
        request,
        "finanzas/gastos/gastos_admin.html",
        {"gastos": gastos, "form": GastoForm()},
    )

@login_required
def crear_gasto(request):
    """
    Registra un gasto operativo.
    """
    if request.method == "POST":
        # Copiamos los datos para poder limpiar el monto
        data = request.POST.copy()
        try:
            # Aseguramos que el monto sea positivo (el front-end lo muestra como resta)
            monto_str = data.get("monto", "0").replace(",", "")
            data["monto"] = abs(Decimal(monto_str))
        except (ValueError, TypeError):
            messages.error(request, "El monto ingresado no es válido.")
            return redirect("finanzas:gastos")

        form = GastoForm(data)
        if form.is_valid():
            form.save()
            messages.success(request, "Gasto registrado exitosamente.")
        else:
            # Si hay errores en el form, los pasamos a mensajes
            for error in form.errors.values():
                messages.error(request, error)

    return redirect("finanzas:gastos")