from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
import json

from .models import Categoria, Producto, VarianteProducto, ImagenProducto, ProduccionInterna
from .forms import CategoriaForm, ProductoForm, ProduccionInternaForm, VarianteProductoForm


# ==============================================================================
# --- GESTIÓN DE PRODUCTOS ---
# ==============================================================================


@login_required
def product_list(request):
    """
    Lista principal de productos agrupados o visualización general.
    Muestra estadísticas globales del inventario.
    """
    # Traemos categorías con el conteo de sus productos
    categorias = Categoria.objects.annotate(total_productos=Count("productos"))

    # Estadísticas para los cuadros superiores
    total_productos = Producto.objects.count()
    # Calculamos el valor del inventario (precio * stock de variantes)    
    valor_inventario = (
        Producto.objects.aggregate(
            total=Sum(
                F("precio_venta")
            )  
        )["total"]
        or 0
    )

    return render(
        request,
        "productos/producto_list.html",
        {
            "categorias": categorias,
            "total_productos": total_productos,
            "valor_inventario": valor_inventario,
        },
    )


@login_required
def crear_producto_base(request):
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)
        
        if form.is_valid():
            producto = form.save()
            messages.success(request, f"Producto '{producto.nombre}' creado.")
            # --- OPTIMIZACIÓN DE SEGURIDAD ---
            next_url = request.POST.get("next")
            # Verificamos si la URL es segura y pertenece a nuestro host
            is_safe = url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            )
            
            if next_url and is_safe:
                return redirect(next_url)
            return redirect("productos:producto_detalle", slug=producto.slug)
            # ---------------------------------
        else:
            # CAMBIO AQUÍ: Captura TODOS los errores de campos para saber qué falla
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error en {field}: {error}")
            
            # Devuelve a donde venía para que el usuario vea los mensajes
            return redirect(request.META.get("HTTP_REFERER", "productos:productos_index"))

    return redirect("productos:productos_index")


@login_required
def producto_detalle(request, slug):
    """
    Muestra el detalle completo de un producto.
    Incluye variantes, galería, stock y opciones de edición.
    """
    # Optimizamos la consulta para traer variantes junto con el producto
    producto = get_object_or_404(Producto.objects.prefetch_related('variantes'), slug=slug)

    context = {
        "producto": producto,
    }
    return render(request, "productos/producto_detalle.html", context)


@login_required
def editar_producto_base(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        # El form maneja el borrado de portada y actualización de slug internamente
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


@login_required
def eliminar_producto_base(request, producto_id):
    if request.method == "POST":
        producto = get_object_or_404(Producto, id=producto_id)
        
        # 1. Verificar si hay variantes con stock físico
        # Usamos el related_name "variantes" que definiste
        tiene_stock = producto.variantes.filter(stock_disponible__gt=0).exists()
        
        # 2. Verificar si hay registros de Producción Interna
        # Usamos el related_name "producciones" que está en tu clase ProduccionInterna
        tiene_historial_produccion = ProduccionInterna.objects.filter(variante__producto=producto).exists()

        # 3. Verificar si hay pedidos (a futuro la app pedidos 
        # tal vez use una FK a VarianteProducto con related_name="items_pedido")
        # Por ahora, lo dejamos asi en false
        tiene_ventas = False 

        if tiene_stock or tiene_historial_produccion or tiene_ventas:
            # BORRADO LÓGICO: Solo lo ocultamos
            producto.activo = False
            producto.mostrar_en_web = False # Deja de mostrarlo en la parte publica
            producto.save()
            return JsonResponse({
                "success": True, 
                "message": "El producto tiene historial de producción o stock. Se ha desactivado para no afectar los registros históricos."
            })
        else:
            # BORRADO FÍSICO: Se puede eliminar de la base de datos totalmente
            producto.delete()
            return JsonResponse({
                "success": True, 
                "message": "Producto eliminado permanentemente ya que no contenía registros vinculados."
            })
            
    return JsonResponse({"success": False, "message": "Método no permitido"}, status=405)

@login_required
def eliminar_imagenes_producto_bulk(request):
    """
    API: Elimina múltiples imágenes de la galería de productos.
    Recibe un array de IDs y las elimina en batch.
    """
    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body)
            imagenes_ids = data.get('imagenes', [])
            
            if not imagenes_ids:
                return JsonResponse({"status": "error", "message": "No se enviaron imágenes"}, status=400)
            
            eliminadas = 0
            errores = []
            
            for imagen_id in imagenes_ids:
                try:
                    imagen = ImagenProducto.objects.get(id=imagen_id)
                    # Borrar el archivo físico
                    if imagen.imagen:
                        imagen.imagen.delete(save=False)
                    # Borrar el registro
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


@login_required
def obtener_producto_json(request, pk):
    """
    API JSON: Devuelve datos de un producto para edición rápida en modal.
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

@login_required
def obtener_productos_archivados(request, categoria_id):
    # Traemos solo los desactivados de ESTA categoría
    productos = Producto.objects.filter(activo=False, categoria_id=categoria_id)
    return render(request, "productos/partials/lista_prod_archivados.html", {"productos": productos})

@login_required
def reactivar_producto(request, producto_id):
    if request.method == "POST":
        producto = get_object_or_404(Producto, id=producto_id)
        producto.mostrar_en_web = True
        producto.activo = True
        producto.save()
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)

@login_required
def reactivar_multiples_productos(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])
            
            if not ids:
                return JsonResponse({"success": False, "message": "No se seleccionaron productos"}, status=400)
            
            # Actualización masiva eficiente
            Producto.objects.filter(id__in=ids).update(activo=True, mostrar_en_web=True)
            
            return JsonResponse({"success": True, "message": f"{len(ids)} productos restaurados"})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
    return JsonResponse({"success": False}, status=405)

# ==============================================================================
# --- VARIANTES DE PRODUCTO ---
# ==============================================================================


@login_required
def obtener_variantes_producto(request, producto_id):
    """
    API JSON: Devuelve variantes disponibles de un producto.
    Usado para seleccionar qué variante producir.
    """
    producto = get_object_or_404(Producto, id=producto_id)
    variantes = producto.variantes.all()
    data = []
    for v in variantes:
        data.append(
            {
                "id": v.id,
                # Mostramos Marca, Tipo y Color para que el admin sepa qué rollo usa
                "nombre_material": f"{v.material.marca.nombre} {v.material.tipo.nombre} - {v.material.color.nombre}",
                "stock_material": float(v.material.stock_actual),
            }
        )
    return JsonResponse({"variantes": data})


@login_required
def crear_variante(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == "POST":
        form = VarianteProductoForm(request.POST, producto=producto)
        if form.is_valid():
            variante = form.save(commit=False)
            variante.producto = producto
            variante.save() # El modelo genera el SKU automáticamente
            messages.success(request, "Variante añadida correctamente.")
            return redirect("productos:producto_detalle", slug=producto.slug)
    else:
        form = VarianteProductoForm(producto=producto)

    return render(request, "productos/modals/agregar_variante_producto.html", {
        "producto": producto,
        "form": form,
        "title": "Agregar Variante",      
        "modal_id": "modalVariante"
    })

@login_required
def registrar_produccion(request, variante_id):
    variante = get_object_or_404(VarianteProducto, id=variante_id)
    
    if request.method == "POST":
        data = request.POST.copy()
        data['variante'] = variante.id
        data['material'] = variante.material.id
        data['gramos_por_pieza'] = variante.producto.peso_gramos
        data['cantidad_producida'] = request.POST.get('cantidad')

        form = ProduccionInternaForm(data)
        
        if form.is_valid():
            form.save()
            messages.success(request, "Producción registrada y stock actualizado.")
            return redirect("productos:producto_detalle", slug=variante.producto.slug)
        else:
            # Si hay error (como stock insuficiente), enviamos los errores a messages
            for error in form.non_field_errors():
                messages.error(request, error)
            # Redirigimos de vuelta al detalle para que el usuario intente de nuevo
            return redirect("productos:producto_detalle", slug=variante.producto.slug)
    
    # Si es GET, renderizamos el modal normal
    return render(request, "productos/modals/registrar_produccion.html", {
        "variante": variante,
    })


@login_required
def eliminar_variante_json(request, variante_id):
    """
    API JSON: Elimina una variante de producto.
    """
    if request.method == "POST":
        variante = get_object_or_404(VarianteProducto, id=variante_id)
        try:
            nombre_material = str(variante.material)
            variante.delete()
            # Devolvemos éxito para que el JS de SweetAlert sepa que todo salió bien
            return JsonResponse({
                "success": True, 
                "message": f"Variante {nombre_material} eliminada."
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
            
    return JsonResponse({"success": False, "message": "Método no permitido"}, status=405)
    
# ==============================================================================
# --- GESTIÓN DE CATEGORÍAS ---
# ==============================================================================


@login_required
def crear_categoria(request):
    """
    Crea una nueva categoría para agrupar productos.
    """
    if request.method == "POST":
        form = CategoriaForm(request.POST, request.FILES)
        if form.is_valid():
            nueva_cat = form.save()
            messages.success(
                request, f'Categoría "{nueva_cat.nombre}" creada con éxito.'
            )
        else:
            # Capturamos errores específicos si los hay
            for error in form.errors.values():
                messages.error(request, error)

    return redirect("productos:productos_index")


@login_required
def editar_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    if request.method == "POST":
        form = CategoriaForm(request.POST, request.FILES, instance=categoria)
        if form.is_valid():
            form.save() # El form maneja el slug y la imagen internamente
            messages.success(request, f'Categoría "{categoria.nombre}" actualizada.')
    return redirect("productos:productos_index")

@login_required
def eliminar_categoria(request, categoria_id):
    if request.method == "POST":
        categoria = get_object_or_404(Categoria, id=categoria_id)

        if categoria.nombre == "Sin Categorizar":
            return JsonResponse({
                "success": False,
                "message": "No puedes eliminar la categoría de respaldo.",
            }, status=400)

        nombre_eliminado = categoria.nombre
        categoria.delete()

        # Agregamos el mensaje al sistema de Django antes de responder el JSON
        messages.success(request, f'Categoría "{nombre_eliminado}" eliminada correctamente.')

        return JsonResponse({
            "success": True,
            "message": "Eliminado con éxito"
        })

    return JsonResponse({"success": False, "message": "Método no permitido."}, status=405)


@login_required
def categoria_detalle(request, slug):
    """
    Muestra el detalle de una categoría y lista sus productos asociados.
    También muestra estadísticas específicas de esa categoría.
    """
    # Buscamos la categoría por su slug
    categoria = get_object_or_404(Categoria, slug=slug)

    # Filtramos los productos que pertenecen a esta categoría
    productos = categoria.productos.filter(activo=True  )

    todas_las_categorias = Categoria.objects.all()

    # Reutilizamos tus cálculos estadísticos pero solo para esta categoría
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


@login_required
def obtener_categoria_json(request, pk):
    """
    API JSON: Devuelve datos de una categoría para usar en modales de edición.
    """
    categoria = get_object_or_404(Categoria, pk=pk)
    data = {
        "id": categoria.id,
        "nombre": categoria.nombre,
        "descripcion": categoria.descripcion or "",
        "imagen": categoria.imagen.url if categoria.imagen else None,
    }
    return JsonResponse(data)