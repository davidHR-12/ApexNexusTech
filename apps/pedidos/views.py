from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from apps.usuarios.decorators import admin_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from .forms import PedidoManualForm, ItemCatalogoForm, ItemPersonalizadoForm
from .models import Pedido, ItemPedido, Impresora, SolicitudCotizacion

# ==========================================
#  VISTAS DE LECTURA Y DASHBOARD
# ==========================================


def _obtener_contexto_dashboard(request):
    pedidos_list = Pedido.objects.select_related("usuario").order_by("-fecha_creacion")
    print(f"DEBUG: Total pedidos en DB: {Pedido.objects.count()}")
    estado_filtro = request.GET.get("estado")
    busqueda = request.GET.get("q")

    if estado_filtro:
        pedidos_list = pedidos_list.filter(estado_pedido=estado_filtro)

    if busqueda:
        pedidos_list = pedidos_list.filter(
            Q(id__icontains=busqueda)
            | Q(usuario__first_name__icontains=busqueda)
            | Q(usuario__email__icontains=busqueda)
        )

    kpis = {
        "pendientes": Pedido.objects.filter(
            estado_pedido__in=["En_Espera", "Confirmado"]
        ).count(),
        "produccion": Pedido.objects.filter(estado_pedido="En_Produccion").count(),
        "listos": Pedido.objects.filter(estado_pedido="Listo").count(),
        "solicitudes_nuevas": SolicitudCotizacion.objects.filter(
            estado="Pendiente"
        ).count(),
    }

    paginator = Paginator(pedidos_list, 10)
    pedidos = paginator.get_page(request.GET.get("page"))

    return {
        "pedidos": pedidos,
        "kpis": kpis,
        "filtro_actual": estado_filtro,
        "busqueda_actual": busqueda,
        "estados_opciones": Pedido.ESTADOS_PEDIDO,
    }


@admin_required
def pedidos_list(request):
    context = _obtener_contexto_dashboard(request)
    context["form"] = PedidoManualForm()
    context["segment"] = "pedidos"
    return render(request, "pedidos/pedidos_list.html", context)


@admin_required
def pedido_detalle(request, pedido_id):
    pedido = get_object_or_404(
        Pedido.objects.select_related("usuario", "solicitud"), pk=pedido_id
    )
    items = pedido.items.all().select_related(
        "variante__producto", "impresora_asignada"
    )
    solicitudes_pendientes = SolicitudCotizacion.objects.filter(
        estado="Pendiente"
    ).count()

    context = {
        "pedido": pedido,
        "items": items,
        "pagos": pedido.pagos.all(),
        "impresoras": Impresora.objects.all(),
        "estados": Pedido.ESTADOS_PEDIDO,
        "form_catalogo": ItemCatalogoForm(),
        "form_personalizado": ItemPersonalizadoForm(),
        "segment": "pedidos",
        "kpis": {"solicitudes_nuevas": solicitudes_pendientes},
    }
    return render(request, "pedidos/pedido_detalle.html", context)


# ==========================================
#  SERVICIOS AUXILIARES (LÓGICA DE NEGOCIO)
# ==========================================


def _validar_requisitos_produccion(pedido, request):
    """Verifica si los items que necesitan impresión tienen máquina asignada."""
    items_sin_maquina = []
    for item in pedido.items.all():
        necesita_impresion = False
        if item.material_personalizado:
            necesita_impresion = True
        elif item.variante and item.variante.stock_disponible < item.cantidad:
            necesita_impresion = True

        if necesita_impresion and not item.impresora_asignada:
            items_sin_maquina.append(item)

    if items_sin_maquina:
        messages.error(
            request,
            "Error: Hay productos que requieren impresión (Personalizados o Sin Stock) y no tienen máquina asignada.",
        )
        return False
    return True


def _revertir_stock_y_liberar(pedido, request):
    """Devuelve materiales al inventario y libera las impresoras físicamente."""
    # 1. Devolver Stock
    for item in pedido.items.all():
        if item.variante:
            item.variante.stock_disponible += item.cantidad
            item.variante.save()
        elif item.material_personalizado:
            gramos = item.gramos_por_unidad * item.cantidad
            item.material_personalizado.stock_actual += gramos
            item.material_personalizado.save()

    # 2. Liberar Impresoras FÍSICAMENTE (Sin borrar la asignación del ítem)
    items_con_maquina = pedido.items.filter(impresora_asignada__isnull=False)
    for item in items_con_maquina:
        maquina = item.impresora_asignada
        # Solo la liberamos si estaba imprimiendo
        if maquina.estado == "Imprimiendo":
            maquina.estado = "Disponible"
            maquina.save()

    pedido.stock_descontado = False
    messages.warning(
        request,
        "Inventario restaurado. Las máquinas han quedado libres para otros pedidos.",
    )

    for item in items_con_maquina:
        # A. Ponemos la máquina física en 'Disponible'
        maquina = item.impresora_asignada
        maquina.estado = "Disponible"
        maquina.save()

        # B. Ahora sí, borramos la asignación del pedido
        item.impresora_asignada = None
        item.save()

    pedido.stock_descontado = False
    messages.warning(
        request, "Inventario restaurado y máquinas liberadas a estado 'Disponible'."
    )


def _procesar_pedido_fallido(pedido, request):
    """Devuelve stock de catálogo pero quema el stock personalizado."""
    productos_devueltos = False
    for item in pedido.items.all():
        if item.variante:
            item.variante.stock_disponible += item.cantidad
            item.variante.save()
            productos_devueltos = True

    if productos_devueltos:
        messages.info(
            request,
            "Productos de catálogo devueltos. El filamento personalizado se registró como pérdida.",
        )
    else:
        messages.error(
            request,
            "Pérdida registrada: El filamento personalizado no regresó al stock.",
        )


def _descontar_stock(pedido, nuevo_estado, request):
    """Consume el stock del inventario."""
    for item in pedido.items.all():
        if item.variante:
            item.variante.stock_disponible -= item.cantidad
            item.variante.save()
        elif item.material_personalizado:
            gramos = item.gramos_por_unidad * item.cantidad
            item.material_personalizado.stock_actual -= gramos
            item.material_personalizado.save()

    pedido.stock_descontado = True

    if nuevo_estado == "Fallido":
        messages.error(
            request, "Stock procesado y marcado como pérdida por error de impresión."
        )
    else:
        messages.info(
            request, "Inventario actualizado: Material apartado para producción."
        )


def _gestionar_ciclo_vida_impresoras(pedido, nuevo_estado, request):
    """Cambia el estado de las máquinas físicas."""
    items_con_maquina = pedido.items.filter(impresora_asignada__isnull=False)

    if nuevo_estado == "En_Produccion":
        for item in items_con_maquina:
            maquina = item.impresora_asignada
            # Solo pasamos a imprimiendo si estaba disponible
            if maquina.estado == "Disponible":
                maquina.estado = "Imprimiendo"
                maquina.save()
        messages.info(
            request, "Las impresoras asignadas ahora están en estado 'Imprimiendo'."
        )

    elif nuevo_estado in ["Entregado", "Listo", "Cancelado", "Fallido"]:
        for item in items_con_maquina:
            maquina = item.impresora_asignada
            maquina.estado = "Disponible"
            maquina.save()


# ==========================================
#  VISTA PRINCIPAL REFACTORIZADA
# ==========================================


@admin_required
def cambiar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    nuevo_estado = request.POST.get("nuevo_estado")

    # 1. Validación de seguridad
    if pedido.estado_pedido in ["Entregado", "Cancelado"]:
        messages.error(request, "No se puede modificar un pedido finalizado.")
        return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    if not nuevo_estado:
        return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    # 2. Validación de Producción (Impresoras obligatorias)
    if nuevo_estado == "En_Produccion":
        if not _validar_requisitos_produccion(pedido, request):
            return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    # 3. Lógica de Stock e Inventario
    estados_consumo = ["Confirmado", "En_Produccion", "Listo", "Entregado", "Fallido"]

    # CASO A: Reversión (Volver atrás)
    if nuevo_estado in ["En_Espera", "Cancelado"] and pedido.stock_descontado:
        _gestionar_ciclo_vida_impresoras(pedido, nuevo_estado, request)
        _revertir_stock_y_liberar(pedido, request)

    # CASO B: Fallo (Manejo especial de pérdida)
    elif nuevo_estado == "Fallido" and pedido.stock_descontado:
        _procesar_pedido_fallido(pedido, request)
        _gestionar_ciclo_vida_impresoras(pedido, nuevo_estado, request)

    # CASO C: Consumo (Avanzar)
    elif nuevo_estado in estados_consumo:
        # Si aún no se ha descontado, descontamos
        if not pedido.stock_descontado:
            _descontar_stock(pedido, nuevo_estado, request)

        # Gestión de máquinas (Poner a Imprimir o Liberar si ya terminó)
        _gestionar_ciclo_vida_impresoras(pedido, nuevo_estado, request)

    # 4. Guardado Final
    pedido.estado_pedido = nuevo_estado
    pedido.save()

    messages.success(
        request, f"Estado actualizado a {pedido.get_estado_pedido_display()}."
    )
    return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)


# ==========================================
#  OTRAS ACCIONES (CREAR, EDITAR, ELIMINAR)
# ==========================================


@require_POST
@admin_required
def crear_pedido_manual(request):
    form = PedidoManualForm(request.POST)
    if form.is_valid():
        nuevo_pedido = form.save(commit=False)
        nuevo_pedido.peso_estimado_g = 0
        nuevo_pedido.tiempo_estimado_h = 0
        nuevo_pedido.precio_total = 0
        nuevo_pedido.save()
        messages.success(
            request,
            f"Borrador de Pedido #{nuevo_pedido.id} creado. Ahora añade los materiales.",
        )
        return redirect("pedidos:pedido_detalle", pedido_id=nuevo_pedido.id)
    else:
        context = _obtener_contexto_dashboard(request)
        context["form"] = form
        context["segment"] = "pedidos"
        return render(request, "pedidos/pedidos_list.html", context)


@admin_required
@require_POST
def agregar_item_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    if getattr(pedido, "stock_descontado", False):
        messages.error(
            request,
            "No puedes añadir ítems a un pedido que ya procesó inventario. Regresa el estado a 'En Espera' primero.",
        )
        return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)

    tipo = request.POST.get("tipo_item")
    form = (
        ItemCatalogoForm(request.POST)
        if tipo == "catalogo"
        else ItemPersonalizadoForm(request.POST)
    )

    if form.is_valid():
        item = form.save(commit=False)
        item.pedido = pedido
        if tipo == "catalogo":
            item.precio_unitario = item.variante.precio_final
            item.descripcion = item.variante.producto.nombre
            item.gramos_por_unidad = item.variante.producto.peso_gramos
            item.costo_material_unitario = item.variante.costo_materiales
        else:
            item.costo_material_unitario = item.material_personalizado.costo_por_gramo
        item.save()
        messages.success(request, "Item agregado Correctamente.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                (
                    messages.error(request, f"{error}")
                    if field in ["material_personalizado", "__all__"]
                    else messages.error(request, f"{field}: {error}")
                )

    return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)


@admin_required
def editar_item_pedido(request, item_id):
    item = get_object_or_404(ItemPedido, id=item_id)
    FormClass = ItemCatalogoForm if item.variante else ItemPersonalizadoForm

    if getattr(item.pedido, "stock_descontado", False):
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "message": "Pedido bloqueado: El stock ya fue descontado.",
                },
                status=400,
            )
        messages.error(
            request, "No se puede editar un ítem de un pedido con stock procesado."
        )
        return redirect("pedidos:pedido_detalle", pedido_id=item.pedido.id)

    if request.method == "POST":
        form = FormClass(request.POST, instance=item)
        if form.is_valid():
            item_editado = form.save(commit=False)
            if item.variante:
                item_editado.gramos_por_unidad = item.variante.producto.peso_gramos
                item_editado.costo_material_unitario = item.variante.costo_materiales
            else:
                item_editado.costo_material_unitario = (
                    item_editado.material_personalizado.costo_por_gramo
                )
            item_editado.save()
            messages.success(request, "Ítem actualizado correctamente.")
            return redirect("pedidos:pedido_detalle", pedido_id=item.pedido.id)
    else:
        form = FormClass(instance=item)
    
    context = _obtener_contexto_dashboard(request)
    context["form"] = form
    context["item"] = item
    context["pedido"] = item.pedido
    context["modal_id"] = "modalEditarItem"
    context["segment"] = "pedidos"
    context["title"] = "Editar Ítem del Pedido"
    context["description"] = "Modifica los valores de la pieza seleccionada"
    context["max_width"] = "max-w-2xl"

    return render(
        request,
        "pedidos/modals/editar_item.html",
        context
    )


@admin_required
def eliminar_item_pedido(request, item_id):
    item = get_object_or_404(ItemPedido, id=item_id)
    if getattr(item.pedido, "stock_descontado", False):
        return JsonResponse(
            {
                "success": False,
                "message": "No se puede eliminar un ítem de un pedido que ya descontó materiales.",
            },
            status=400,
        )
    try:
        item.delete()
        return JsonResponse(
            {"success": True, "message": "Ítem eliminado correctamente."}
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


@require_POST
@admin_required
def asignar_impresora_item(request, item_id):
    item = get_object_or_404(ItemPedido, id=item_id)
    impresora_id = request.POST.get("impresora_id")

    if impresora_id:
        impresora = get_object_or_404(Impresora, id=impresora_id)
        item.impresora_asignada = impresora
        messages.success(request, f"Impresora {impresora.nombre} asignada.")
    else:
        item.impresora_asignada = None
        messages.info(request, "Impresora desasignada del ítem.")

    item.save()
    return redirect("pedidos:pedido_detalle", pedido_id=item.pedido.id)


@admin_required
def solicitudes_list(request):
    solicitudes_list = SolicitudCotizacion.objects.select_related("usuario").order_by(
        "-fecha_solicitud"
    )

    # Filtro básico por estado si lo deseas
    estado = request.GET.get("estado")
    if estado:
        solicitudes_list = solicitudes_list.filter(estado=estado)

    # Calculamos los KPIs para las cards superiores
    kpis = {
        "solicitudes_nuevas": SolicitudCotizacion.objects.filter(
            estado="Pendiente"
        ).count(),
    }
    paginator = Paginator(solicitudes_list, 10)
    solicitudes = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "solicitudes/solicitudes_list.html",
        {
            "segment": "solicitud",
            "solicitudes": solicitudes,
            "filtro_actual": estado,
            "kpis": kpis,
        },
    )


@admin_required
def convertir_solicitud_a_pedido(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCotizacion, id=solicitud_id)

    # MEDIDA DE SEGURIDAD: Verificar si ya existe un pedido para esta solicitud
    if hasattr(solicitud, "pedido"):
        messages.info(
            request,
            f"Esta solicitud ya fue convertida al Pedido #{solicitud.pedido.id}.",
        )
        return redirect("pedidos:pedido_detalle", pedido_id=solicitud.pedido.id)

    # Si no existe, procedemos a crear el pedido
    try:
        nuevo_pedido = Pedido.objects.create(
            usuario=solicitud.usuario,
            solicitud=solicitud,
            descripcion=solicitud.descripcion,
            estado_pedido="En_Espera",
            peso_estimado_g=0,
            tiempo_estimado_h=0,
            precio_total=0,
            notas=f"Convertido desde solicitud enviada el {solicitud.fecha_solicitud.date()}",
        )

        solicitud.estado = "Completada"
        solicitud.save()

        messages.success(
            request, f"¡Éxito! Solicitud convertida al Pedido #{nuevo_pedido.id}."
        )
        return redirect("pedidos:pedido_detalle", pedido_id=nuevo_pedido.id)

    except Exception as e:
        messages.error(request, f"Error al convertir la solicitud: {str(e)}")
        return redirect("pedidos:solicitudes_lista")


@admin_required
def editar_descripcion_modal(request, pedido_id):
    """Devuelve el HTML del modal de edición"""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    return render(request, "pedidos/modals/editar_descripcion.html", {"pedido": pedido})


@require_POST
@admin_required
def guardar_descripcion(request, pedido_id):
    """Procesa el cambio de descripción"""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    nueva_desc = request.POST.get("descripcion")

    pedido.descripcion = nueva_desc
    pedido.save()

    messages.success(request, "Descripción del pedido actualizada.")
    return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)
