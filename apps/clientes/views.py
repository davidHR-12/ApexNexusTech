from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

# Importación de Modelos
from apps.materiales.models import Material
from apps.pedidos.models import SolicitudCotizacion, Pedido, ItemPedido
from apps.productos.models import Producto, VarianteProducto
from apps.clientes.models import PerfilCliente

# Importación de Formularios
from .forms import SolicitudCotizacionForm, PerfilClienteForm # Asegúrate de importar el Perfil

# ==========================================
#  VISTAS PÚBLICAS
# ==========================================

def index(request):
    """Vista principal pública (landing page)."""
    total_materiales = Material.objects.count()
    piezas_reales = Pedido.objects.filter(estado_pedido="Entregado").count()
    piezas_mostrar = 50 + piezas_reales

    materiales = Material.objects.all()
    productos = Producto.objects.all()[:6] # Mostramos solo los primeros 6 productos destacados

    context = {
        "n_materiales": total_materiales,
        "n_piezas": piezas_mostrar,
        "materiales": materiales,
        "productos": productos,
    }
    return render(request, "index.html", context)

def guia_materiales(request):
    """Catálogo de materiales disponibles"""
    materiales_disponibles = Material.objects.filter(stock_actual__gt=0) # Solo lo que tiene stock
    return render(request, "materiales.html", {"materiales": materiales_disponibles})

def proceso(request):
    """Vista estática del proceso"""
    return render(request, "proceso.html")

def productos(request):
    """Catálogo completo de productos"""
    productos = Producto.objects.filter(mostrar_en_web=True)
    return render(request, "productos.html", {"productos": productos})

def detalle_producto(request, pk):
    """Detalle de producto para compra"""
    producto = get_object_or_404(Producto, pk=pk, mostrar_en_web=True)
    galeria = producto.imagenes.all()
    # IMPORTANTE: Enviamos las variantes para que el cliente elija color/tamaño
    variantes = producto.variantes.filter(activo=True)

    return render(request, "detalle_producto.html", {
        "producto": producto, 
        "galeria": galeria,
        "variantes": variantes
    })

# ==========================================
#  ÁREA PRIVADA (CLIENTE)
# ==========================================

@login_required
def home(request):
    """
    Dashboard del cliente. Muestra sus pedidos y cotizaciones.
    """
    # 1. Obtenemos pedidos activos e históricos
    mis_pedidos = Pedido.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    print(f"DEBUG: Solicitudes en DB: {SolicitudCotizacion.objects.count()}")
    
    # 2. Obtenemos sus solicitudes de cotización
    mis_cotizaciones = SolicitudCotizacion.objects.filter(usuario=request.user).order_by('-fecha_solicitud')

    context = {
        "pedidos": mis_pedidos,
        "cotizaciones": mis_cotizaciones
    }
    return render(request, "clientes/home.html", context)

@login_required
def mi_perfil(request):
    """Vista para que el cliente actualice sus datos de envío/contacto"""
    perfil, created = PerfilCliente.objects.get_or_create(usuario=request.user)
    
    if request.method == 'POST':
        form = PerfilClienteForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos actualizados correctamente.")
            return redirect('clientes:home')
    else:
        form = PerfilClienteForm(instance=perfil)
    
    return render(request, "clientes/perfil.html", {"form": form})

@login_required
def solicitar_cotizacion(request):
    """Procesa la subida de archivos personalizados"""
    if request.method == 'POST':
        form = SolicitudCotizacionForm(request.POST, request.FILES)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = request.user
            solicitud.estado = 'Pendiente'
            solicitud.save()
            messages.success(request, "Solicitud enviada. Te avisaremos cuando tengamos tu presupuesto.")
            return redirect('clientes:home')
    else:
        form = SolicitudCotizacionForm()
    
    return render(request, 'clientes/solicitar.html', {'form': form})

@login_required
def crear_pedido_catalogo(request, variante_id):
    """
    Crea un pedido automáticamente al pulsar 'Comprar' en una variante.
    """
    variante = get_object_or_404(VarianteProducto, id=variante_id)
    
    # 1. Crear el Pedido Base (Con valores en 0 para evitar errores de Not Null)
    pedido = Pedido.objects.create(
        usuario=request.user,
        estado_pedido='En_Espera',
        descripcion=f"Pedido Web: {variante.producto.nombre}",
        precio_total=0,       # Se actualizará solo
        peso_estimado_g=0,    # Se actualizará solo
        tiempo_estimado_h=0,  # Se actualizará solo
        costo_material=0,
        costo_energia=0,
        otros_costos=0
    )
    
    # 2. Crear el Ítem
    # Al guardar el ítem, tu método save() en ItemPedido dispara actualizar_totales() en el Pedido
    ItemPedido.objects.create(
        pedido=pedido,
        variante=variante,
        cantidad=1, 
        precio_unitario=variante.precio_final,
        descripcion=f"{variante.producto.nombre} - {variante.nombre}"
    )
    
    messages.success(request, f"¡Pedido #{pedido.id} creado! Por favor gestiona el pago.")
    
    # Redirigir al detalle del pedido (o al dashboard si no tienes vista pública de detalle)
    return redirect('clientes:home')