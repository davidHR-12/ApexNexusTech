from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from decimal import Decimal
import json
import logging
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.db import transaction

from .models import Categoria, Producto, VarianteProducto, ImagenProducto, ProduccionInterna
from .forms import CategoriaForm, ProductoForm, ProduccionInternaForm, VarianteProductoForm, MaterialDetalleFormSet


# Vista para listar los productos y mostrar estadísticas generales
@staff_member_required
def product_list(request):
    """
    Muestra el listado de categorías con sus productos y estadísticas generales del inventario.
    """
    categorias = Categoria.objects.annotate(total_productos=Count("productos")).order_by("orden")

    # Contar total de modelos de productos registrados
    total_modelos = Producto.objects.count()

    # Calcular el stock físico total sumando el stock de todas las variantes
    total_stock_fisico = VarianteProducto.objects.aggregate(
        total=Sum('stock_disponible')
    )['total'] or 0

    # Calcular valor del inventario (Precio venta * Stock disponible)
    valor_inventario = VarianteProducto.objects.aggregate(
        total=Sum(F('producto__precio_venta') * F('stock_disponible'))
    )['total'] or 0

    return render(
        request,
        "productos/producto_list.html",
        {
            "categorias": categorias,
            "total_modelos": total_modelos,
            "total_stock_fisico": total_stock_fisico,
            "valor_inventario": valor_inventario,
        },
    )


# Vista para crear un nuevo producto base
@staff_member_required
def crear_producto_base(request, categoria_id=None): # El ID es opcional por si usas la vista general
    """
    Crea un producto base asegurando que la categoría no sea manipulada.
    """
    if request.method == "POST":
        # Hacemos una copia mutable del POST para forzar la categoría
        datos_post = request.POST.copy()
        
        # SEGURIDAD: Si la URL trae una categoría, la forzamos. 
        # Esto ignora cualquier cambio hecho por el usuario en el HTML.
        if categoria_id:
            datos_post['categoria'] = categoria_id
        
        # Pasamos categoria_predefinida para que el form aplique los estilos grises
        form = ProductoForm(
            datos_post, 
            request.FILES, 
            categoria_predefinida=categoria_id
        )
        
        if form.is_valid():
            # Guardamos el producto
            producto = form.save()
            
            messages.success(request, f"Producto '{producto.nombre}' creado exitosamente.")
            
            # --- Lógica de redirección segura ---
            next_url = request.POST.get("next")
            is_safe = url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            )
            
            if next_url and is_safe:
                return redirect(next_url)
            return redirect("productos:producto_detalle", slug=producto.slug)
        
        else:
            # Si el formulario no es válido, reportamos errores
            for field, errors in form.errors.items():
                for error in errors:
                    # Traducimos el nombre del campo para el usuario si es necesario
                    nombre_campo = field.replace('_', ' ').capitalize()
                    messages.error(request, f"{nombre_campo}: {error}")
            
            # Volvemos a la página anterior para que el modal se pueda reabrir con los errores
            return redirect(request.META.get("HTTP_REFERER", "productos:productos_index"))

    # Si no es POST, simplemente regresamos al índice
    return redirect("productos:productos_index")


# Vista para ver el detalle de un producto específico
@staff_member_required
def producto_detalle(request, slug):
    """
    Muestra el detalle completo de un producto, incluyendo sus variantes y galería.
    """
    producto = get_object_or_404(Producto.objects.prefetch_related('variantes'), slug=slug)

    context = {
        "producto": producto,
    }
    return render(request, "productos/producto_detalle.html", context)


# Vista para editar un producto existente
@staff_member_required
def editar_producto_base(request, producto_id):
    """
    Permite editar la información básica de un producto.
    Maneja la eliminación de la imagen de portada si se solicita.
    """
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        eliminar_portada = request.POST.get('eliminar_portada_flag') == 'true'
        
        if eliminar_portada and producto.imagen:
            producto.imagen.delete(save=False)
            producto.imagen = None
        
        form = ProductoForm(request.POST, request.FILES, instance=producto)

        if form.is_valid():
            producto_editado = form.save()
            messages.success(request, f"'{producto_editado.nombre}' actualizado correctamente.")

            next_url = request.POST.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("productos:categoria_detalle", slug=producto_editado.categoria.slug)
        else:
            messages.error(request, "Error al actualizar el producto. Verifique los datos.")

    return redirect("productos:productos_index")


# Vista para eliminar (o desactivar) un producto
@staff_member_required
def eliminar_producto_base(request, producto_id):
    """
    Elimina un producto o lo desactiva si tiene historial asociado (stock, producción, ventas).
    Retorna una respuesta JSON.
    """
    if request.method == "POST":
        producto = get_object_or_404(Producto, id=producto_id)
        
        # Verificar dependencias antes de eliminar
        tiene_stock = producto.variantes.filter(stock_disponible__gt=0).exists()
        tiene_historial_produccion = ProduccionInterna.objects.filter(variante__producto=producto).exists()
        tiene_ventas = False 

        if tiene_stock or tiene_historial_produccion or tiene_ventas:
            # Borrado lógico si hay historial
            producto.activo = False
            producto.mostrar_en_web = False
            producto.save()
            return JsonResponse({
                "success": True, 
                "message": "El producto tiene historial de producción o stock. Se ha desactivado para no afectar los registros históricos."
            })
        else:
            # Borrado físico si no hay historial
            producto.delete()
            return JsonResponse({
                "success": True, 
                "message": "Producto eliminado permanentemente ya que no contenía registros vinculados."
            })
            
    return JsonResponse({"success": False, "message": "Método no permitido"}, status=405)


# Vista para eliminar múltiples imágenes de un producto
@staff_member_required
def eliminar_imagenes_producto_bulk(request):
    """
    Elimina múltiples imágenes de la galería de productos recibiendo una lista de IDs.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            imagenes_ids = data.get('imagenes', [])
            
            if not imagenes_ids:
                return JsonResponse({"status": "error", "message": "No se enviaron imágenes"}, status=400)
            
            eliminadas = 0
            errores = []
            
            for imagen_id in imagenes_ids:
                try:
                    imagen = ImagenProducto.objects.get(id=imagen_id)
                    if imagen.imagen:
                        imagen.imagen.delete(save=False)
                    imagen.delete()
                    eliminadas += 1
                except ImagenProducto.DoesNotExist:
                    errores.append(f"Imagen {imagen_id} no encontrada")
                except Exception as e:
                    errores.append(f"Error al eliminar imagen {imagen_id}: {str(e)}")
            
            if errores:
                return JsonResponse({
                    "status": "partial",
                    "eliminadas": eliminadas,
                    "errores": errores
                }, status=207)
            
            return JsonResponse({
                "status": "ok",
                "eliminadas": eliminadas,
                "message": f"{eliminadas} imagen(es) eliminada(s) correctamente"
            })
            
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "JSON inválido"}, status=400)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "error", "message": "Método no permitido"}, status=405)


# Vista para obtener datos de un producto en formato JSON
@staff_member_required
def obtener_producto_json(request, pk):
    """
    Retorna los datos de un producto en formato JSON para su edición rápida.
    """
    producto = get_object_or_404(Producto, pk=pk)

    imagenes_galeria_data = [
        {"id": img.id, "url": img.imagen.url} for img in producto.imagenes.all()
    ]

    data = {
        "nombre": producto.nombre,
        "categoria_id": producto.categoria.id if producto.categoria else None,
        "precio_venta": str(producto.precio_venta),
        "peso_gramos": str(producto.peso_gramos),
        "mostrar_en_web": producto.mostrar_en_web,
        "descripcion": producto.descripcion,
        "imagen_url": producto.imagen.url if producto.imagen else None,
        "imagenes_galeria": imagenes_galeria_data,
    }
    return JsonResponse(data)


# Vista para obtener productos archivados de una categoría
@staff_member_required
def obtener_productos_archivados(request, categoria_id):
    """
    Renderiza una lista parcial con los productos desactivados (archivados) de una categoría.
    """
    productos = Producto.objects.filter(activo=False, categoria_id=categoria_id)
    return render(request, "productos/partials/lista_prod_archivados.html", {"productos": productos})


# Vista para reactivar un producto archivado
@staff_member_required
def reactivar_producto(request, producto_id):
    """
    Reactiva un producto desactivado, volviéndolo visible y activo.
    """
    if request.method == "POST":
        producto = get_object_or_404(Producto, id=producto_id)
        producto.mostrar_en_web = True
        producto.activo = True
        producto.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)


# Vista para reactivar múltiples productos a la vez
@staff_member_required
def reactivar_multiples_productos(request):
    """
    Reactiva un lote de productos seleccionados por sus IDs.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])
            
            if not ids:
                return JsonResponse({"success": False, "message": "No se seleccionaron productos"}, status=400)
            
            Producto.objects.filter(id__in=ids).update(activo=True, mostrar_en_web=True)
            
            return JsonResponse({"success": True, "message": f"{len(ids)} productos restaurados"})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
    return JsonResponse({"success": False}, status=405)


# Vista para obtener las variantes de un producto en JSON
@staff_member_required
def obtener_variantes_producto(request, producto_id):
    """
    Devuelve las variantes disponibles de un producto en formato JSON.
    """
    producto = get_object_or_404(Producto, id=producto_id)
    variantes = producto.variantes.all()
    data = []
    for v in variantes:
        materiales_nombres = ", ".join([
            f"{d.material.color.nombre} ({d.material.tipo.nombre})" 
            for d in v.detalles_material.all()
        ])
        data.append({
            "id": v.id,
            "nombre_material": materiales_nombres if materiales_nombres else "Sin materiales configurados",
            "stock_disponible": v.stock_disponible,
        })
    return JsonResponse({"variantes": data})



# --- FUNCIONES AUXILIARES PRIVADAS ---

def _extraer_materiales_del_formset(formset):
    """
    Extrae materiales válidos del formset validado.
    Retorna lista de tuplas (material_id, gramos) ordenada.
    """
    nuevos_materiales = []
    for f in formset:
        if f.cleaned_data and not f.cleaned_data.get("DELETE"):
            mat = f.cleaned_data.get("material")
            gramos = f.cleaned_data.get("gramos_usados")
            if mat and gramos:
                nuevos_materiales.append((mat.id, Decimal(str(gramos))))
    nuevos_materiales.sort()
    return nuevos_materiales

# Verificar duplicados
def _verificar_duplicado(producto, materiales_nuevos):
    """
    Verifica si ya existe una variante con la misma combinación de materiales.
    Retorna: (es_duplicado: bool, variante_duplicada: VarianteProducto | None)
    """
    if not materiales_nuevos:
        return False, None
    
    variantes_existentes = producto.variantes.prefetch_related(
        "detalles_material__material"
    )
    
    for variante_ex in variantes_existentes:
        materiales_existentes = [
            (detalle.material.id, Decimal(str(detalle.gramos_usados)))
            for detalle in variante_ex.detalles_material.all()
        ]
        materiales_existentes.sort()
        
        if materiales_nuevos == materiales_existentes:
            return True, variante_ex
    
    return False, None

# Guardar variante con materiales
def _guardar_variante_con_materiales(variante, producto, formset):
    """
    Guarda la variante y sus materiales de forma transaccional.
    Lanza excepción si hay error.
    """
    with transaction.atomic():
        variante.producto = producto
        variante.save()
        formset.instance = variante
        formset.save()

# Procesar errores de formulario
def _procesar_errores_formulario(form, formset):
    """
    Extrae y retorna una lista de mensajes de error del formulario y formset.
    """
    errores = []
    
    # Errores del formulario principal
    if not form.is_valid():
        for field, field_errors in form.errors.items():
            for error in field_errors:
                errores.append(f"{field}: {error}")
    
    # Errores del formset
    if not formset.is_valid():
        for error in formset.non_form_errors():
            errores.append(str(error))
        for i, form_errors in enumerate(formset.errors):
            if form_errors:
                for field, field_errors in form_errors.items():
                    for error in field_errors:
                        errores.append(f"Material {i+1} - {field}: {error}")
    
    return errores

# Renderizar formulario
def _renderizar_formulario(request, producto, form, formset):
    """
    Renderiza el template con los formularios.
    """
    return render(
        request,
        "productos/modals/agregar_variante_producto.html",
        {
            "producto": producto,
            "form": form,
            "formset": formset,
        }
    )


# --- VISTA PRINCIPAL ---

# Crear variante
@staff_member_required
def crear_variante(request, producto_id):
    """
    Maneja la creación de una variante de producto, incluyendo la validación
    de materiales y la prevención de duplicados.
    """
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == "POST":
        form = VarianteProductoForm(request.POST)
        formset = MaterialDetalleFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            return _procesar_post_valido(
                request, producto, form, formset
            )
        else:
            return _procesar_post_invalido(
                request, producto, form, formset
            )
    
    # GET: mostrar formulario vacío
    form = VarianteProductoForm()
    formset = MaterialDetalleFormSet()
    return _renderizar_formulario(request, producto, form, formset)

# Procesar POST válido
def _procesar_post_valido(request, producto, form, formset):
    """
    Lógica para POST válido: valida duplicados y guarda.
    """
    # Extraer y validar materiales
    materiales_nuevos = _extraer_materiales_del_formset(formset)
    
    if not materiales_nuevos:
        messages.error(
            request,
            "Debes agregar al menos un material a la variante."
        )
        return redirect("productos:producto_detalle", slug=producto.slug)
    
    # Verificar duplicados
    es_duplicado, _ = _verificar_duplicado(producto, materiales_nuevos)
    if es_duplicado:
        messages.error(
            request,
            "Ya existe una variante con exactamente la misma combinación "
            "de materiales y gramos."
        )
        return redirect("productos:producto_detalle", slug=producto.slug)
    
    # Guardar
    try:
        variante = form.save(commit=False)
        _guardar_variante_con_materiales(variante, producto, formset)
        messages.success(request, "Variante creada correctamente.")
        return redirect("productos:producto_detalle", slug=producto.slug)
    except Exception as e:
        messages.error(request, f"Error al guardar: {e}")
        return redirect("productos:producto_detalle", slug=producto.slug)

# Procesar POST inválido
def _procesar_post_invalido(request, producto, form, formset):
    """
    Lógica para POST inválido: muestra errores.
    """
    errores = _procesar_errores_formulario(form, formset)
    for error in errores:
        messages.error(request, error)
    
    return _renderizar_formulario(request, producto, form, formset)


# Vista para registrar producción de una variante
@staff_member_required
def registrar_produccion(request, variante_id):
    """
    Registra el aumento de stock de una variante mediante una producción interna.
    """
    variante = get_object_or_404(VarianteProducto, id=variante_id)
    
    if request.method == "POST":
        data = {
            'variante': variante.id,
            'cantidad_producida': request.POST.get('cantidad'),
            'observaciones': request.POST.get('observaciones', '')
        }

        form = ProduccionInternaForm(data)
        
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Producción de {data['cantidad_producida']} unidades registrada.")
            except ValueError as e:
                messages.error(request, str(e))
            
            return redirect("productos:producto_detalle", slug=variante.producto.slug)
        else:
            for error in form.non_field_errors():
                messages.error(request, error)

            for field in form:
                for error in field.errors:
                    messages.error(request, f"{field.label}: {error}")
            return redirect("productos:producto_detalle", slug=variante.producto.slug)
    
    return render(request, "productos/modals/registrar_produccion.html", {"variante": variante})


# Vista para eliminar una variante vía JSON
@staff_member_required
def eliminar_variante_json(request, variante_id):
    """
    Elimina una variante específica y retorna confirmación en JSON.
    """
    if request.method == "POST":
        variante = get_object_or_404(VarianteProducto, id=variante_id)
        try:
            nombre_variante = str(variante)
            variante.delete()
            return JsonResponse({
                "success": True, 
                "message": f"Variante '{nombre_variante}' eliminada."
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "message": "Método no permitido"}, status=405)


# Vista para crear una nueva categoría
@staff_member_required
def crear_categoria(request):
    """
    Procesa el formulario para crear una nueva categoría de productos.
    """
    if request.method == "POST":
        form = CategoriaForm(request.POST, request.FILES)
        if form.is_valid():
            nueva_cat = form.save()
            messages.success(
                request, f'Categoría "{nueva_cat.nombre}" creada con éxito.'
            )
        else:
            for error in form.errors.values():
                messages.error(request, error)

    return redirect("productos:productos_index")


# Vista para editar una categoría existente
@staff_member_required
def editar_categoria(request, categoria_id):
    """
    Permite modificar los datos de una categoría existente.
    """
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    if request.method == "POST":
        form = CategoriaForm(request.POST, request.FILES, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, f'Categoría "{categoria.nombre}" actualizada.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    print(f"Error en {field}: {error}")
                    messages.error(request, f"Error en {field}: {error}")
                    
    return redirect("productos:productos_index")


# Vista para eliminar una categoría
@staff_member_required
def eliminar_categoria(request, categoria_id):
    """
    Elimina una categoría si no es la categoría por defecto 'Sin Categorizar'.
    """
    if request.method == "POST":
        categoria = get_object_or_404(Categoria, id=categoria_id)

        if categoria.nombre == "Sin Categorizar":
            return JsonResponse({
                "success": False,
                "message": "No puedes eliminar la categoría de respaldo.",
            }, status=400)

        nombre_eliminado = categoria.nombre
        categoria.delete()

        messages.success(request, f'Categoría "{nombre_eliminado}" eliminada correctamente.')

        return JsonResponse({
            "success": True,
            "message": "Eliminado con éxito"
        })

    return JsonResponse({"success": False, "message": "Método no permitido."}, status=405)


# Vista para ver el detalle de una categoría
@staff_member_required
def categoria_detalle(request, slug):
    """
    Muestra el detalle de una categoría, incluyendo los productos asociados y estadísticas.
    """
    categoria = get_object_or_404(Categoria, slug=slug)

    productos = categoria.productos.filter(activo=True)
    todas_las_categorias = Categoria.objects.all()

    total_stock = sum(p.stock_total for p in productos)
    valor_inventario = sum(p.precio_venta * p.stock_total for p in productos)

    return render(
        request,
        "productos/categoria_detalle.html",
        {
            "categoria": categoria,
            "productos": productos,
            "total_stock": total_stock,
            "valor_inventario": valor_inventario,
            "categorias": todas_las_categorias,
        },
    )


# Vista para obtener datos de categoría en JSON
@staff_member_required
def obtener_categoria_json(request, categoria_id):
    """
    Retorna los datos de una categoría en formato JSON para edición.
    """
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    data = {
        "id": categoria.id,
        "nombre": categoria.nombre,
        "descripcion": categoria.descripcion or "",
        "orden": int(categoria.orden) if categoria.orden is not None else 0,
        "imagen": categoria.imagen.url if categoria.imagen else None,
    }
    return JsonResponse(data)


# Vista para obtener el precio de una variante
@staff_member_required
def obtener_precio_variante(request, variante_id):
    """
    Retorna el precio unitario y peso de una variante específica en JSON.
    """
    variante = get_object_or_404(VarianteProducto, id=variante_id)
    gramos = variante.producto.peso_gramos
    precio = variante.precio_final 
    
    return JsonResponse({
        'precio_unitario': float(precio),
        'gramos_por_unidad': float(gramos),
        'nombre': str(variante)
    })


# Vista para buscar materiales para una variante
@staff_member_required
def buscar_material_variante(request):
    """
    Realiza una búsqueda de materiales basada en un término de consulta (query).
    Retorna un renderizado parcial compatible con HTMX.
    """
    from apps.materiales.models import Material
    from django.db.models import Q
    
    if not request.htmx:
        return HttpResponse(status=403)

    query = request.GET.get("q", "").strip()
    if not query:
        return HttpResponse("")

    field_index = request.GET.get("field_index", "0")
    logger = logging.getLogger(__name__)
    
    # Log de la búsqueda
    logger.info(f"Búsqueda material: query='{query}', field_index={field_index}")
    logger.info(f"Parámetros GET completos: {dict(request.GET)}")

    if not field_index.isdigit():
        return HttpResponse(status=400)

    materiales = []
    
    if len(query) >= 1:
        palabras = query.split()
        materiales_qs = Material.objects.filter(
            stock_actual__gt=0
        ).select_related(
            "marca", "tipo", "color"
        )
        
        for palabra in palabras:
            materiales_qs = materiales_qs.filter(
                Q(marca__nombre__icontains=palabra) |
                Q(tipo__nombre__icontains=palabra) |
                Q(color__nombre__icontains=palabra)
            )

        # Ordenar por marca, tipo y color
        materiales = materiales_qs.select_related(
            "marca", "tipo", "color"
        ).distinct().order_by('marca__nombre', 'tipo__nombre', 'color__nombre')[:8]
    
    return render(
        request,
        "productos/partials/resultados_busqueda_material_variante.html",
        {
            "materiales": materiales,
            "field_index": field_index,
            "query": query
        }
    )