from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse,HttpResponse
from apps.usuarios.decorators import admin_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.db import transaction as db_transaction
from .forms import PedidoManualForm, ItemCatalogoForm, ItemPersonalizadoForm, ItemContenedorForm, ComponenteItemForm
from .models import Pedido, ItemPedido, Impresora, SolicitudCotizacion, NotaPedido, Pago, ConfiguracionPago,PerdidaMaterial

from apps.pedidos.factura_pdf import generar_factura_pdf

@admin_required
def factura_view(request, pedido_id):
    return generar_factura_pdf(request, pedido_id)

# ==========================================
#  VISTAS DE LECTURA Y DASHBOARD
# ==========================================


@admin_required
def pedidos_list(request):
    """Vista principal de pedidos con soporte para HTMX."""
    context = _obtener_contexto_dashboard(request)
    context["form"] = PedidoManualForm()
    context["segment"] = "pedidos"
    
    # Si es HTMX, devolvemos solo la tabla
    if request.headers.get("HX-Request"):
        return render(request, "pedidos/partials/pedido_tabla.html", context)
        
    return render(request, "pedidos/pedidos_list.html", context)

def _obtener_contexto_dashboard(request):
    # Aseguramos que los valores sean strings vacíos en lugar de None
    estado_filtro = request.GET.get("estado", "")
    busqueda = request.GET.get("q", "")
    page_number = request.GET.get("page", 1)

    pedidos_qs = Pedido.objects.select_related("usuario").order_by("-fecha_creacion")

    if estado_filtro:
        pedidos_qs = pedidos_qs.filter(estado_pedido=estado_filtro)

    if busqueda:
        palabras = busqueda.split()
        for palabra in palabras:
            pedidos_qs = pedidos_qs.filter(
                Q(id__icontains=palabra) |
                Q(usuario__first_name__icontains=palabra) |
                Q(usuario__last_name__icontains=palabra) |
                Q(usuario__email__icontains=palabra) |
                Q(guest_nombre__icontains=palabra) |
                Q(guest_email__icontains=palabra) |
                Q(guest_telefono__icontains=palabra)
            )
        pedidos_qs = pedidos_qs.distinct()

    # Paginación
    paginator = Paginator(pedidos_qs, 10)
    pedidos_paginados = paginator.get_page(page_number)

    kpis = {
        "pendientes": Pedido.objects.filter(estado_pedido__in=["En_Espera", "Confirmado"]).count(),
        "produccion": Pedido.objects.filter(estado_pedido="En_Produccion").count(),
        "listos": Pedido.objects.filter(estado_pedido="Listo").count(),
        "solicitudes_nuevas": SolicitudCotizacion.objects.filter(estado="Pendiente").count(),

    }

    return {
        "pedidos": pedidos_paginados,
        "kpis": kpis,
        "filtro_actual": estado_filtro,
        "busqueda_actual": busqueda,
        "estados_opciones": Pedido.ESTADOS_PEDIDO,
    }


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
        "form_contenedor": ItemContenedorForm(),
        "form_componente": ComponenteItemForm(),
        "segment": "pedidos",
        "kpis": {"solicitudes_nuevas": solicitudes_pendientes},
    }
    return render(request, "pedidos/pedido_detalle.html", context)


# ==========================================
#  SERVICIOS AUXILIARES (LÓGICA DE NEGOCIO)
# ==========================================

def _items_de_produccion(pedido):
    """
    Retorna los ítems reales que necesitan impresión/material:
    - Componentes de contenedores
    - Ítems personalizados al estilo antiguo (sin item_padre, con material)
    - Ítems de catálogo que requieren impresión (sin stock)
    """
    produccion = []
    for item in pedido.items.filter(item_padre__isnull=True).prefetch_related('componentes'):
        if item.variante:
            if item.variante.stock_disponible < item.cantidad:
                produccion.append(item)
        elif item.componentes.exists():
            produccion.extend(item.componentes.all())
        elif item.material_personalizado:
            produccion.append(item)
    return produccion

def _validar_requisitos_produccion(pedido, request):
    """Verifica impresoras asignadas para todos los ítems que necesitan producción."""
    items_sin_maquina  = []
    maquinas_con_error = []

    for item in _items_de_produccion(pedido):
        if not item.impresora_asignada:
            nombre = item.descripcion or str(item)
            items_sin_maquina.append(nombre)
        else:
            maquina = item.impresora_asignada
            if maquina.estado != "Disponible":
                if maquina.estado in ["Mantenimiento", "Offline"]:
                    maquinas_con_error.append(f"{maquina.nombre} ({maquina.estado})")
                elif maquina.estado == "Imprimiendo":
                    from .models import ItemPedido as _IP
                    if _IP.objects.filter(impresora_asignada=maquina).exclude(pedido=pedido).exists():
                        maquinas_con_error.append(f"{maquina.nombre} (Ocupada por otro pedido)")

    if items_sin_maquina:
        messages.error(request, f"Falta asignar máquina a: {', '.join(items_sin_maquina)}")
        return False
    if maquinas_con_error:
        messages.error(request, f"No se puede iniciar producción: {', '.join(maquinas_con_error)}")
        return False
    return True

def _validar_stock_disponible(pedido, request):
    """Verifica stock de materiales y variantes (incluyendo componentes)."""
    faltantes = []

    for item in pedido.items.filter(item_padre__isnull=True).prefetch_related('componentes'):
        if item.variante:
            if item.variante.stock_disponible < item.cantidad:
                faltantes.append(
                    f"{item.descripcion} (Faltan {item.cantidad - item.variante.stock_disponible}u)"
                )
        elif item.componentes.exists():
            for comp in item.componentes.all():
                if comp.material_personalizado:
                    gramos = comp.gramos_por_unidad * comp.cantidad
                    if comp.material_personalizado.stock_actual < gramos:
                        faltantes.append(
                            f"{comp.descripcion} — {comp.material_personalizado} "
                            f"(Faltan {gramos - comp.material_personalizado.stock_actual}g)"
                        )
        elif item.material_personalizado:
            gramos = item.gramos_por_unidad * item.cantidad
            if item.material_personalizado.stock_actual < gramos:
                faltantes.append(
                    f"Material {item.material_personalizado.tipo} "
                    f"(Faltan {gramos - item.material_personalizado.stock_actual}g)"
                )

    if faltantes:
        messages.error(request, "Stock insuficiente: " + " | ".join(faltantes))
        return False
    return True


def _revertir_stock_y_liberar(pedido, request):
    """
    Devuelve al inventario solo el material de ítems que NO tuvieron fallo de
    impresión confirmado (fallo_registrado=False).
    Los ítems con fallo_registrado=True ya perdieron ese material → no se devuelve.
    También libera impresoras de los ítems sin fallo.
    """
    for item in pedido.items.filter(item_padre__isnull=True).prefetch_related('componentes'):
        if item.variante:
            # Los ítems de catálogo no tienen fallo de impresión → siempre devolver
            item.variante.stock_disponible += item.cantidad
            item.variante.save()

        elif item.componentes.exists():
            for comp in item.componentes.all():
                if comp.fallo_registrado:
                    # Material ya perdido — no devolver, solo liberar impresora si quedó asignada
                    if comp.impresora_asignada:
                        comp.impresora_asignada.estado = "Disponible"
                        comp.impresora_asignada.save()
                        comp.impresora_asignada = None
                        comp.save()
                    continue

                if comp.material_personalizado:
                    comp.material_personalizado.stock_actual += comp.gramos_por_unidad * comp.cantidad
                    comp.material_personalizado.save()
                if comp.impresora_asignada:
                    comp.impresora_asignada.estado = "Disponible"
                    comp.impresora_asignada.save()
                    comp.impresora_asignada = None
                    comp.save()

        elif item.material_personalizado:
            if item.fallo_registrado:
                # Material ya perdido — solo liberar impresora
                if item.impresora_asignada:
                    item.impresora_asignada.estado = "Disponible"
                    item.impresora_asignada.save()
                    item.impresora_asignada = None
                    item.save()
                continue

            item.material_personalizado.stock_actual += item.gramos_por_unidad * item.cantidad
            item.material_personalizado.save()

    # Liberar impresoras de ítems raíz con impresora directa (no fallidos)
    for item in pedido.items.filter(
        item_padre__isnull=True,
        impresora_asignada__isnull=False,
        fallo_registrado=False,
    ):
        item.impresora_asignada.estado = "Disponible"
        item.impresora_asignada.save()
        item.impresora_asignada = None
        item.save()

    pedido.stock_descontado = False
    messages.warning(request, "Stock restaurado y máquinas liberadas (materiales con fallo no recuperados).")


def _descontar_stock(pedido, nuevo_estado, request):
    """Descuenta inventario de variantes y materiales (incluyendo componentes)."""
    for item in pedido.items.filter(item_padre__isnull=True).prefetch_related('componentes'):
        if item.variante:
            item.variante.stock_disponible -= item.cantidad
            item.variante.save()
        elif item.componentes.exists():
            for comp in item.componentes.all():
                if comp.material_personalizado:
                    comp.material_personalizado.stock_actual -= comp.gramos_por_unidad * comp.cantidad
                    comp.material_personalizado.save()
        elif item.material_personalizado:
            item.material_personalizado.stock_actual -= item.gramos_por_unidad * item.cantidad
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
        
        elif nuevo_estado in ["Listo", "Entregado", "Fallido"]:
            maquina.estado = "Disponible"
            maquina.save()
            
        maquinas_procesadas.add(maquina.id)


@require_POST
@admin_required
def registrar_fallo_impresion(request, pedido_id):
    """
    Registra fallos de impresión de forma granular por ítem.

    - Recibe una lista de IDs de ítems fallidos vía POST (checkboxes: name="item_fallido")
    - Cada ítem fallido genera un registro PerdidaMaterial + HistorialInventario
    - Los ítems NO marcados no se tocan (siguen en producción)
    - Si un ítem fallido tiene impresora asignada y ningún otro ítem activo la usa → se libera
    - El pedido permanece En_Produccion si quedan ítems activos;
      regresa a Confirmado solo si todos los ítems personalizados fallaron
    - stock_descontado se mantiene True (el stock ya salió; la pérdida es el registro)
    - El cliente no ve nada — se crea una nota interna privada
    """
    from apps.materiales.models import HistorialInventario

    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if pedido.estado_pedido != 'En_Produccion':
        messages.error(request, "Solo se puede registrar un fallo cuando el pedido está En Producción.")
        return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

    # IDs de ítems marcados como fallidos
    ids_fallidos = request.POST.getlist('item_fallido')  # lista de str

    if not ids_fallidos:
        messages.error(request, "Debes seleccionar al menos un ítem para registrar el fallo.")
        return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

    perdidas_resumen = []
    maquinas_a_liberar = set()

    with db_transaction.atomic():
        items_produccion = _items_de_produccion(pedido)
        total_produccion = len(items_produccion)
        fallidos_count   = 0

        for item in pedido.items.filter(id__in=ids_fallidos):
            if not item.material_personalizado:
                continue

            gramos   = item.gramos_por_unidad * item.cantidad
            material = item.material_personalizado
            motivo   = request.POST.get(f"motivo_{item.id}", "").strip() or "Sin especificar"

            PerdidaMaterial.objects.create(
                pedido=pedido, material=material, gramos_perdidos=gramos,
                motivo=motivo, registrado_por=request.user,
            )
            HistorialInventario.objects.create(
                material=material, accion="Consumo",
                cantidad_nueva=material.stock_actual,
                cantidad_anterior=material.stock_actual + gramos,
                diferencia=-gramos,
            )
            perdidas_resumen.append(
                f"{item.descripcion or 'Pieza'}: {gramos}g de {material} ({motivo})"
            )
            fallidos_count += 1

            # ← NUEVO: marcar el ítem como fallido
            item.fallo_registrado = True
            item.save(update_fields=['fallo_registrado'])

            if item.impresora_asignada:
                maquinas_a_liberar.add(item.impresora_asignada_id)

        # Liberar solo máquinas no usadas por ítems activos
        for item in pedido.items.exclude(id__in=ids_fallidos).filter(impresora_asignada__isnull=False):
            maquinas_a_liberar.discard(item.impresora_asignada_id)

        for maquina_id in maquinas_a_liberar:
            Impresora.objects.filter(id=maquina_id).update(estado="Disponible")

        NotaPedido.objects.create(
            pedido=pedido, autor=request.user,
            contenido=(
                f"FALLO DE IMPRESIÓN — {fallidos_count} componente(s)\n\n"
                + "\n".join(f"• {r}" for r in perdidas_resumen)
                + (f"\n\nImpresoras liberadas: {len(maquinas_a_liberar)}" if maquinas_a_liberar else "")
            ),
            visible_para_cliente=False,
        )

        if fallidos_count >= total_produccion:
            pedido.estado_pedido    = "Confirmado"
            pedido.stock_descontado = False
            pedido.save()
            messages.warning(request, "Todos los componentes fallaron. Pedido regresó a 'Confirmado'.")
        else:
            pedido.save()
            messages.warning(
                request,
                f"Fallo registrado en {fallidos_count} componente(s). "
                f"Quedan {total_produccion - fallidos_count} activos."
            )

    return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

# ==========================================
#  VISTA PRINCIPAL REFACTORIZADA
# ==========================================



@admin_required
def cambiar_estado_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    nuevo_estado = request.POST.get("nuevo_estado")

    # BLOQUEO: estados finales no se modifican
    if pedido.estado_pedido in ["Entregado", "Cancelado"]:
        messages.error(request, f"El pedido está en estado final y no puede ser modificado.")
        return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    if not nuevo_estado:
        return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    # Validar stock (solo al avanzar por primera vez)
    estados_que_consumen = ["Confirmado", "En_Produccion", "Listo", "Entregado"]
    if nuevo_estado in estados_que_consumen and not pedido.stock_descontado:
        if not _validar_stock_disponible(pedido, request):
            return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    # Validar impresoras (solo al pasar a producción)
    if nuevo_estado == "En_Produccion":
        if not _validar_requisitos_produccion(pedido, request):
            return redirect("pedidos:pedido_detalle", pedido_id=pedido_id)

    # Reversión: volver a En_Espera o cancelar habiendo descontado stock
    if nuevo_estado in ["En_Espera", "Cancelado"] and pedido.stock_descontado:
        _revertir_stock_y_liberar(pedido, request)

    # Avance normal: descontar stock y gestionar impresoras
    elif nuevo_estado in estados_que_consumen:
        if not pedido.stock_descontado:
            _descontar_stock(pedido, nuevo_estado, request)
        _gestionar_ciclo_vida_impresoras(pedido, nuevo_estado, request)

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
            "No puedes añadir ítems a un pedido que ya procesó inventario. "
            "Regresa el estado a 'En Espera' primero.",
        )
        return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)

    tipo = request.POST.get("tipo_item")

    if tipo == "catalogo":
        form = ItemCatalogoForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pedido          = pedido
            item.precio_unitario = item.variante.precio_final
            item.descripcion     = item.variante.producto.nombre
            item.gramos_por_unidad = item.variante.peso_total
            item.costo_material_unitario = item.variante.costo_materiales
            item.save()
            messages.success(request, "Producto del catálogo agregado.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}" if field != "__all__" else error)

    elif tipo == "contenedor":
        # Nuevo flujo: crea el ítem contenedor (solo nombre + cantidad)
        form = ItemContenedorForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pedido          = pedido
            item.save()
            messages.success(
                request,
                f"Producto '{item.descripcion}' creado. Ahora agrégale los componentes de producción."
            )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)

    else:
        # Compatibilidad con el flujo antiguo de "personalizado" (ítem simple con material)
        form = ItemPersonalizadoForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.pedido = pedido
            item.costo_material_unitario = item.material_personalizado.costo_por_gramo
            item.save()
            messages.success(request, "Ítem personalizado agregado.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error if field in ["material_personalizado", "__all__"] else f"{field}: {error}")

    return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)


@admin_required
@require_POST
def agregar_componente(request, item_id):
    """
    Agrega un componente de producción a un ítem contenedor.
    Los componentes son los detalles técnicos (material, gramos, precio).
    """
    item_padre = get_object_or_404(ItemPedido, id=item_id)
    pedido     = item_padre.pedido

    if getattr(pedido, "stock_descontado", False):
        messages.error(request, "No se pueden añadir componentes a un pedido con stock ya descontado.")
        return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)

    if item_padre.variante:
        messages.error(request, "No se pueden añadir componentes a ítems del catálogo.")
        return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)

    form = ComponenteItemForm(request.POST)
    if form.is_valid():
        componente = form.save(commit=False)
        componente.pedido      = pedido
        componente.item_padre  = item_padre
        componente.costo_material_unitario = componente.material_personalizado.costo_por_gramo
        componente.save()   # save() dispara actualizar_totales vía el signal del contenedor
        messages.success(request, f"Componente '{componente.descripcion}' agregado.")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)

    return redirect("pedidos:pedido_detalle", pedido_id=pedido.id)


@admin_required
def eliminar_componente(request, componente_id):
    """Elimina un componente de producción."""
    componente = get_object_or_404(ItemPedido, id=componente_id)

    if not componente.es_componente:
        return JsonResponse({"success": False, "message": "No es un componente válido."}, status=400)

    if getattr(componente.pedido, "stock_descontado", False):
        return JsonResponse(
            {"success": False, "message": "No se puede eliminar un componente con stock ya descontado."},
            status=400,
        )

    try:
        pedido_id = componente.pedido_id
        componente.delete()
        # Recalculamos el padre manualmente (ya que el signal de delete llama a actualizar_totales)
        return JsonResponse({"success": True, "message": "Componente eliminado."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


@admin_required
def editar_componente(request, componente_id):
    """Edita un componente de producción existente."""
    componente = get_object_or_404(ItemPedido, id=componente_id)

    if not componente.es_componente:
        messages.error(request, "No es un componente válido.")
        return redirect("pedidos:pedido_detalle", pedido_id=componente.pedido_id)

    if getattr(componente.pedido, "stock_descontado", False):
        messages.error(request, "No se puede editar con stock ya descontado.")
        return redirect("pedidos:pedido_detalle", pedido_id=componente.pedido_id)

    if request.method == "POST":
        form = ComponenteItemForm(request.POST, instance=componente)
        if form.is_valid():
            comp = form.save(commit=False)
            comp.costo_material_unitario = comp.material_personalizado.costo_por_gramo
            comp.save()
            messages.success(request, "Componente actualizado.")
            return redirect("pedidos:pedido_detalle", pedido_id=componente.pedido_id)
    else:
        form = ComponenteItemForm(instance=componente)

    return render(request, "pedidos/modals/editar_componente.html", {
        "form":       form,
        "componente": componente,
        "pedido":     componente.pedido,
    })

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
    """Vista de solicitudes con búsqueda HTMX y paginación."""
    busqueda   = request.GET.get("q", "")
    estado     = request.GET.get("estado", "")
    page_number = request.GET.get("page", 1)

    qs = SolicitudCotizacion.objects.select_related("usuario").order_by("-fecha_solicitud")

    if estado:
        qs = qs.filter(estado=estado)

    if busqueda:
        palabras = busqueda.split()
        for palabra in palabras:
            qs = qs.filter(
                Q(usuario__first_name__icontains=palabra) |
                Q(usuario__last_name__icontains=palabra)  |
                Q(usuario__email__icontains=palabra)      |
                Q(descripcion__icontains=palabra)
            )
        qs = qs.distinct()

    paginator    = Paginator(qs, 10)
    solicitudes  = paginator.get_page(page_number)

    kpis = {
        "solicitudes_nuevas": SolicitudCotizacion.objects.filter(estado="Pendiente").count(),
        "total": paginator.count,
    }

    context = {
        "segment": "solicitud",
        "solicitudes": solicitudes,
        "filtro_actual": estado,
        "busqueda_actual": busqueda,
        "estados_opciones": SolicitudCotizacion.ESTADOS,
        "kpis": kpis,
    }

    # HTMX → solo la tabla
    if request.headers.get("HX-Request"):
        return render(request, "solicitudes/partials/solicitudes_tabla.html", context)

    return render(request, "solicitudes/solicitudes_list.html", context)

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
        return redirect("pedidos:solicitudes_list")

@require_POST
@admin_required
def rechazar_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudCotizacion, id=solicitud_id)

    if solicitud.estado in ['Completada', 'Rechazada']:
        messages.warning(request, f"La solicitud ya está en estado '{solicitud.get_estado_display()}'.")
        return redirect('pedidos:solicitudes_list')

    solicitud.estado = 'Rechazada'
    solicitud.save(update_fields=['estado'])
    messages.success(request, f"Solicitud #{solicitud.id} de {solicitud.usuario.get_full_name() or solicitud.usuario.email} marcada como rechazada.")
    return redirect('pedidos:solicitudes_list')

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



@require_POST
@admin_required
def revisar_comprobante(request, pedido_id):
    """
    El admin aprueba o rechaza el comprobante de pago subido por el cliente.
    """
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    decision = request.POST.get('decision', '')

    if decision not in ['Aprobado', 'Rechazado']:
        messages.error(request, "Decisión no válida.")
        return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

    if not pedido.comprobante_cliente:
        messages.error(request, "Este pedido no tiene comprobante para revisar.")
        return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

    pedido.comprobante_estado = decision
    pedido.save(update_fields=['comprobante_estado'])

    if decision == 'Aprobado':
        messages.success(request, f"✅ Comprobante del Pedido #{pedido.id} aprobado.")
    else:
        messages.warning(request, f"❌ Comprobante del Pedido #{pedido.id} rechazado. El cliente deberá subir uno nuevo.")

    return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)


@require_POST
@admin_required
def registrar_pago(request, pedido_id):
    """
    El admin registra un pago recibido (efectivo, transferencia, etc.)
    directamente desde el detalle del pedido.
    """
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    monto_str = request.POST.get('monto', '').strip()
    metodo = request.POST.get('metodo', '').strip()
    referencia = request.POST.get('referencia', '').strip()
    notas = request.POST.get('notas', '').strip()

    # Validaciones
    if not monto_str or not metodo:
        messages.error(request, "El monto y el método son obligatorios.")
        return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

    try:
        from decimal import Decimal
        monto = Decimal(monto_str)
        if monto <= 0:
            raise ValueError
    except (ValueError, Exception):
        messages.error(request, "El monto debe ser un número mayor a 0.")
        return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

    METODOS_VALIDOS = ['Efectivo', 'Transferencia', 'Tarjeta', 'PayPal', 'Otro']
    if metodo not in METODOS_VALIDOS:
        messages.error(request, "Método de pago no válido.")
        return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)

    Pago.objects.create(
        pedido=pedido,
        monto=monto,
        metodo=metodo,
        referencia=referencia,
        notas=notas,
    )

    messages.success(
        request,
        f"Pago de RD$ {monto:,.2f} ({metodo}) registrado correctamente en el Pedido #{pedido.id}."
    )
    return redirect('pedidos:pedido_detalle', pedido_id=pedido_id)