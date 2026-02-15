from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from .forms import GastoForm, GastoFormExtendido
from .models import Gasto
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Q
from datetime import date
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from apps.usuarios.decorators import admin_required

@admin_required
def gastos_list(request):
    """
    Lista los gastos registrados mostrando información clave simplificada:
    Fecha, Descripción, Categoría, Monto y Estado.
    Permite filtrar por tipo y buscar por descripción o proveedor.
    """
    gastos = Gasto.objects.all().order_by("-fecha", "-id")
    conteo = gastos.count()

    # Búsqueda por descripción o proveedor
    search_query = request.GET.get("search", "")
    if search_query:
        gastos = gastos.filter(
            Q(descripcion__icontains=search_query) |
            Q(proveedor__icontains=search_query)
        )
    
    # Filtro por tipo de gasto
    tipo_filtro = request.GET.get("tipo", "")
    if tipo_filtro:
        gastos = gastos.filter(tipo=tipo_filtro)
    
    # Cálculo de totales y promedios
    total_gastos = gastos.aggregate(Sum('monto'))['monto__sum'] or Decimal('0.00')
    promedio = total_gastos / conteo if conteo > 0 else 0

    context = {
        "gastos": gastos,
        "total_gastos": total_gastos,
        "tipos": Gasto.TIPOS,
        "search_query": search_query,
        "tipo_filtro": tipo_filtro,
        "promedio": promedio,
    }
    
    return render(request, "finanzas/gastos/gastos_list.html", context)


@login_required
def dashboard_finanzas(request):
    """
    Renderiza el dashboard de finanzas.
    Los datos de gráficos y KPIs se cargan de forma asíncrona vía AJAX desde gastos_por_mes().
    """
    return render(request, "finanzas/gastos/dashboard_gastos.html")


@admin_required
def gasto_detalle(request, gasto_id):
    """
    Vista detallada de un gasto que permite su edición.
    Maneja la actualización de datos y carga de comprobantes.
    Separa lógica de validación para gastos automáticos vs manuales.
    """
    gasto = get_object_or_404(Gasto, id=gasto_id)
    
    if request.method == "POST":
        data = request.POST.copy()
        files = request.FILES.copy() if request.FILES else {}
        
        # Validación: Gastos Automáticos vs Manuales
        if gasto.es_automatico:
            # Los gastos automáticos tienen campos protegidos que no deben modificarse
            data['monto'] = gasto.monto
            data['fecha'] = gasto.fecha
            data['tipo'] = gasto.tipo
        else:
            # Validación y limpieza de monto para gastos manuales
            try:
                monto_str = data.get("monto", "0").replace(",", "")
                data["monto"] = abs(Decimal(monto_str))
            except (ValueError, TypeError):
                messages.error(request, "El monto ingresado no es válido.")
                return redirect("finanzas:gasto_detalle", gasto_id=gasto_id)
        
        # Determinar si usar el formulario extendido (si hay comprobante o campos extra)
        usar_extendido = bool(files.get("comprobante")) or bool(data.get("proveedor"))
        FormClass = GastoFormExtendido if usar_extendido else GastoForm
        
        form = FormClass(data, files, instance=gasto) if usar_extendido else FormClass(data, instance=gasto)
        
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "✅ Gasto actualizado correctamente.")
            except Exception as e:
                messages.error(request, f"Error al guardar: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        
        return redirect("finanzas:gasto_detalle", gasto_id=gasto_id)
    
    context = {
        "gasto": gasto,
    }
    
    return render(request, "finanzas/gastos/gasto_detalle.html", context)

@admin_required
@require_http_methods(["POST"])
def crear_gasto(request):
    """
    Procesa la creación de un nuevo gasto.
    Maneja la limpieza de datos monetarios y redireccionamiento inteligente.
    """
    data = request.POST.copy()
    files = request.FILES.copy()
    
    try:
        # Limpieza y conversión del campo monto
        monto_str = data.get("monto", "0").replace(",", "")
        data["monto"] = abs(Decimal(monto_str))
    except (ValueError, TypeError):
        messages.error(request, "El monto ingresado no es válido.")
        return redirect("finanzas:gastos")

    # Verificar si es necesario usar el formulario extendido
    usar_extendido = any([
        files.get("comprobante"), 
        data.get("proveedor"), 
        data.get("numero_factura"), 
        data.get("es_recurrente")
    ])
    
    FormClass = GastoFormExtendido if usar_extendido else GastoForm
    form = FormClass(data, files)

    if form.is_valid():
        try:
            gasto = form.save()
            messages.success(request, "✅ Gasto registrado exitosamente.")
            
            # Redirección: Intentar volver a la URL previa si es segura, sino ir al detalle
            next_url = request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url, 
                allowed_hosts={request.get_host()}, 
                require_https=request.is_secure()
            ):
                return redirect(next_url)
            
            return redirect("finanzas:gasto_detalle", gasto_id=gasto.id)
            
        except Exception as e:
            messages.error(request, f"Error al guardar: {str(e)}")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect("finanzas:gastos")

@admin_required
@require_http_methods(["POST"])
def editar_gasto(request, gasto_id):
    """
    Edita un gasto existente manejando restricciones de campos.
    Los gastos automáticos (vinculados a inventario) tienen restricciones en
    monto, fecha y tipo para preservar integridad de datos.
    """
    gasto = get_object_or_404(Gasto, id=gasto_id)
    next_url = request.META.get('HTTP_REFERER', reverse('finanzas:gastos'))

    if request.method == "POST":
        data = request.POST.copy()
        files = request.FILES.copy() if request.FILES else {}
        
        # Validación de campos protegidos para gastos automáticos
        if gasto.es_automatico:
            data['monto'] = gasto.monto
            data['fecha'] = gasto.fecha
            data['tipo'] = gasto.tipo
        else:
            # Para gastos manuales, permitimos edición completa con validación
            try:
                monto_str = data.get("monto", "0").replace(",", "")
                data["monto"] = abs(Decimal(monto_str))
            except (ValueError, TypeError):
                messages.error(request, "El monto ingresado no es válido.")
                return redirect("finanzas:gastos")

        # Verificar uso de formulario extendido
        usar_extendido = (
            bool(files.get("comprobante")) or 
            bool(data.get("proveedor")) or 
            bool(data.get("numero_factura")) or
            bool(data.get("es_recurrente"))
        )
        
        FormClass = GastoFormExtendido if usar_extendido else GastoForm
        form = FormClass(data, files, instance=gasto) if usar_extendido else FormClass(data, instance=gasto)
        
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Gasto actualizado correctamente.")
            except Exception as e:
                messages.error(request, f"Error al actualizar: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
                
    return redirect(next_url)

@admin_required
def gasto_detalle_api(request, gasto_id):
    """
    API endpoint para obtener detalles de un gasto en formato JSON.
    Utilizado para carga dinámica en modales de edición.
    """
    gasto = get_object_or_404(Gasto, id=gasto_id)
    
    comprobante_url = None
    if gasto.comprobante:
        comprobante_url = gasto.comprobante.url
    
    data = {
        "id": gasto.id,
        "descripcion": gasto.descripcion,
        "monto": float(gasto.monto),
        "fecha": gasto.fecha.strftime('%Y-%m-%d'),
        "tipo": gasto.tipo,
        "notas": gasto.notas,
        "es_automatico": gasto.es_automatico,
        "proveedor": gasto.proveedor or "",
        "numero_factura": gasto.numero_factura or "",
        "comprobante": comprobante_url,
        "es_recurrente": gasto.es_recurrente,
    }
    return JsonResponse(data)

@admin_required
def eliminar_gasto(request, gasto_id):
    """
    Elimina un gasto del sistema.
    Impide la eliminación de gastos automáticos vinculados a inventario.
    """
    gasto = get_object_or_404(Gasto, id=gasto_id)
    
    if gasto.es_automatico:
        return JsonResponse({
            "success": False,
            "message": "No se pueden eliminar gastos automáticos. Elimina la entrada de inventario."
        })
    
    try:
        descripcion = str(gasto)
        gasto.delete()
        return JsonResponse({
            "success": True,
            "message": f"Gasto eliminado correctamente."
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error al eliminar: {str(e)}"
        })

@admin_required
def gastos_por_mes(request):
    """
    API endpoint para estadísticas de gastos.
    Retorna datos agrupados por mes y por tipo para visualización en gráficos.
    """
    tipo_filtro = request.GET.get("tipo", "")
    
    gastos = Gasto.objects.all()
    if tipo_filtro:
        gastos = gastos.filter(tipo=tipo_filtro)
    
    # Agrupación por mes para totales generales
    gastos_por_mes = {}
    for gasto in gastos:
        mes = gasto.fecha.strftime("%Y-%m")
        if mes not in gastos_por_mes:
            gastos_por_mes[mes] = Decimal("0.00")
        gastos_por_mes[mes] += gasto.monto
    
    # Agrupación por tipo y mes
    gastos_por_tipo = {}
    for tipo, _ in Gasto.TIPOS:
        gastos_tipo = Gasto.objects.filter(tipo=tipo)
        por_mes = {}
        for gasto in gastos_tipo:
            mes = gasto.fecha.strftime("%Y-%m")
            if mes not in por_mes:
                por_mes[mes] = Decimal("0.00")
            por_mes[mes] += gasto.monto
        gastos_por_tipo[tipo] = por_mes
    
    return JsonResponse({
        "meses": sorted(gastos_por_mes.keys()),
        "totales": [float(gastos_por_mes[m]) for m in sorted(gastos_por_mes.keys())],
        "por_tipo": {tipo: gastos_por_tipo[tipo] for tipo in gastos_por_tipo}
    })