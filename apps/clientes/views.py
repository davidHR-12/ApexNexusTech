from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

# Importación de Modelos
from apps.materiales.models import Material
from apps.pedidos.models import SolicitudCotizacion, Pedido, ItemPedido
from apps.productos.models import Producto, VarianteProducto
from apps.clientes.models import PerfilCliente
from apps.usuarios.models import Usuario


# Importación de Formularios
from .forms import SolicitudCotizacionForm, GuestCheckoutForm,PerfilClienteForm

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
    producto = get_object_or_404(Producto, pk=pk, mostrar_en_web=True)
    # Solo variantes activas
    variantes = producto.variantes.filter(activa=True).prefetch_related('detalles_material__material')
    
    # Si no hay variantes activas, podrías querer manejar ese error o mostrar un mensaje
    variante_default = variantes.filter(es_default=True).first() or variantes.first()
    
    return render(request, "detalle_producto.html", {
        "producto": producto,
        "galeria": producto.imagenes.all(),
        "variantes": variantes,
        "variante_default": variante_default
    })

# ==========================================
#  ÁREA PRIVADA (CLIENTE)
# ==========================================

@login_required
def mis_pedidos(request):
    # Filtramos pedidos por el usuario actual, ordenando por fecha más reciente
    pedidos = Pedido.objects.filter(usuario=request.user).order_by('-fecha_creacion')
    
    return render(request, 'clientes/mis_pedidos.html', {
        'pedidos': pedidos
    })
    
@login_required
def detalle_pedido_cliente(request, pedido_id):
    # Obtenemos el pedido asegurando que pertenezca al cliente logueado
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    
    # Obtenemos solo las notas marcadas como públicas
    # Usamos el related_name 'anotaciones' que definimos en el modelo NotaPedido
    notas_publicas = pedido.anotaciones.filter(visible_para_cliente=True).order_by('-fecha_creacion')
    
    # Obtenemos los ítems
    items = pedido.items.all() 
    
    return render(request, 'clientes/detalle_pedido.html', {
        'pedido': pedido,
        'items': items,
        'notas': notas_publicas  # Enviamos las notas filtradas
    })

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
        "pedidos": mis_pedidos[:3],
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
        precio_total=0,       
        peso_estimado_g=0,    
        tiempo_estimado_h=0,  
        costo_material=0,
        costo_energia=0,
        otros_costos=0
    )
    
    # 2. Crear el Ítem
    # Al guardar el ítem, el método save() en ItemPedido dispara actualizar_totales() en el Pedido
    ItemPedido.objects.create(
        pedido=pedido,
        variante=variante,
        cantidad=1, 
        precio_unitario=variante.precio_final,
        descripcion = f"{variante}"
    )
    
    messages.success(request, f"¡Pedido #{pedido.id} creado! Por favor gestiona el pago.")
    
    # Redirigir al detalle del pedido (o al dashboard si no no hay vista pública de detalle)
    return redirect('clientes:home')
# ==========================================
#  HELPERS (Lógica Modularizada)
# ==========================================

def _procesar_pedido_desde_carrito(usuario, carrito):
    """Toma el carrito de la sesión y crea el objeto Pedido e Items en la DB."""
    with transaction.atomic():
        # Inicializamos con 0 los campos que son obligatorios en el modelo Pedido
        nuevo_pedido = Pedido.objects.create(
            usuario=usuario,
            estado_pedido='En_Espera',
            descripcion="Pedido Web: Varios productos del catálogo",
            peso_estimado_g=0,      # <--- Obligatorio
            tiempo_estimado_h=0,    # <--- Obligatorio
            precio_total=0          # <--- Obligatorio
        )

        for variante_id, item_data in carrito.items():
            variante = get_object_or_404(VarianteProducto, id=int(variante_id))
            
            # Al crear el ItemPedido, el método save() del modelo 
            # ItemPedido llamará automáticamente a nuevo_pedido.actualizar_totales()
            ItemPedido.objects.create(
                pedido=nuevo_pedido,
                variante=variante,
                cantidad=item_data['cantidad'],
                precio_unitario=variante.precio_final,
                gramos_por_unidad=variante.peso_total or 0
            )
            
        return nuevo_pedido

# ==========================================
#  VISTAS ACTUALIZADAS
# ==========================================
@transaction.atomic
def checkout_paso_final(request):
    """
    Procesa el pedido final. 
    Soporta clientes autenticados y compras como invitado real.
    """
    carrito = request.session.get('carrito', {})
    if not carrito:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect('clientes:productos')

    if request.method == 'POST':
        if not request.user.is_authenticated:
            form = GuestCheckoutForm(request.POST)
            if not form.is_valid():
                return render(request, 'clientes/checkout_invitado.html', {
                    'form': form, 
                    'carrito': carrito
                })
            
            # Datos para pedido de invitado
            datos_cliente = {
                'usuario': None,
                'guest_nombre': f"{form.cleaned_data['nombre']} {form.cleaned_data['apellido']}",
                'guest_email': form.cleaned_data['email'],
                'guest_telefono': form.cleaned_data['telefono'],
                'guest_direccion': form.cleaned_data['direccion'],
                'guest_ciudad': form.cleaned_data['ciudad'],
                'descripcion': f"Pedido invitado: {form.cleaned_data['nombre']}"
            }
        else:
            # Datos para usuario logueado
            datos_cliente = {
                'usuario': request.user,
                'descripcion': f"Pedido de {request.user.get_full_name() or request.user.username}"
            }

        try:
            # 1. Crear el Pedido
            nuevo_pedido = Pedido.objects.create(**datos_cliente)

            # 2. Crear los ítems
            for v_id, item_data in carrito.items():
                variante = get_object_or_404(VarianteProducto, id=v_id)
                ItemPedido.objects.create(
                    pedido=nuevo_pedido,
                    variante=variante,
                    cantidad=item_data['cantidad'],
                    precio_unitario=variante.precio_final,
                    gramos_por_unidad=variante.peso_total or 0
                )

            # 3. Limpiar sesión y redirigir
            request.session['carrito'] = {}
            request.session['ultimo_pedido_id'] = nuevo_pedido.id
            
            messages.success(request, "¡Pedido realizado con éxito!")
            # Esta redirección ahora funcionará porque el name en urls.py es correcto
            return redirect('clientes:pedido_confirmado_invitado')

        except Exception as e:
            # Si algo falla aquí, redirige al checkout para intentar de nuevo
            messages.error(request, f"Hubo un error al procesar tu pedido: {str(e)}")
            return redirect('clientes:checkout_express')

    form = GuestCheckoutForm() if not request.user.is_authenticated else None
    return render(request, 'clientes/checkout_invitado.html', {'form': form, 'carrito': carrito})

def pedido_confirmado_invitado(request):
    """Vista de éxito que muestra los detalles del pedido recién creado."""
    pedido_id = request.session.get('ultimo_pedido_id')
    pedido = None
    if pedido_id:
        pedido = Pedido.objects.filter(id=pedido_id).first()
        
    return render(request, 'clientes/confirmacion_guest.html', {'pedido': pedido})

def _procesar_pedido_guest(data, carrito):
    """Crea el pedido sin asociar ningún usuario. Limpio."""
    with transaction.atomic():
        nuevo_pedido = Pedido.objects.create(
            usuario=None,  # Sin cuenta
            guest_nombre=f"{data['nombre']} {data['apellido']}",
            guest_email=data['email'],
            guest_telefono=data['telefono'],
            guest_direccion=data['direccion'],
            guest_ciudad=data['ciudad'],
            estado_pedido='En_Espera',
            descripcion="Pedido Web (Invitado): Varios productos del catálogo",
            peso_estimado_g=0,
            tiempo_estimado_h=0,
            precio_total=0,
        )

        for variante_id, item_data in carrito.items():
            variante = get_object_or_404(VarianteProducto, id=int(variante_id))
            ItemPedido.objects.create(
                pedido=nuevo_pedido,
                variante=variante,
                cantidad=item_data['cantidad'],
                precio_unitario=variante.precio_final,
                gramos_por_unidad=variante.peso_total or 0,
                descripcion=f"{variante}",
            )

        return nuevo_pedido


def confirmacion_guest(request):
    """Página de confirmación para pedidos sin cuenta."""
    pedido_id = request.session.get('ultimo_pedido_guest')
    pedido = None
    if pedido_id:
        pedido = Pedido.objects.filter(id=pedido_id, usuario=None).first()
    
    return render(request, 'clientes/confirmacion_guest.html', {'pedido': pedido})



def agregar_al_carrito(request, variante_id):
    """Soporta cantidad personalizada vía parámetro GET."""
    carrito = request.session.get('carrito', {})
    variante = get_object_or_404(VarianteProducto, id=variante_id)
    
    # Capturar cantidad del GET (por defecto 1 si no viene nada)
    try:
        cantidad = int(request.GET.get('cantidad', 1))
    except ValueError:
        cantidad = 1

    v_id_str = str(variante_id)
    
    if v_id_str in carrito:
        carrito[v_id_str]['cantidad'] += cantidad
    else:
        carrito[v_id_str] = {
            'nombre': variante.producto.nombre,
            'precio': float(variante.precio_final),
            'cantidad': cantidad,
            'imagen': variante.producto.imagen.url if variante.producto.imagen else ''
        }
    
    request.session['carrito'] = carrito
    messages.success(request, f"Se han añadido {cantidad} unidad(es) de {variante.producto.nombre}.")
    return redirect(request.META.get('HTTP_REFERER', 'clientes:productos'))

def actualizar_carrito(request, variante_id, accion):
    """
    Acciones: 'sumar', 'restar', 'eliminar'
    """
    carrito = request.session.get('carrito', {})
    v_id_str = str(variante_id)

    if v_id_str in carrito:
        if accion == 'sumar':
            carrito[v_id_str]['cantidad'] += 1
        elif accion == 'restar':
            carrito[v_id_str]['cantidad'] -= 1
            if carrito[v_id_str]['cantidad'] <= 0:
                del carrito[v_id_str]
        elif accion == 'eliminar':
            del carrito[v_id_str]
        
        request.session['carrito'] = carrito
        request.session.modified = True
        
    return redirect(request.META.get('HTTP_REFERER', 'clientes:productos'))