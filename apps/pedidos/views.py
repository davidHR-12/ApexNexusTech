from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from .forms import PedidoManualForm, ItemPedidoForm
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

@login_required
@user_passes_test(lambda u: u.is_staff)
def pedidos_list(request):
    """Solo muestra la lista y los modales vacíos"""
    context = _obtener_contexto_dashboard(request)
    context['form'] = PedidoManualForm() # Formulario vacío
    return render(request, 'pedidos/pedidos_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
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
        'form_item': ItemPedidoForm(), # Form vacío para el modal de items
    }
    return render(request, 'pedidos/pedido_detalle.html', context)

# ==========================================
#  ACCIONES (POST) - Vistas Dedicadas
# ==========================================

@require_POST
@login_required
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

@require_POST
@login_required
def agregar_item_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    form = ItemPedidoForm(request.POST)
    
    if form.is_valid():
        item = form.save(commit=False)
        item.pedido = pedido
        
        # Validar consistencia antes de guardar
        if not item.gramos_por_unidad:
            item.gramos_por_unidad = 0.00

        # --- LÓGICA PARA CATÁLOGO (VARIANTE) ---
        if item.variante:
            # Si no hay descripción manual, usamos el nombre de la variante
            if not item.descripcion:
                item.descripcion = str(item.variante)
            if item.gramos_por_unidad == 0:
                item.gramos_por_unidad = item.variante.producto.peso_gramos
            
            # El precio unitario y gramos ya vienen del form (rellenados por JS),
            # pero el costo_material_unitario lo tomamos de la "receta" de la variante
            item.costo_material_unitario = item.variante.costo_materiales
        
        # Si es personalizado, guardamos el costo del material en ese momento
        if item.material_personalizado:
            item.costo_material_unitario = item.material_personalizado.costo_por_gramo
            # Si no puso descripción, usamos el nombre del material
            if not item.descripcion:
                item.descripcion = f"Pieza de {item.material_personalizado.nombre}"
        
        item.save()
        messages.success(request, "Ítem añadido correctamente.")
    else:
        messages.error(request, "Error: " + str(form.errors))
    
    return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

@login_required
def editar_item_pedido(request, item_id):
    item = get_object_or_404(ItemPedido, id=item_id)
    
    if request.method == 'POST':
        form = ItemPedidoForm(request.POST, instance=item)
        if form.is_valid():
            item_editado = form.save(commit=False)
            
            # Recalcular costos unitarios si cambió la variante o material
            if item_editado.variante:
                 item_editado.costo_material_unitario = item_editado.variante.costo_materiales
            elif item_editado.material_personalizado:
                 item_editado.costo_material_unitario = item_editado.material_personalizado.costo_por_gramo
            
            item_editado.save() # Dispara actualización de totales del pedido
            messages.success(request, "Ítem actualizado correctamente.")
            return redirect('pedidos:pedido_detalle', pedido_id=item.pedido.id)
    else:
        form = ItemPedidoForm(instance=item)
    
    return render(request, 'pedidos/modals/editar_item.html', {
        'form': form,
        'item': item,
        'pedido': item.pedido,
        'modal_id': 'modalEditarItem'
    })

@require_POST
@login_required
def eliminar_item_pedido(request, item_id):
    item = get_object_or_404(ItemPedido, id=item_id)
    try:
        item.delete() # Dispara señal para actualizar totales
        return JsonResponse({'success': True, 'message': 'Ítem eliminado correctamente.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@require_POST
@login_required
def cambiar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    nuevo_estado = request.POST.get('nuevo_estado')
    
    if nuevo_estado:
        pedido.estado_pedido = nuevo_estado
        pedido.save()
        messages.success(request, f"Estado actualizado a {pedido.get_estado_pedido_display()}.")
    
    return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

@require_POST
@login_required
def asignar_impresora_item(request, item_id):
    item = get_object_or_404(ItemPedido, pk=item_id)
    impresora_id = request.POST.get('impresora_id')
    
    if impresora_id:
        item.impresora_asignada_id = impresora_id
        item.save()
        messages.success(request, "Impresora asignada.")
        
    return redirect('pedidos:pedido_detalle', pedido_id=item.pedido.id)