from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.materiales.models import Material
from apps.pedidos.models import SolicitudCotizacion, Pedido
from apps.productos.models import Producto


def index(request):
    """
    Vista principal pública (landing page).
    """
    # Contamos datos reales de la base de datos
    total_materiales = Material.objects.count()
    # Contamos pedidos con estado 'Entregado' (asumiendo que tienes ese estado)
    piezas_reales = Pedido.objects.filter(estado_pedido="Entregado").count()

    # Si piezas_reales es bajo, sumamos un número base "de cortesía"
    # por tus trabajos previos fuera del sistema
    piezas_mostrar = 50 + piezas_reales
    materiales = Material.objects.all()
    productos = Producto.objects.all()
    context = {
        "n_materiales": total_materiales,
        "n_piezas": piezas_mostrar,
        "materiales": materiales,
        "productos": productos,
    }
    return render(request, "clientes/index.html", context)


@login_required
def home(request):
    """
    Panel principal del cliente (Dashboard).
    Muestra sus pedidos y estado.
    """
    return render(request, "clientes/home.html", {"pedidos": []})


def guia_materiales(request):
    # Traemos los materiales para que sepa cuáles tienes en stock actualmente
    materiales_disponibles = Material.objects.all()
    return render(
        request, "clientes/materiales.html", {
            "materiales": materiales_disponibles}
    )


def proceso(request):
    """
    Vista del proceso de fabricación.
    """
    return render(request, "clientes/proceso.html")


def productos(request):
    """
    Vista del catálogo de productos.
    """
    productos = Producto.objects.filter(mostrar_en_web=True)
    context = {
        "productos": productos,
    }
    return render(request, "clientes/productos.html", context)


def detalle_producto(request, pk):
    # Buscamos el producto o lanzamos error 404 si no existe
    producto = get_object_or_404(Producto, pk=pk, mostrar_en_web=True)

    # Obtenemos las imágenes de la galería (las que subiste en el Inline)
    # Gracias al related_name='imagenes' en el modelo
    galeria = producto.imagenes.all()

    return render(
        request,
        "clientes/detalle_producto.html",
        {"producto": producto, "galeria": galeria},
    )
