from django.shortcuts import render, redirect, get_object_or_404
from apps.usuarios.decorators import admin_required
from django.contrib import messages
from django.db.models import Sum, F, FloatField
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.http import HttpResponse

from .models import (
    TipoMaterial,
    Material,
    Color,
    Marca,
    EntradaInventario,
    ConsumoMaterial,
    HistorialInventario,
)

from .forms import MaterialForm, EntradaInventarioForm, EditarMaterialForm


# --- VISTAS PRINCIPALES ---
@admin_required
def material_list(request):
    """Muestra el listado principal con filtros, búsqueda y cálculos de valor."""
    # 1. Parámetros de entrada
    search_query = request.GET.get("search", "")
    tipo_filtro = request.GET.get("tipo", "")
    orden_filtro = request.GET.get("orden", "")

    # 2. QuerySet Base
    materiales_qs = Material.objects.all()

    # 3. Aplicar Búsqueda y Filtros
    if search_query:
        palabras = search_query.split()
        for palabra in palabras:
            # La clave es re-filtrar el queryset ya filtrado por la palabra anterior
            materiales_qs = materiales_qs.filter(
                Q(marca__nombre__icontains=palabra) |
                Q(tipo__nombre__icontains=palabra) |
                Q(color__nombre__icontains=palabra)
            )
        # Importante: usar distinct() si hay muchos joins para evitar duplicados
        materiales_qs = materiales_qs.distinct()
    if tipo_filtro:
        materiales_qs = materiales_qs.filter(tipo_id=tipo_filtro)

    # 4. Cálculo del Valor Total (Sobre el QuerySet filtrado)
    resultado = materiales_qs.aggregate(
        total=Sum(F("stock_actual") * F("costo_por_gramo"), output_field=FloatField())
    )
    valor_total = resultado["total"] or 0

    # 5. Aplicar Ordenanza
    if orden_filtro == "stock_asc":
        materiales_qs = materiales_qs.order_by("stock_actual", "tipo__nombre")
    elif orden_filtro == "stock_desc":
        materiales_qs = materiales_qs.order_by("-stock_actual", "tipo__nombre")
    else:
        materiales_qs = materiales_qs.order_by("tipo__nombre", "marca__nombre")

    # 6. Paginación
    paginator = Paginator(materiales_qs, 10)
    page_number = request.GET.get("page")
    materiales = paginator.get_page(page_number)

    context = {
        "materiales": materiales,
        "valor_total": valor_total,
        "marcas_list": Marca.objects.all().order_by("nombre"),
        "tipos_list": TipoMaterial.objects.all().order_by("nombre"),
        "colores_list": Color.objects.all().order_by("nombre"),
        "form": MaterialForm(),
        "entrada_form": EntradaInventarioForm(),
        "search_query": search_query,
        "tipo_filtro": tipo_filtro,
        "orden_actual": orden_filtro,
    }

    if request.headers.get("HX-Request"):
        return render(request, "materiales/partials/material_tabla.html", context)

    return render(request, "materiales/material_list.html", context)


# --- VISTAS DE FORMULARIOS ---
@admin_required
def crear_material(request):
    if request.method == "POST":
        data = request.POST.copy()

        # --- CORRECCIÓN AQUÍ ---
        # Usamos los nombres exactos que vienen del HTML (mira tu traceback)
        campos_a_limpiar = ["marca_nombre", "tipo_nombre", "color_nombre", "enlace_compra"]

        for campo in campos_a_limpiar:
            valor = data.get(campo)
            if valor:
                # Convertimos "AMARILLO" -> "Amarillo"
                data[campo] = valor.strip().capitalize()

        # Pasamos la data ya limpia (donde 'color_nombre' es 'Amarillo')
        form = MaterialForm(data)

        if form.is_valid():
            try:
                material = form.save()
                if material.just_created:
                    messages.success(request, f"Material {material} creado con éxito.")
                else:
                    messages.warning(request, f"El material {material} ya existía.")
            except Exception as e:
                # Capturamos cualquier otro error de integridad por si acaso
                messages.error(request, f"Error al guardar: {e}")
        else:
            messages.error(request, "Error al procesar el formulario.")

    return redirect("materiales:lista_materiales")


@admin_required
def editar_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    if request.method == "POST":
        form = EditarMaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, "Material actualizado correctamente.")
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    return redirect("materiales:lista_materiales")


@admin_required
@require_POST
def eliminar_material(request, material_id):
    material = get_object_or_404(Material, pk=material_id)
    try:
        nombre = str(material)
        material.delete()
        return JsonResponse(
            {"success": True, "message": f"Material {nombre} eliminado correctamente."}
        )
    except ValidationError as e:
        return JsonResponse({"success": False, "message": str(e.message)})
    except Exception:
        return JsonResponse(
            {"success": False, "message": "Ocurrió un error inesperado."}
        )


@admin_required
def registrar_entrada(request):
    if request.method == "POST":
        form = EntradaInventarioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Entrada de inventario registrada y stock actualizado."
            )
        else:
            # Mostramos los errores específicos del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return redirect("materiales:lista_materiales")


@admin_required
def gestionar_atributo(request, modelo_tipo, objeto_id):
    modelos = {"marca": Marca, "tipo": TipoMaterial, "color": Color}
    model_class = modelos.get(modelo_tipo)
    objeto = get_object_or_404(model_class, id=objeto_id)

    if request.method == "POST":
        nuevo_nombre = request.POST.get("nuevo_nombre").strip()
        existente = (
            model_class.objects.filter(nombre__iexact=nuevo_nombre)
            .exclude(id=objeto.id)
            .first()
        )

        try:
            with transaction.atomic():
                if existente:
                    # Buscamos todos los materiales que usan el atributo viejo (ej: SASA)
                    filtro = {modelo_tipo: objeto}
                    materiales_a_mover = Material.objects.filter(**filtro)

                    for mat_viejo in materiales_a_mover:
                        # Buscamos si ya existe un material igual pero con el atributo nuevo (ej: ASA)
                        busqueda_clon = {
                            "marca": mat_viejo.marca,
                            "tipo": mat_viejo.tipo,
                            "color": mat_viejo.color,
                        }
                        # Reemplazamos el atributo que estamos gestionando en la búsqueda
                        busqueda_clon[modelo_tipo] = existente

                        mat_clon = Material.objects.filter(**busqueda_clon).first()

                        if mat_clon:
                            # ¡COLISIÓN DETECTADA! Fusionamos datos
                            mat_clon.stock_actual += mat_viejo.stock_actual
                            mat_clon.save()

                            # Movemos el historial para no perder el rastro
                            HistorialInventario.objects.filter(
                                material=mat_viejo
                            ).update(material=mat_clon)
                            # También mover las entradas y consumos si quieres mantener link
                            EntradaInventario.objects.filter(material=mat_viejo).update(
                                material=mat_clon
                            )
                            ConsumoMaterial.objects.filter(material=mat_viejo).update(
                                material=mat_clon
                            )

                            from apps.finanzas.models import Gasto

                            # Buscamos todos los gastos asociados a las entradas que acabamos de mover
                            entradas_ids = EntradaInventario.objects.filter(
                                material=mat_clon
                            ).values_list("id", flat=True)
                            gastos_a_corregir = Gasto.objects.filter(
                                entrada_inventario_id__in=entradas_ids
                            )

                            for gasto in gastos_a_corregir:
                                # Reemplazamos el nombre viejo por el nuevo en la descripción
                                # Ejemplo: "Compra de 1000g de Daviterra PLAS Blanco" -> "... PLA Blanco"
                                nombre_viejo = str(mat_viejo).split(" (")[
                                    0
                                ]  # Quita el stock del __str__
                                nombre_nuevo = str(mat_clon).split(" (")[0]

                                gasto.descripcion = gasto.descripcion.replace(
                                    nombre_viejo, nombre_nuevo
                                )
                                gasto.save()

                            # Borramos el material viejo USANDO EL NUEVO PERMISO
                            mat_viejo.delete(force_delete=True)
                        else:
                            # No hay colisión, solo actualizamos el atributo
                            setattr(mat_viejo, modelo_tipo, existente)
                            mat_viejo.save()

                    objeto.delete()  # Borramos SASA
                    messages.success(
                        request,
                        f"Fusión exitosa. '{nuevo_nombre}' ha absorbido los materiales.",
                    )
                else:
                    # Simple renombramiento (no hay riesgo de colisión)
                    objeto.nombre = nuevo_nombre
                    objeto.save()
                    messages.success(request, f"Nombre corregido a '{nuevo_nombre}'.")

        except Exception as e:
            messages.error(request, f"Error durante la gestión: {str(e)}")

    return redirect("materiales:lista_materiales")


@admin_required
@require_POST
def eliminar_atributo(request, tipo_atrib, id_atrib):
    modelos = {"marcas": Marca, "tipos": TipoMaterial, "colores": Color}

    model_class = modelos.get(tipo_atrib)
    if not model_class:
        return JsonResponse({"success": False, "message": "Atributo no válido."})

    obj = get_object_or_404(model_class, id=id_atrib)

    # Verificamos si hay materiales vinculados
    if obj.material_set.exists():
        return JsonResponse(
            {
                "success": False,
                "message": f"Existen materiales registrados con este/a {tipo_atrib}. Elimina o edita esos materiales primero.",
            }
        )

    try:
        nombre = obj.nombre
        obj.delete()
        return JsonResponse(
            {
                "success": True,
                "message": f"{tipo_atrib.capitalize()} '{nombre}' eliminado correctamente.",
            }
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error al eliminar el registro."}
        )


# --- ENDPOINTS AJAX / JSON ---
@admin_required
def buscar_atributo_ajax(request):
    query = (
        request.GET.get("q")
        or request.GET.get("marca_nombre")
        or request.GET.get("tipo_nombre")
        or request.GET.get("color_nombre")
        or ""
    )
    tipo_busqueda = request.GET.get("tipo", "")

    resultados = []
    if len(query.strip()) >= 1:
        modelos = {"marca": Marca, "tipo": TipoMaterial, "color": Color}
        model_class = modelos.get(tipo_busqueda)
        if model_class:
            resultados = model_class.objects.filter(nombre__icontains=query.strip()).order_by('nombre')[:4]

    # Si no hay texto, devolvemos un string vacío (nada de HTML)
    if not query:
        return HttpResponse("")
    
    return render(
        request,
        "materiales/partials/resultados_atributos.html",
        {"resultados": resultados, "tipo": tipo_busqueda},
    )


@admin_required
def buscar_material_ajax(request):

    if not request.htmx:
        # Solo permitir acceso a staff
        if request.user.is_staff:
            messages.warning(
                request,
                "Url no permitida."
            )
            return redirect("materiales:lista_materiales")
    
    query = request.GET.get("q", request.GET.get("material_search", "")).strip()

    if not query:
        return HttpResponse("")

    materiales = []

    if len(query) >= 1:
        palabras = (
            query.split()
        )  # Separa "Bambu ASA Negro" en ['Bambu', 'ASA', 'Negro']
        materiales_qs = Material.objects.select_related(
            "marca", "tipo", "color"
        )
        for palabra in palabras:
            # Filtramos el queryset sucesivamente por cada palabra
            materiales_qs = materiales_qs.filter(
                Q(marca__nombre__icontains=palabra)
                | Q(tipo__nombre__icontains=palabra)
                | Q(color__nombre__icontains=palabra)
            )


        materiales = materiales_qs.distinct().order_by('marca__nombre', 'tipo__nombre', 'color__nombre')[:4] # Ordenamos por marca y color y limitamos a 4 resultados

    return render(
        request,
        "materiales/partials/resultados_busqueda_material.html",
        {"materiales": materiales},
    )


@admin_required
def obtener_material_json(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    
    #Manejar casos donde color_hex está vacío o None
    color_hex = '#10b981'  # Color por defecto
    if material.color and material.color.codigo_hex:
        color_hex = material.color.codigo_hex.strip()
        # Si después del strip está vacío, usar el default
        if not color_hex or color_hex == '':
            color_hex = '#10b981'
    
    print(f" DEBUG - Material: {material}")
    print(f" DEBUG - Color original: '{material.color.codigo_hex if material.color else 'None'}'")
    print(f" DEBUG - Color hex a enviar: '{color_hex}'")
    
    return JsonResponse(
        {
            "id": material.id,
            "nombre": str(material),
            "tipo": material.tipo.nombre,
            "costo_por_gramo": "{:.2f}".format(material.costo_por_gramo),
            "stock_minimo": float(material.stock_minimo),
            "stock_actual": float(material.stock_actual),
            "enlace_compra": material.enlace_compra,
            "color_hex": color_hex,
            "color_nombre": material.color.nombre if material.color else "",
        }
    )

@admin_required
def obtener_precio_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    
    return JsonResponse({
        'costo_por_gramo': float(material.costo_por_gramo),
        'stock_actual': float(material.stock_actual),
        'nombre': f"{material.tipo} {material.marca}",
        'color': str(material.color),
    })
