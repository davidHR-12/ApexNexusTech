from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, F
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from django.utils.text import slugify

from .models import Categoria, Producto, VarianteProducto, ImagenProducto
from apps.materiales.models import Material
from apps.materiales.forms import MaterialForm
from .forms import CategoriaForm, ProductoForm, ProduccionInternaForm


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
    # Esto es un ejemplo, ajusta según tu lógica de valor
    valor_inventario = (
        Producto.objects.aggregate(
            total=Sum(
                F("precio_venta")
            )  # Aquí podrías multiplicar por stock si prefieres
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
def crear_producto(request):
    """
    Procesa el formulario para crear un nuevo producto.
    Maneja limpieza de formatos numéricos (comas y decimales).
    """
    if request.method == "POST":
        data = request.POST.copy()

        # Limpieza de decimales segura
        try:
            data["precio_venta"] = abs(
                Decimal(data.get("precio_venta", "0").replace(",", "") or "0")
            )
            data["peso_gramos"] = abs(
                Decimal(data.get("peso_gramos", "0").replace(",", "") or "0")
            )
        except (InvalidOperation, ValueError):
            messages.error(request, "Formatos numéricos incorrectos.")
            return redirect(request.META.get("HTTP_REFERER", "productos:lista_productos"))

        form = ProductoForm(data, request.FILES)

        if form.is_valid():
            producto = form.save()

            # Guardar galería adicional
            imagenes_extras = request.FILES.getlist("imagenes_galeria")
            for f in imagenes_extras:
                ImagenProducto.objects.create(producto=producto, imagen=f)

            messages.success(request, f"Producto '{producto.nombre}' creado.")

            next_url = request.POST.get("next", "")
            if next_url:
                return redirect(next_url)
            else:
                # Redirigir a los detalles del producto
                return redirect("productos:producto_detalle", slug=producto.slug)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")

    return redirect("productos:lista_productos")


@login_required
def producto_detalle(request, slug):
    """
    Muestra el detalle completo de un producto.
    Incluye variantes, galería, stock y opciones de edición.
    """
    producto = get_object_or_404(Producto, slug=slug)
    # Obtenemos las variantes relacionadas para mostrarlas en el inventario
    variantes = producto.variantes.all()

    context = {
        "producto": producto,
        "variantes": variantes,
    }
    return render(request, "productos/producto_detalle.html", context)


@login_required
def editar_producto(request, producto_id):
    """
    Edita un producto existente.
    Permite eliminar la imagen de portada y gestionar la galería.
    """
    producto = get_object_or_404(Producto, id=producto_id)

    if request.method == "POST":
        data = request.POST.copy()

        # --- LÓGICA PARA BORRAR PORTADA ---
        # Si el flag es 'true', borramos la imagen antes de procesar el form
        if request.POST.get("eliminar_portada_flag") == "true":
            if producto.imagen:
                producto.imagen.delete(save=False)  # Borra el archivo físico
                producto.imagen = None  # Limpia el campo en DB
        # ----------------------------------

        # Limpieza de datos numéricos
        try:
            data["precio_venta"] = abs(
                Decimal(data.get("precio_venta", "0").replace(",", ""))
            )
            data["peso_gramos"] = abs(
                Decimal(data.get("peso_gramos", "0").replace(",", ""))
            )
        except (InvalidOperation, ValueError):
            messages.error(request, "Formatos numéricos incorrectos.")
            return redirect(request.META.get("HTTP_REFERER", "productos:lista_productos"))

        form = ProductoForm(data, request.FILES, instance=producto)

        if form.is_valid():
            # Si el nombre cambió, forzamos la actualización del slug
            producto_editado = form.save(commit=False)
            # Si el flag estaba activo, aseguramos que se guarde como None
            if request.POST.get("eliminar_portada_flag") == "true":
                producto_editado.imagen = None
            producto_editado.slug = slugify(producto_editado.nombre)
            producto_editado.save()

            # Guardar nuevas imágenes de la galería
            nuevas_imagenes = request.FILES.getlist("imagenes_galeria")
            for f in nuevas_imagenes:
                ImagenProducto.objects.create(producto=producto_editado, imagen=f)

            messages.success(
                request, f"'{producto_editado.nombre}' actualizado correctamente."
            )

            # Redirección inteligente
            next_url = request.POST.get("next")
            if next_url:
                # Si el slug cambió, intentamos actualizar el slug en la URL de 'next'
                # para evitar errores 404 si el usuario estaba viendo el detalle del producto
                return redirect(next_url)

            return redirect(
                "productos:categoria_detalle", slug=producto_editado.categoria.slug
            )
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")

    return redirect("productos:lista_productos")


@login_required
def eliminar_imagen_producto(request, imagen_id):
    """
    API: Elimina una imagen específica de la galería de un producto.
    Borra tanto de BDD como del sistema de archivos.
    """
    if request.method == "POST":
        imagen = get_object_or_404(ImagenProducto, id=imagen_id)
        try:
            # Borrar el archivo físico
            if imagen.imagen:
                imagen.imagen.delete(save=False)
            # Borrar el registro
            imagen.delete()
            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return JsonResponse({"status": "error"}, status=400)


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
def crear_variante_json(request):
    """
    API JSON: Asocia un material a un producto (crea una variante).
    """
    if request.method == "POST":
        import json

        data = json.loads(request.body)
        producto_id = data.get("producto_id")
        material_id = data.get("material_id")

        producto = get_object_or_404(Producto, id=producto_id)
        material = get_object_or_404(Material, id=material_id)

        # Esto crea la conexión en la base de datos
        variante, creada = VarianteProducto.objects.get_or_create(
            producto=producto, material=material
        )

        return JsonResponse({"success": True, "id": variante.id})
    return JsonResponse({"success": False}, status=400)


@login_required
def eliminar_variante_json(request, variante_id):
    """
    API JSON: Elimina una variante de producto.
    """
    if request.method == "POST":
        try:
            variante = VarianteProducto.objects.get(id=variante_id)
            variante.delete()
            return JsonResponse({"success": True})
        except VarianteProducto.DoesNotExist:
            return JsonResponse({"success": False, "error": "Variante no encontrada"})
    return JsonResponse({"success": False}, status=400)
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

    return redirect("productos:lista_productos")


@login_required
def editar_categoria(request, categoria_id):
    """
    Edita una categoría existente.
    Permite cambiar nombre, descripción e imagen. Re-slugifica si cambia el nombre.
    """
    categoria = get_object_or_404(Categoria, pk=categoria_id)

    if request.method == "POST":
        form = CategoriaForm(request.POST, request.FILES, instance=categoria)
        eliminar_imagen = request.POST.get("eliminar_imagen") == "true"

        if form.is_valid():
            obj = form.save(commit=False)

            # --- ACTUALIZACIÓN DE SLUG ---
            # Forzamos la regeneración del slug basado en el nuevo nombre
            obj.slug = slugify(obj.nombre)

            # --- LÓGICA DE IMAGEN ---
            if eliminar_imagen and not request.FILES.get("imagen"):
                if obj.imagen:
                    obj.imagen.delete(save=False)
                obj.imagen = None

            obj.save()
            messages.success(request, f'Categoría "{obj.nombre}" actualizada.')

            # --- REDIRECCIÓN INTELIGENTE ---
            # Si venimos de una página que usaba el slug viejo, redirigimos al nuevo
            # para evitar errores 404 al recargar.
        else:
            for error in form.errors.values():
                messages.error(request, error)

    return redirect("productos:lista_productos")

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
    productos = categoria.productos.all()

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