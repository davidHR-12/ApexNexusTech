from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from apps.usuarios.decorators import admin_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from .forms import PedidoManualForm, ItemCatalogoForm, ItemPersonalizadoForm
from .models import Pedido, ItemPedido, Impresora, SolicitudCotizacion, NotaPedido

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

    impresoras_disponibles = Impresora.objects.filter(estado="Disponible")

    context = {
        "pedido": pedido,
        "items": items,
        "pagos": pedido.pagos.all(),
        "impresoras": impresoras_disponibles,
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
    """Verifica impresoras asignadas y su disponibilidad técnica."""
    items_sin_maquina = []
    maquinas_con_error = []

    for item in pedido.items.all():
        necesita_impresion = item.material_personalizado or (item.variante and item.variante.stock_disponible < item.cantidad)

        if necesita_impresion:
            if not item.impresora_asignada:
                items_sin_maquina.append(item.descripcion)
            else:
                maquina = item.impresora_asignada
                # LÓGICA REPARADA:
                # Solo damos error si la máquina NO está disponible 
                # Y ADEMÁS no es una máquina que ya estuviéramos usando en este mismo pedido.
                if maquina.estado != "Disponible":
                    # Si la máquina está "Imprimiendo", verificamos si es por este mismo pedido
                    # Buscamos si hay algún otro ítem de OTRO pedido usando esta máquina
                    # Pero para simplificar: si el estado es Mantenimiento u Offline, error siempre.
                    if maquina.estado in ["Mantenimiento", "Offline"]:
                        maquinas_con_error.append(f"{maquina.nombre} ({maquina.estado})")
                    
                    # Si está "Imprimiendo", solo damos error si el pedido actual NO es el que la tiene
                    # (Esto previene el error de "doble ítem")
                    elif maquina.estado == "Imprimiendo":
                        # Verificamos si hay otros ítems de OTROS pedidos que tengan esta máquina
                        from .models import ItemPedido
                        ocupada_por_otro = ItemPedido.objects.filter(
                            impresora_asignada=maquina
                        ).exclude(pedido=pedido).exists()
                        
                        if ocupada_por_otro:
                            maquinas_con_error.append(f"{maquina.nombre} (Ocupada por otro pedido)")

    if items_sin_maquina:
        messages.error(request, f"Falta asignar máquina a: {', '.join(items_sin_maquina)}")
        return False

    if maquinas_con_error:
        messages.error(request, f"No se puede iniciar producción: {', '.join(maquinas_con_error)}")
        return False

    return True

def _validar_stock_disponible(pedido, request):
    """Verifica si hay stock suficiente antes de permitir el avance del pedido."""
    faltantes = []
    
    for item in pedido.items.all():
        if item.variante:
            if item.variante.stock_disponible < item.cantidad:
                faltantes.append(f"{item.descripcion} (Faltan {item.cantidad - item.variante.stock_disponible}u)")
        
        elif item.material_personalizado:
            gramos_necesarios = item.gramos_por_unidad * item.cantidad
            if item.material_personalizado.stock_actual < gramos_necesarios:
                faltantes.append(f"Material {item.material_personalizado.tipo} (Faltan {gramos_necesarios - item.material_personalizado.stock_actual}g)")

    if faltantes:
        messages.error(request, "Stock insuficiente: " + " | ".join(faltantes))
        return False
    return True

def _revertir_stock_y_liberar(pedido, request):
    """Devuelve TODO al inventario (Catálogo y Material) y libera impresoras."""
    for item in pedido.items.all():
        if item.variante:
            item.variante.stock_disponible += item.cantidad
            item.variante.save()
        elif item.material_personalizado:
            gramos = item.gramos_por_unidad * item.cantidad
            item.material_personalizado.stock_actual += gramos
            item.material_personalizado.save()

    # Liberar máquinas y limpiar asignación
    items_con_maquina = pedido.items.filter(impresora_asignada__isnull=False)
    for item in items_con_maquina:
        maquina = item.impresora_asignada
        maquina.estado = "Disponible"
        maquina.save()
        item.impresora_asignada = None
        item.save()

    pedido.stock_descontado = False
    messages.warning(request, "Stock restaurado y máquinas liberadas.")


def _procesar_pedido_fallido(pedido, request):
    """
    Si falla la impresión, el filamento se pierde (no se devuelve),
    pero los productos de catálogo sí se reintegran al inventario.
    """
    items_con_maquina = pedido.items.filter(impresora_asignada__isnull=False)
    
    # 1. Liberar máquinas
    for item in items_con_maquina:
        maquina = item.impresora_asignada
        maquina.estado = "Disponible"
        maquina.save()

    # 2. Devolver solo Catálogo
    devoluciones = 0
    for item in pedido.items.all():
        if item.variante:
            item.variante.stock_disponible += item.cantidad
            item.variante.save()
            devoluciones += 1
    
    if devoluciones > 0:
        messages.info(request, "Productos de catálogo devueltos. El filamento personalizado se registró como pérdida.")
    else:
        messages.error(request, "Pérdida registrada: El material personalizado no regresó al stock.")


def _descontar_stock(pedido, nuevo_estado, request):
    """Resta del inventario."""
    for item in pedido.items.all():
        if item.variante:
            item.variante.stock_disponible -= item.cantidad
            item.variante.save()
        elif item.material_personalizado:
            gramos = item.gramos_por_unidad * item.cantidad
            item.material_personalizado.stock_actual -= gramos
            item.material_personalizado.save()

    pedido.stock_descontado = True
    messages.info(request, "Inventario actualizado: Materiales descontados.")


def _gestionar_ciclo_vida_impresoras(pedido, nuevo_estado, request):
    items_con_maquina = pedido.items.filter(impresora_asignada__isnull=False)
    
    # Usamos un set para no repetir procesos si la misma máquina está en varios ítems
    maquinas_procesadas = set()

    for item in items_con_maquina:
        maquina = item.impresora_asignada
        if maquina.id in maquinas_procesadas:
            continue
            
        if nuevo_estado == "En_Produccion":
            # Solo la ponemos en Imprimiendo si estaba Disponible
            if maquina.estado == "Disponible":
                maquina.estado = "Imprimiendo"
                maquina.save()
        
        elif nuevo_estado in ["Listo", "Entregado", "Cancelado", "Fallido"]:
            maquina.estado = "Disponible"
            maquina.save()
            
        maquinas_procesadas.add(maquina.id)


# ==========================================
#  VISTA PRINCIPAL REFACTORIZADA
# ==========================================


@admin_required
def cambiar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    nuevo_estado = request.POST.get("nuevo_estado")

    # BLOQUEO DE SEGURIDAD PARA ESTADOS FINALIZADOS O FALLIDOS
    if pedido.estado_pedido in ["Entregado", "Cancelado", "Fallido"]:
        messages.error(request, f"El pedido está en estado {pedido.estado_pedido} y no puede ser modificado.")
        return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    # 1. VALIDACIÓN DE SEGURIDAD BÁSICA
    if pedido.estado_pedido in ["Entregado", "Cancelado"]:
        messages.error(request, "No se puede modificar un pedido finalizado.")
        return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    if not nuevo_estado:
        return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    # 2. VALIDACIONES PREVIAS AL CAMBIO
    # A. Validar Stock (Solo si intentamos avanzar a estados de consumo y no se ha descontado aún)
    estados_que_consumen = ["Confirmado", "En_Produccion", "Listo", "Entregado"]
    if nuevo_estado in estados_que_consumen and not pedido.stock_descontado:
        if not _validar_stock_disponible(pedido, request):
            return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    # B. Validar Impresoras (Solo si el nuevo estado es producción)
    if nuevo_estado == "En_Produccion":
        if not _validar_requisitos_produccion(pedido, request):
            return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    # 3. EJECUCIÓN DE LÓGICA SEGÚN TRANSICIÓN
    
    # Caso Reversión: Volver a borrador o cancelar habiendo descontado stock
    if nuevo_estado in ["En_Espera", "Cancelado"] and pedido.stock_descontado:
        _revertir_stock_y_liberar(pedido, request)

    # Caso Fallo: Manejo de pérdida de material
    elif nuevo_estado == "Fallido" and pedido.stock_descontado:
        _procesar_pedido_fallido(pedido, request)

    # Caso Avance: Consumo de stock y actualización de máquinas
    elif nuevo_estado in estados_que_consumen:
        # Descontar stock si es la primera vez que entra en este flujo
        if not pedido.stock_descontado:
            _descontar_stock(pedido, nuevo_estado, request)
        
        # Gestionar (Activar/Liberar) máquinas físicas
        _gestionar_ciclo_vida_impresoras(pedido, nuevo_estado, request)

    # 4. GUARDADO FINAL
    pedido.estado_pedido = nuevo_estado
    pedido.save()

    messages.success(request, f"Pedido #{pedido.id} actualizado a {pedido.get_estado_pedido_display()}.")
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
            item.gramos_por_unidad = item.variante.peso_total
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
    
    # Bloqueo para itens de Catálogo
    # Como decidimos que catálogo no se edita, redireccionamos si alguien intenta acceder a la URL
    if item.variante:
        messages.warning(request, "Los itens de catálogo no pueden ser editados. Remuévalos y agréguelos nuevamente si es necesario.")
        return redirect("pedidos:pedido_detalle", pedido_id=item.pedido.id)

    # Bloqueo por Procesamiento de Stock
    if getattr(item.pedido, "stock_descontado", False):
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "success": False,
                "message": "Pedido bloqueado: El stock ya fue descontado.",
            }, status=400)
        messages.error(request, "No es posible editar un item con stock ya procesado.")
        return redirect("pedidos:pedido_detalle", pedido_id=item.pedido.id)

    # Ahora usamos solo el FormPersonalizado
    if request.method == "POST":
        form = ItemPersonalizadoForm(request.POST, instance=item)
        if form.is_valid():
            item_editado = form.save(commit=False)
            # Actualiza el costo del material
            if item_editado.material_personalizado:
                item_editado.costo_material_unitario = item_editado.material_personalizado.costo_por_gramo
            
            item_editado.save()
            messages.success(request, "Item personalizado actualizado.")
            return redirect("pedidos:pedido_detalle", pedido_id=item.pedido.id)
    else:
        form = ItemPersonalizadoForm(instance=item)
    
    context = _obtener_contexto_dashboard(request)
    context.update({
        "form": form,
        "item": item,
        "pedido": item.pedido,
        "modal_id": "modalEditarItem",
        "title": "Editar Pieza Personalizada",
        "max_width": "max-w-2xl"
    })

    return render(request, "pedidos/modals/editar_item.html", context)


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

    # 1. BLOQUEO RADICAL: No se toca la asignación si ya está en producción o más allá
    if item.pedido.estado_pedido in ["En_Produccion", "Listo", "Entregado", "Cancelado", "Fallido"]:
        messages.error(request, "No puedes cambiar impresoras de un pedido que ya está en producción o finalizado.")
        return redirect("pedidos:pedido_detalle", pedido_id=item.pedido.id)

    if impresora_id:
        # Lógica de asignación
        impresora = get_object_or_404(Impresora, id=impresora_id)
        if impresora.estado != "Disponible" and item.impresora_asignada != impresora:
            messages.error(request, f"La impresora {impresora.nombre} no está disponible.")
            return redirect("pedidos:pedido_detalle", pedido_id=item.pedido.id)
            
        item.impresora_asignada = impresora
        messages.success(request, f"Impresora {impresora.nombre} asignada.")
    else:
        # 2. LOGICA DE DESASIGNACIÓN (Opción vacía)
        if item.impresora_asignada:
            maquina_vieja = item.impresora_asignada
            # Al desasignar, nos aseguramos que la máquina quede libre
            maquina_vieja.estado = "Disponible"
            maquina_vieja.save()
            
        item.impresora_asignada = None
        messages.info(request, "Impresora desasignada e inventario de máquinas actualizado.")

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

    if hasattr(solicitud, "pedido"):
        messages.info(request, f"Ya existe el Pedido #{solicitud.pedido.id} para esta solicitud.")
        return redirect("pedidos:pedido_detalle", pedido_id=solicitud.pedido.id)

    try:
        nuevo_pedido = Pedido.objects.create(
            usuario=solicitud.usuario,
            solicitud=solicitud,
            descripcion=solicitud.descripcion,
            estado_pedido="En_Espera",
            precio_total=0,
            notas=f"Convertido desde solicitud del {solicitud.fecha_solicitud.date()}",
        )
        solicitud.estado = "Completada"
        solicitud.save()
        messages.success(request, f"Solicitud convertida al Pedido #{nuevo_pedido.id}.")
        return redirect("pedidos:pedido_detalle", pedido_id=nuevo_pedido.id)
    except Exception as e:
        messages.error(request, f"Error al convertir: {str(e)}")
        return redirect("pedidos:solicitudes_lista")

@admin_required
def editar_notas_modal(request, pedido_id):
    """Devuelve el HTML del modal para editar las notas administrativas"""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    return render(request, "pedidos/modals/editar_notas.html", {"pedido": pedido})

@require_POST
@admin_required
def agregar_nota_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    contenido = request.POST.get("contenido")
    es_publica = request.POST.get("visible_para_cliente") == 'on'

    if contenido:
        # Usamos el related_name 'anotaciones'
        NotaPedido.objects.create(
            pedido=pedido,
            autor=request.user,
            contenido=contenido,
            visible_para_cliente=es_publica
        )
        messages.success(request, "Nota añadida.")
    else:
        messages.error(request, "La nota no puede estar vacía.")
    return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)

@require_POST
@admin_required
def guardar_notas(request, pedido_id):
    """Actualiza el campo de notas/descripción general del pedido."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    pedido.notas = request.POST.get("notas")
    pedido.save()
    messages.success(request, "Información de seguimiento actualizada.")
    return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)