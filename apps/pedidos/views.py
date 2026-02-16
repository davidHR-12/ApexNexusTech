from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from apps.usuarios.decorators import admin_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from .forms import PedidoManualForm, ItemCatalogoForm, ItemPersonalizadoForm
from .models import Pedido, ItemPedido, Impresora

# --- Helper: Lógica común del Dashboard (para no repetir código) ---
def _obtener_contexto_dashboard(request):
    # 1. Query Base
    pedidos_list = Pedido.objects.select_related('usuario').order_by('-fecha_creacion')

    # 2. Filtros
    estado_filtro = request.GET.get('estado')
    busqueda = request.GET.get('q')

    if estado_filtro:
        pedidos_list = pedidos_list.filter(estado_pedido=estado_filtro)

    if busqueda:
        pedidos_list = pedidos_list.filter(
            Q(id__icontains=busqueda) |
            Q(usuario__first_name__icontains=busqueda) |
            Q(usuario__email__icontains=busqueda)
        )

    # 3. KPIs
    kpis = {
        'pendientes': Pedido.objects.filter(estado_pedido__in=['En_Espera', 'Confirmado']).count(),
        'produccion': Pedido.objects.filter(estado_pedido='En_Produccion').count(),
        'listos': Pedido.objects.filter(estado_pedido='Listo').count(),
    }

    # 4. Paginación
    paginator = Paginator(pedidos_list, 10)
    page_number = request.GET.get('page')
    pedidos = paginator.get_page(page_number)

    return {
        'pedidos': pedidos,
        'kpis': kpis,
        'filtro_actual': estado_filtro,
        'busqueda_actual': busqueda,
        'estados_opciones': Pedido.ESTADOS_PEDIDO, 
    }

# ==========================================
#  VISTAS DE LECTURA (GET)
# ==========================================

@admin_required
def pedidos_list(request):
    """Solo muestra la lista y los modales vacíos"""
    context = _obtener_contexto_dashboard(request)
    context['form'] = PedidoManualForm() # Formulario vacío
    return render(request, 'pedidos/pedidos_list.html', context)

@admin_required
def pedido_detalle(request, pedido_id):
    """Solo muestra el detalle"""
    pedido = get_object_or_404(Pedido.objects.select_related('usuario', 'solicitud'), pk=pedido_id)
    items = pedido.items.all().select_related('variante__producto', 'impresora_asignada')
    
    context = {
        'pedido': pedido,
        'items': items,
        'pagos': pedido.pagos.all(),
        'impresoras': Impresora.objects.all(),
        'estados': Pedido.ESTADOS_PEDIDO,
        'form_catalogo': ItemCatalogoForm(), # Form vacío para el modal de items
        'form_personalizado': ItemPersonalizadoForm(), # Form vacío para el modal de items
    }
    return render(request, 'pedidos/pedido_detalle.html', context)

# ==========================================
#  ACCIONES (POST) - Vistas Dedicadas
# ==========================================

@require_POST
@admin_required
def crear_pedido_manual(request):
    form = PedidoManualForm(request.POST)
    if form.is_valid():
        nuevo_pedido = form.save(commit=False)
        # Inicializamos valores técnicos en 0
        nuevo_pedido.peso_estimado_g = 0
        nuevo_pedido.tiempo_estimado_h = 0
        nuevo_pedido.precio_total = 0
        nuevo_pedido.save()
        
        messages.success(request, f"Borrador de Pedido #{nuevo_pedido.id} creado. Ahora añade los materiales.")
        # Redirigimos directo al detalle para empezar a agregar materiales/productos
        return redirect('pedidos:pedido_detalle', pedido_id=nuevo_pedido.id)
    else:
        # Si falla, volvemos al dashboard con los errores
        context = _obtener_contexto_dashboard(request)
        context['form'] = form
        return render(request, 'pedidos/pedidos_list.html', context)

@admin_required
@require_POST
def agregar_item_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    tipo = request.POST.get('tipo_item')

    if tipo == 'catalogo':
        form = ItemCatalogoForm(request.POST)
    else:
        form = ItemPersonalizadoForm(request.POST)

    if form.is_valid():
        item = form.save(commit=False)
        item.pedido = pedido
        
        if tipo == 'catalogo':
            # 1. Usar el precio_final de la variante (Producto.precio_venta + Variante.precio_adicional)
            # Solo lo asignamos si el precio_unitario viene vacío o queremos forzar el del catálogo
            item.precio_unitario = item.variante.precio_final
            
            # 2. Otros datos automáticos
            item.descripcion = item.variante.producto.nombre
            item.gramos_por_unidad = item.variante.producto.peso_gramos
            item.costo_material_unitario = item.variante.costo_materiales
        else:
            # Logica para piezas unicas
            item.costo_material_unitario = item.material_personalizado.costo_por_gramo
            
        item.save()
        messages.success(request, "Item agregado Correctamente.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                # Si el error es del campo material, no mostramos el nombre del campo
                if field == 'material_personalizado' or field == '__all__':
                    messages.error(request, f"{error}")
                else:
                    # Para otros campos (precio, cantidad) mantenemos una referencia
                    label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f"{label}: {error}")
    
    return redirect('pedidos:pedido_detalle', pedido_id=pedido.id)


@admin_required
def editar_item_pedido(request, item_id):
    item = get_object_or_404(ItemPedido, id=item_id)
    FormClass = ItemCatalogoForm if item.variante else ItemPersonalizadoForm
    
    if request.method == 'POST':
        form = FormClass(request.POST, instance=item)
        if form.is_valid():
            item_editado = form.save(commit=False)
            
            # Si es catálogo, forzamos los gramos y el costo 
            # desde la variante original, ignorando cualquier intento de cambio.
            if item.variante:
                item_editado.gramos_por_unidad = item.variante.producto.peso_gramos
                item_editado.costo_material_unitario = item.variante.costo_materiales
            else:
                # Si es personalizado, recalculamos costo según material elegido
                item_editado.costo_material_unitario = item_editado.material_personalizado.costo_por_gramo
            
            item_editado.save()
            messages.success(request, "Ítem actualizado correctamente.")
            return redirect('pedidos:pedido_detalle', pedido_id=item.pedido.id)
    else:
        form = FormClass(instance=item)
    
    return render(request, 'pedidos/modals/editar_item.html', {
        'form': form,
        'item': item,
        'pedido': item.pedido,
        'modal_id': 'modalEditarItem'
    })

@admin_required
def eliminar_item_pedido(request, item_id):
    item = get_object_or_404(ItemPedido, id=item_id)
    try:
        item.delete() # Dispara señal para actualizar totales
        return JsonResponse({'success': True, 'message': 'Ítem eliminado correctamente.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@admin_required
def cambiar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    nuevo_estado = request.POST.get('nuevo_estado')
    
    if nuevo_estado:
        pedido.estado_pedido = nuevo_estado
        pedido.save()
        messages.success(request, f"Estado actualizado a {pedido.get_estado_pedido_display()}.")
    
    return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

@require_POST
@admin_required
def asignar_impresora_item(request, item_id):
    item = get_object_or_404(ItemPedido, pk=item_id)
    impresora_id = request.POST.get('impresora_id')
    
    if impresora_id:
        item.impresora_asignada_id = impresora_id
        item.save()
        messages.success(request, "Impresora asignada.")
        
    return redirect('pedidos:pedido_detalle', pedido_id=item.pedido.id)