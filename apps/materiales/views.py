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
from django.db import transaction, IntegrityError

from .models import (TipoMaterial, Material, Color, Marca,
                     EntradaInventario, HistorialInventario, ConsumoMaterial)

from .forms import MaterialForm, EntradaInventarioForm, EditarMaterialForm

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
    orden_filtro = request.GET.get('orden', '')
    if search_query:
        materiales_qs = materiales_qs.filter(
            Q(marca__nombre__icontains=search_query) |
            Q(tipo__nombre__icontains=search_query) |
            Q(color__nombre__icontains=search_query)
        )

    #Aplicar Lógica de Filtro (por ejemplo, Filamento vs Resina)
    if tipo_filtro:
        materiales_qs = materiales_qs.filter(tipo_id=tipo_filtro)
    if orden_filtro == "stock_asc":
        materiales_qs = materiales_qs.order_by("stock_actual", "tipo__nombre")
    elif orden_filtro == "stock_desc":
        materiales_qs = materiales_qs.order_by("-stock_actual", "tipo__nombre")
    else:
        # Orden por defecto: Alfabético
        materiales_qs = materiales_qs.order_by("tipo__nombre", "marca__nombre")

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
        "orden_actual": orden_filtro,
    }

    if request.headers.get('HX-Request'):
        return render(request, "materiales/partials/material_tabla.html", context)
    
    return render(request, "materiales/material_list.html", context)

@login_required
def crear_material(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save()
            
            if material.just_created:
                messages.success(request, f"Material {material} creado con éxito.")
            else:
                messages.warning(request, f"El material {material} ya existe en el sistema.")
        else:
            messages.error(request, "Error al procesar el formulario. Revisa los datos.")
            
    return redirect("materiales:lista_materiales")

@login_required
def buscar_atributo_ajax(request):
    # Intentamos obtener 'q' (el estándar) o el nombre específico del input
    query = request.GET.get('q') or request.GET.get('marca_nombre') or request.GET.get('tipo_nombre') or request.GET.get('color_nombre') or ''
    query = query.strip()
    
    tipo_busqueda = request.GET.get('tipo', '') 
    
    resultados = []
    if len(query) >= 1:
        if tipo_busqueda == 'marca':
            resultados = Marca.objects.filter(nombre__icontains=query)[:5]
        elif tipo_busqueda == 'tipo':
            resultados = TipoMaterial.objects.filter(nombre__icontains=query)[:5]
        elif tipo_busqueda == 'color':
            resultados = Color.objects.filter(nombre__icontains=query)[:5]
            
    return render(request, "materiales/partials/resultados_atributos.html", {
        "resultados": resultados,
        "tipo": tipo_busqueda
    })

@login_required
def editar_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.method == "POST":
        form = EditarMaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, "Material actualizado correctamente.")
        else:
            # Si el formulario no es válido (ej: stock en cero), capturamos el error
            for error in form.non_field_errors():
                messages.error(request, error)
            # También podrías iterar form.errors si quieres ser más específico
            
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

@login_required
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

@login_required
def gestionar_atributo(request, modelo_tipo, objeto_id):
    modelos = {'marca': Marca, 'tipo': TipoMaterial, 'color': Color}
    model_class = modelos.get(modelo_tipo)
    objeto = get_object_or_404(model_class, id=objeto_id)
    
    if request.method == "POST":
        nuevo_nombre = request.POST.get("nuevo_nombre").strip()
        existente = model_class.objects.filter(nombre__iexact=nuevo_nombre).exclude(id=objeto.id).first()
        
        try:
            with transaction.atomic():
                if existente:
                    # Buscamos todos los materiales que usan el atributo viejo (ej: SASA)
                    filtro = {modelo_tipo: objeto}
                    materiales_a_mover = Material.objects.filter(**filtro)

                    for mat_viejo in materiales_a_mover:
                        # Buscamos si ya existe un material igual pero con el atributo nuevo (ej: ASA)
                        busqueda_clon = {
                            'marca': mat_viejo.marca,
                            'tipo': mat_viejo.tipo,
                            'color': mat_viejo.color,
                        }
                        # Reemplazamos el atributo que estamos gestionando en la búsqueda
                        busqueda_clon[modelo_tipo] = existente
                        
                        mat_clon = Material.objects.filter(**busqueda_clon).first()

                        if mat_clon:
                            # ¡COLISIÓN DETECTADA! Fusionamos datos
                            mat_clon.stock_actual += mat_viejo.stock_actual
                            mat_clon.save()
                            
                            # Movemos el historial para no perder el rastro
                            HistorialInventario.objects.filter(material=mat_viejo).update(material=mat_clon)
                            
                            # Borramos el material viejo que ya no sirve
                            mat_viejo.delete()
                        else:
                            # No hay colisión, solo actualizamos el atributo
                            setattr(mat_viejo, modelo_tipo, existente)
                            mat_viejo.save()
                    
                    objeto.delete() # Borramos SASA
                    messages.success(request, f"Fusión exitosa. '{nuevo_nombre}' ha absorbido los materiales.")
                else:
                    # Simple renombramiento (no hay riesgo de colisión)
                    objeto.nombre = nuevo_nombre
                    objeto.save()
                    messages.success(request, f"Nombre corregido a '{nuevo_nombre}'.")
                    
        except Exception as e:
            messages.error(request, f"Error durante la gestión: {str(e)}")
            
    return redirect('materiales:lista_materiales')