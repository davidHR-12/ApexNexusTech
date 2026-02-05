from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, F, FloatField
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from django.utils.text import slugify
from django.core.paginator import Paginator
from django.db.models import Q


# Create your views here.
from .models import (TipoMaterial, Material, Color, Marca,
                     EntradaInventario, HistorialInventario, ConsumoMaterial)

from .forms import MaterialForm, EntradaInventarioForm

@login_required
def material_list(request):
    """
    Muestra el listado de materiales (rollos, resinas, etc.)
    Incluye formularios para crear materiales y registrar entradas de stock.
    """
    #Obtener todos los materiales
    materiales_qs = Material.objects.all().order_by("tipo__nombre", "marca__nombre")

    
    #CÁLCULO DEL VALOR TOTAL (Sobre todo el material)
    #Esto multiplica stock * costo en la base de datos y suma todo.
    resultado = materiales_qs.aggregate(
        total=Sum(F('stock_actual') * F('costo_por_gramo'), output_field=FloatField())
    )
    valor_total = resultado['total'] or 0

    #Obtener parametros de busqueda y filtro
    search_query = request.GET.get('search', '')
    tipo_filtro = request.GET.get('tipo', '')
    if search_query:
        materiales_qs = materiales_qs.filter(
            Q(marca__nombre__icontains=search_query) |
            Q(tipo__nombre__icontains=search_query) |
            Q(color__nombre__icontains=search_query)
        )

    #Aplicar Lógica de Filtro (por ejemplo, Filamento vs Resina)
    if tipo_filtro:
        materiales_qs = materiales_qs.filter(tipo_id=tipo_filtro)

    # Paginación
    paginator = Paginator(materiales_qs, 10)  # 10 materiales por página
    page_number = request.GET.get("page")
    materiales = paginator.get_page(page_number)

    context = {
        "materiales": materiales,
        "valor_total": valor_total,
        "marcas_list": Marca.objects.all().order_by("nombre"),
        "tipos_list": TipoMaterial.objects.all(),
        "colores_list": Color.objects.all().order_by("nombre"),
        "form": MaterialForm(),
        "entrada_form": EntradaInventarioForm(),    
        "search_query": search_query,
        "tipo_filtro": tipo_filtro,
        "tipo_seleccionado": tipo_filtro,
    }

    if request.headers.get('HX-Request'):
        return render(request, "materiales/partials/material_tabla.html", context)
    
    return render(request, "materiales/material_list.html", context)

@login_required
def crear_material(request):
    """
    Registra un nuevo tipo de material en el sistema.
    Crea automáticamente Marca, Tipo y Color si no existen.
    """
    if request.method == "POST":
        # Extraemos los nombres del formulario
        marca_txt = request.POST.get("marca_nombre").strip()
        tipo_txt = request.POST.get("tipo_nombre").strip()
        color_txt = request.POST.get("color_nombre").strip()

        costo = abs(Decimal(request.POST.get("costo_por_gramo", 0) or 0))
        minimo = abs(Decimal(request.POST.get("stock_minimo", 0) or 0))

        # Magia de Django: Si existe lo usa, si no, lo crea
        marca_obj, _ = Marca.objects.get_or_create(nombre=marca_txt)
        tipo_obj, _ = TipoMaterial.objects.get_or_create(nombre=tipo_txt)
        color_obj, _ = Color.objects.get_or_create(nombre=color_txt)

        try:
            material, created = Material.objects.get_or_create(
                tipo=tipo_obj,
                marca=marca_obj,
                color=color_obj,
                defaults={
                    "costo_por_gramo": costo,
                    "stock_minimo": minimo,
                    "stock_actual": 0,
                },
            )
            if created:
                messages.success(
                    request, f"Material {str(material)} creado exitosamente."
                )
            else:
                messages.info(request, "Este material ya existía en el catálogo.")
        except Exception as e:
            messages.error(request, f"Error al crear el material: {e}")

    return redirect("materiales:lista_materiales")


@login_required
def editar_material(request, material_id):
    """
    Edita propiedades un material y gestione pérdidas/mermas manuales.
    Si se reporta pérdida, descuenta stock y registra en historial.
    """
    material = get_object_or_404(Material, id=material_id)

    if request.method == "POST":
        # Extraemos los valores manualmente para asegurar precisión
        nuevo_costo = abs(Decimal(request.POST.get("costo_por_gramo", 0) or 0))
        nuevo_minimo = abs(Decimal(request.POST.get("stock_minimo", 0) or 0))

        # 1. Actualizamos los campos básicos directamente
        material.costo_por_gramo = nuevo_costo
        material.stock_minimo = nuevo_minimo

        # 2. Lógica de pérdida (antes de guardar todo)
        if request.POST.get("es_perdida") == "on":
            cantidad_p = abs(Decimal(request.POST.get("cantidad_perdida") or 0))

            if cantidad_p > 0:
                stock_viejo = material.stock_actual
                # Limitamos la pérdida al stock disponible
                if cantidad_p > material.stock_actual:
                    cantidad_p = material.stock_actual

                material.stock_actual -= cantidad_p

                # Registramos en historial
                HistorialInventario.objects.create(
                    material=material,
                    accion="Eliminación",
                    cantidad_anterior=stock_viejo,
                    cantidad_nueva=material.stock_actual,
                    diferencia=-cantidad_p,
                )
                messages.warning(request, f"Se descontaron {cantidad_p}g del stock.")

        # 3. Guardado final de todos los cambios
        material.save()
        messages.success(request, "Material actualizado correctamente.")

    return redirect("materiales:lista_materiales")

@login_required
def registrar_entrada(request):
    """
    Registra una compra o reabastecimiento de material.
    Aumenta el stock disponible.
    """
    if request.method == "POST":
        data = request.POST.copy()
        # Blindaje: cantidad y costo siempre positivos
        data["cantidad_gramos"] = abs(Decimal(data.get("cantidad_gramos", 0) or 0))
        data["costo_total"] = abs(Decimal(data.get("costo_total", 0) or 0))

        form = EntradaInventarioForm(data)
        if form.is_valid():
            form.save()
            messages.success(request, "Entrada de inventario registrada.")
        else:
            messages.error(request, "Error: Verifique que los datos sean correctos.")
    return redirect("materiales:lista_materiales")

def buscar_material_ajax(request):
    query = request.GET.get('q', request.GET.get('material_search', '')).strip() # HTMX enviará el nombre del input
    if len(query) >= 2:
        materiales = Material.objects.filter(
            Q(marca__nombre__icontains=query) |
            Q(tipo__nombre__icontains=query) |
            Q(color__nombre__icontains=query)
        )[:4] # Limitamos a 5 resultados para que no sea gigante
    else:
        materiales = []

    return render(request, "materiales/partials/resultados_busqueda_material.html", {"materiales": materiales})


@login_required
def obtener_material_json(request, material_id):
    """
    API JSON: Devuelve datos de un material para su edición rápida.
    """
    material = get_object_or_404(Material, id=material_id)
    return JsonResponse(
        {
            "id": material.id,
            "nombre": str(material),
            "tipo": material.tipo.nombre,
            "costo_por_gramo": "{:.2f}".format(material.costo_por_gramo),
            "stock_minimo": float(material.stock_minimo),
            "stock_actual": float(material.stock_actual),
        }
    )