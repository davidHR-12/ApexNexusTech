from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, F, Q
from django.http import JsonResponse, HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme
from apps.usuarios.decorators import admin_required
from django.db import transaction
from django.urls import reverse
from decimal import Decimal
import json
import logging
import hashlib
from django.db.models import ProtectedError
from django.db import IntegrityError

from .models import Categoria, Producto, VarianteProducto, ImagenProducto, ProduccionInterna
from .forms import CategoriaForm, ProductoForm, ProduccionInternaForm, VarianteProductoForm, MaterialDetalleFormSet


def _generar_firma_materiales(materiales):
    """
    Genera una firma hash única a partir de una lista ordenada de tuplas (material_id, gramos).
    Se usa para detectar variantes duplicadas.
    """
    base_string = "|".join(f"{mat_id}-{gramos}" for mat_id, gramos in materiales)
    return hashlib.sha256(base_string.encode()).hexdigest()


def _redirect_producto_detalle_htmx(request, producto):
    """Redirige a la página de detalle del producto usando HTMX"""
    response = HttpResponse()
    response["HX-Redirect"] = reverse("productos:producto_detalle", kwargs={"slug": producto.slug})
    return response


@admin_required
def product_list(request):
    """Muestra el listado de categorías con búsqueda HTMX y estadísticas de variantes."""
    search_query = request.GET.get("search", "")
    
    # Filtrado de categorías basado en la búsqueda
    categorias = Categoria.objects.annotate(total_productos=Count("productos")).order_by("orden")
    
    if search_query:
        categorias = categorias.filter(
            Q(nombre__icontains=search_query) | 
            Q(descripcion__icontains=search_query)
        ).distinct()

    # Estadísticas generales (se calculan sobre todo el inventario, no solo el filtrado)
    total_modelos = Producto.objects.count()
    total_stock_fisico = VarianteProducto.objects.aggregate(total=Sum('stock_disponible'))['total'] or 0
    valor_inventario = VarianteProducto.objects.aggregate(
        total=Sum(F('producto__precio_venta') * F('stock_disponible'))
    )['total'] or 0

    context = {
        "categorias": categorias,
        "total_modelos": total_modelos,
        "total_stock_fisico": total_stock_fisico,
        "valor_inventario": valor_inventario,
        "search_query": search_query,
    }

    # Si es una petición de HTMX, solo devolvemos el listado de tarjetas
    if request.headers.get("HX-Request"):
        return render(request, "productos/partials/categoria_listado.html", context)

    return render(request, "productos/producto_list.html", context)


@admin_required
def crear_producto_base(request, categoria_id=None):
    """Crea un producto base asegurando que la categoría no sea manipulada por el usuario"""
    if request.method == "POST":
        datos_post = request.POST.copy()
        
        # Fuerza la categoría desde la URL, ignorando cualquier manipulación del formulario
        if categoria_id:
            datos_post['categoria'] = categoria_id
        
        form = ProductoForm(datos_post, request.FILES, categoria_predefinida=categoria_id)
        
        if form.is_valid():
            producto = form.save()
            messages.success(request, f"Producto '{producto.nombre}' creado exitosamente.")
            
            # Redirección segura
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
            for error in form.non_field_errors():
                messages.error(request, error)

            # 2. Manejar errores de campos específicos
            for field, errors in form.errors.items():
                if field == '__all__':
                    continue # Ya manejado arriba
                for error in errors:
                    if field == 'nombre':
                        # Si es el nombre, enviamos solo el error (ej: "Ya existe un producto...")
                        messages.error(request, error)
                    else:
                        # Para otros campos, mantenemos el formato descriptivo
                        nombre_campo = field.replace('_', ' ').capitalize()
                        messages.error(request, f"{nombre_campo}: {error}")
            return redirect(request.META.get("HTTP_REFERER", "productos:productos_index"))

    return redirect("productos:productos_index")


@admin_required
def producto_detalle(request, slug):
    """Muestra el detalle completo de un producto, incluyendo sus variantes y galería"""
    producto = get_object_or_404(Producto.objects.prefetch_related('variantes'), slug=slug)
    context = {"producto": producto}
    return render(request, "productos/producto_detalle.html", context)


@admin_required
def editar_producto_base(request, producto_id):
    """Permite editar la información básica de un producto"""
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


@admin_required
def eliminar_producto_base(request, producto_id):
    """
    Elimina un producto o lo desactiva si tiene historial asociado.
    Retorna una respuesta JSON.
    """
    if request.method == "POST":
        producto = get_object_or_404(Producto, id=producto_id)
        
        tiene_stock = producto.variantes.filter(stock_disponible__gt=0).exists()
        tiene_historial_produccion = ProduccionInterna.objects.filter(variante__producto=producto).exists()
        tiene_ventas = False

        if tiene_stock or tiene_historial_produccion or tiene_ventas:
            producto.activo = False
            producto.mostrar_en_web = False
            producto.save()
            return JsonResponse({
                "success": True,
                "message": "El producto tiene historial de producción o stock. Se ha desactivado para no afectar los registros históricos."
            })
        else:
            producto.delete()
            return JsonResponse({
                "success": True,
                "message": "Producto eliminado permanentemente ya que no contenía registros vinculados."
            })
            
    return JsonResponse({"success": False, "message": "Método no permitido"}, status=405)


@admin_required
def eliminar_imagenes_producto_bulk(request):
    """Elimina múltiples imágenes de la galería de productos recibiendo una lista de IDs"""
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


@admin_required
def obtener_producto_json(request, pk):
    """Retorna los datos de un producto en formato JSON para su edición"""
    producto = get_object_or_404(Producto, pk=pk)
    imagenes_galeria_data = [
        {"id": img.id, "url": img.imagen.url} for img in producto.imagenes.all()
    ]

    data = {
        "nombre": producto.nombre,
        "categoria_id": producto.categoria.id if producto.categoria else None,
        "precio_venta": str(producto.precio_venta),
        "mostrar_en_web": producto.mostrar_en_web,
        "descripcion": producto.descripcion,
        "activo": producto.activo,
        "imagen_url": producto.imagen.url if producto.imagen else None,
        "imagenes_galeria": imagenes_galeria_data,
    }
    return JsonResponse(data)


@admin_required
def obtener_productos_archivados(request, categoria_id):
    """Renderiza una lista parcial con los productos desactivados de una categoría"""
    productos = Producto.objects.filter(activo=False, categoria_id=categoria_id)
    return render(request, "productos/partials/lista_prod_archivados.html", {"productos": productos})


@admin_required
def reactivar_producto(request, producto_id):
    """Reactiva un producto desactivado"""
    if request.method == "POST":
        producto = get_object_or_404(Producto, id=producto_id)
        producto.mostrar_en_web = True
        producto.activo = True
        producto.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)


@admin_required
def reactivar_multiples_productos(request):
    """Reactiva un lote de productos seleccionados por sus IDs"""
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


@admin_required
def obtener_variantes_producto(request, producto_id):
    """Devuelve las variantes disponibles de un producto en formato JSON"""
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


def _verificar_duplicado(producto, materiales_nuevos):
    """
    Verifica si ya existe una variante con la misma combinación de materiales.
    Retorna: (es_duplicado: bool, variante_duplicada: VarianteProducto | None)
    """
    if not materiales_nuevos:
        return False, None
    
    variantes_existentes = producto.variantes.prefetch_related("detalles_material__material")
    
    for variante_ex in variantes_existentes:
        materiales_existentes = [
            (detalle.material.id, Decimal(str(detalle.gramos_usados)))
            for detalle in variante_ex.detalles_material.all()
        ]
        materiales_existentes.sort()
        
        if materiales_nuevos == materiales_existentes:
            return True, variante_ex
    
    return False, None


def _guardar_variante_con_materiales(variante, producto, formset):
    """Guarda la variante y sus materiales de forma transaccional"""
    with transaction.atomic():
        variante.producto = producto
        variante.save()
        formset.instance = variante
        formset.save()


def _procesar_errores_formulario(form, formset):
    """Extrae y retorna una lista de mensajes de error del formulario y formset"""
    errores = []
    
    if not form.is_valid():
        for field, field_errors in form.errors.items():
            for error in field_errors:
                nombre_campo = field.replace('_', ' ').capitalize()
                errores.append(f"{nombre_campo}: {error}")
    
    if not formset.is_valid():
        for error in formset.non_form_errors():
            error_texto = str(error).replace('<ul class="errorlist nonform"><li>', '').replace('</li></ul>', '')
            errores.append(error_texto)
        
        for i, form_errors in enumerate(formset.errors):
            if form_errors:
                for field, field_errors in form_errors.items():
                    if field != '__all__':
                        for error in field_errors:
                            errores.append(f"Material {i+1} - {field}: {error}")
                    else:
                        for error in field_errors:
                            error_str = str(error)
                            # Filtra errores de duplicados en inglés
                            if 'duplicate' not in error_str.lower():
                                errores.append(f"Material {i+1}: {error_str}")
    
    return errores


def _renderizar_formulario(request, producto, form, formset):
    """Renderiza el template con los formularios de variante"""
    return render(
        request,
        "productos/modals/agregar_variante_producto.html",
        {
            "producto": producto,
            "form": form,
            "formset": formset,
        }
    )


@admin_required
def crear_variante(request, producto_id):
    """Maneja la creación de una variante de producto, validando materiales y previniendo duplicados"""
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == "POST":
        form = VarianteProductoForm(request.POST)
        formset = MaterialDetalleFormSet(request.POST)
        
        form_valido = form.is_valid()
        formset_valido = formset.is_valid()
        
        print(f"DEBUG - Form válido: {form_valido}")
        print(f"DEBUG - Formset válido: {formset_valido}")
        print(f"DEBUG - Errores formset: {formset.errors}")
        print(f"DEBUG - Non-form errors: {formset.non_form_errors()}")
        
        if form_valido and formset_valido:
            return _procesar_post_valido(request, producto, form, formset)
        else:
            return _procesar_post_invalido(request, producto, form, formset)
    
    form = VarianteProductoForm()
    formset = MaterialDetalleFormSet()
    return _renderizar_formulario(request, producto, form, formset)

def _procesar_post_valido(request, producto, form, formset):
    """Procesa el POST válido al crear una variante"""
    materiales_nuevos = _extraer_materiales_del_formset(formset)

    if not materiales_nuevos:
        messages.error(request, "Debes agregar al menos un material a la variante.")
        if request.htmx:
            return _redirect_producto_detalle_htmx(request, producto)
        return redirect("productos:producto_detalle", slug=producto.slug)

    firma = _generar_firma_materiales(materiales_nuevos)

    # 1. Validación preventiva manual
    if producto.variantes.filter(firma_materiales=firma).exists():
        messages.error(
            request,
            "Ya existe una variante con exactamente la misma combinación de materiales y gramos."
        )
        if request.htmx:
            return _redirect_producto_detalle_htmx(request, producto)
        return redirect("productos:producto_detalle", slug=producto.slug)

    try:
        # 2. Intento de guardado capturando errores de base de datos
        variante = form.save(commit=False)
        variante.firma_materiales = firma
        _guardar_variante_con_materiales(variante, producto, formset)

        messages.success(request, "Variante creada correctamente.")
        
    except IntegrityError:
        # Este captura el error de UNIQUE constraint directamente desde la DB
        messages.error(
            request, 
            "No se pudo guardar: Ya existe otra variante con esta misma configuración técnica."
        )
    except Exception as e:
        messages.error(request, f"Error inesperado al guardar: {e}")
    
    # Redirección final (común para éxito o error capturado)
    if request.htmx:
        return _redirect_producto_detalle_htmx(request, producto)
    return redirect("productos:producto_detalle", slug=producto.slug)


def _procesar_post_invalido(request, producto, form, formset):
    """Procesa el POST inválido al crear una variante y muestra los errores"""
    errores = _procesar_errores_formulario(form, formset)
    
    print(f"DEBUG - Errores capturados: {errores}")
    
    if errores:
        for error in errores:
            messages.error(request, error)
    else:
        messages.error(request, "Hay errores en el formulario. Verifica los datos ingresados.")

    if request.htmx:
        return _redirect_producto_detalle_htmx(request, producto)
    return redirect("productos:producto_detalle", slug=producto.slug)


@admin_required
def registrar_produccion(request, variante_id):
    """Registra el aumento de stock de una variante mediante una producción interna"""
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


@admin_required
def eliminar_variante_json(request, variante_id):
    if request.method == "POST":
        variante = get_object_or_404(VarianteProducto, id=variante_id)
        try:
            nombre_variante = str(variante)
            variante.delete()
            return JsonResponse({
                "success": True,
                "message": f"Variante '{nombre_variante}' eliminada."
            })
        except ProtectedError:
            return JsonResponse({
                "success": False, 
                "error": "No puedes eliminar esta variante porque ya está asociada a pedidos existentes. Prueba a desactivarla en su lugar.",
                "tipo_error": "protegido"
            }, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "message": "Método no permitido"}, status=405)

@admin_required
def crear_categoria(request):
    """Procesa el formulario para crear una nueva categoría de productos"""
    if request.method == "POST":
        form = CategoriaForm(request.POST, request.FILES)
        if form.is_valid():
            nueva_cat = form.save()
            messages.success(request, f'Categoría "{nueva_cat.nombre}" creada con éxito.')
        else:
            for error in form.errors.values():
                messages.error(request, error)

    return redirect("productos:productos_index")


@admin_required
def editar_categoria(request, categoria_id):
    """Permite modificar los datos de una categoría existente"""
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


@admin_required
def eliminar_categoria(request, categoria_id):
    """Elimina una categoría si no es la categoría por defecto 'Sin Categorizar'"""
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


@admin_required
def categoria_detalle(request, slug):
    """Muestra el detalle de una categoría, incluyendo los productos asociados y estadísticas"""
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


@admin_required
def obtener_categoria_json(request, categoria_id):
    """Retorna los datos de una categoría en formato JSON para edición"""
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    data = {
        "id": categoria.id,
        "nombre": categoria.nombre,
        "descripcion": categoria.descripcion or "",
        "orden": int(categoria.orden) if categoria.orden is not None else 0,
        "imagen": categoria.imagen.url if categoria.imagen else None,
    }
    return JsonResponse(data)


@admin_required
def obtener_precio_variante(request, variante_id):
    """Retorna el precio unitario desglosado y peso de una variante específica"""
    try:
        variante = get_object_or_404(VarianteProducto.objects.select_related('producto'), id=variante_id)
        
        return JsonResponse({
            'precio_base': float(variante.producto.precio_venta),
            'precio_extra': float(variante.precio_adicional),
            'precio_unitario': float(variante.precio_final),
            'gramos_por_unidad': float(variante.peso_total),
            'nombre': str(variante)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@admin_required
def buscar_material_variante(request):
    """Realiza una búsqueda de materiales y retorna un renderizado parcial compatible con HTMX"""
    from apps.materiales.models import Material
    
    if not request.htmx:
        return HttpResponse(status=403)

    query = request.GET.get("q", "").strip()
    if not query:
        return HttpResponse("")

    field_index = request.GET.get("field_index", "0")
    logger = logging.getLogger(__name__)
    
    logger.info(f"Búsqueda material: query='{query}', field_index={field_index}")
    logger.info(f"Parámetros GET completos: {dict(request.GET)}")

    if not field_index.isdigit():
        return HttpResponse(status=400)

    materiales = []
    
    if len(query) >= 1:
        palabras = query.split()
        materiales_qs = Material.objects.filter(stock_actual__gt=0).select_related("marca", "tipo", "color")
        
        for palabra in palabras:
            materiales_qs = materiales_qs.filter(
                Q(marca__nombre__icontains=palabra) |
                Q(tipo__nombre__icontains=palabra) |
                Q(color__nombre__icontains=palabra)
            )

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

logger = logging.getLogger(__name__)

@admin_required
def toggle_variante_activo(request, variante_id):
    if request.method == "POST":
        try:
            variante = get_object_or_404(VarianteProducto, id=variante_id)
            variante.activa = not variante.activa
            # Usamos full_clean para ver si hay errores de validación antes de salvar
            variante.save() 
            
            estado = "activada" if variante.activa else "desactivada"
            return JsonResponse({
                "success": True, 
                "nuevo_estado": variante.activa,
                "message": f"Variante {estado} correctamente"
            })
        except Exception as e:
            # Esto imprimirá el error real en consola
            print(f"ERROR AL TOGGLE VARIANTE: {str(e)}") 
            return JsonResponse({
                "success": False, 
                "error": str(e)
            }, status=500)
            
    return JsonResponse({"success": False}, status=405)

# --- VISTA PARA REACTIVACIÓN MÚLTIPLE ---
@admin_required
def reactivar_multiples_variantes(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ids = data.get('ids', [])
            # Actualizamos de forma masiva (esto no llama al método save() individual,
            # lo cual es más rápido y evita errores de validación individuales)
            VarianteProducto.objects.filter(id__in=ids).update(activa=True)
            
            return JsonResponse({
                "success": True,
                "message": f"{len(ids)} variantes reactivadas correctamente"
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"success": False}, status=405)

@admin_required
def obtener_variantes_archivadas(request, producto_id):
    # Obtenemos el producto o devolvemos 404
    producto = get_object_or_404(Producto, id=producto_id)
    
    # Filtramos solo las variantes que están desactivadas
    # Usamos select_related o prefetch_related para optimizar la carga de materiales
    variantes = producto.variantes.filter(activa=False).prefetch_related(
        'detalles_material__material__color',
        'detalles_material__material__marca'
    )
    
    return render(request, 'productos/partials/lista_variantes_archivadas.html', {
        'variantes': variantes,
        'producto': producto
    })

@admin_required
def editar_variante(request, variante_id):
    variante = get_object_or_404(VarianteProducto, id=variante_id)
    if request.method == "POST":
        form = VarianteProductoForm(request.POST, instance=variante)
        if form.is_valid():
            form.save()
            messages.success(request, "Variante actualizada correctamente.")
            return redirect("productos:producto_detalle", slug=variante.producto.slug)
        else:
            return render(request, "productos/modals/editar_variante.html", {
                "producto": variante.producto,
                "editando": True,
                "variante": variante
            })
    
    form = VarianteProductoForm(instance=variante)
    return render(request, "productos/modals/editar_variante.html", {
        "form": form,
        "producto": variante.producto,
        "editando": True,
        "variante": variante
    })