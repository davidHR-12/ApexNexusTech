from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .forms import GastoForm
from .models import Gasto
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

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

@login_required
def editar_gasto(request, gasto_id):
    """
    Edita un gasto existente. 
    Si es automático (de inventario), solo permite cambiar descripción y notas.
    """
    gasto = get_object_or_404(Gasto, id=gasto_id)
    
    if request.method == "POST":
        data = request.POST.copy()
        
        # Si el gasto es automático, forzamos los valores originales en campos críticos
        if gasto.es_automatico:
            data['monto'] = gasto.monto
            data['fecha'] = gasto.fecha
            data['tipo'] = gasto.tipo
        else:
            # Si es manual, limpiamos el monto como en crear_gasto
            try:
                monto_str = data.get("monto", "0").replace(",", "")
                data["monto"] = abs(Decimal(monto_str))
            except (ValueError, TypeError):
                messages.error(request, "El monto ingresado no es válido.")
                return redirect("finanzas:gastos")

        form = GastoForm(data, instance=gasto)
        if form.is_valid():
            form.save()
            messages.success(request, "Gasto actualizado correctamente.")
        else:
            for error in form.errors.values():
                messages.error(request, error)
                
    return redirect("finanzas:gastos")

@login_required
def gasto_detalle_api(request, gasto_id):
    gasto = get_object_or_404(Gasto, id=gasto_id)
    data = {
        "id": gasto.id,
        "descripcion": gasto.descripcion,
        "monto": float(gasto.monto),
        "fecha": gasto.fecha.strftime('%Y-%m-%d'),
        "tipo": gasto.tipo,
        "notas": gasto.notas,
        "es_automatico": gasto.es_automatico, # Clave para bloquear campos
    }
    return JsonResponse(data)