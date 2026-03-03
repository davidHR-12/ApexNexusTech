from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

# Importación de Modelos
from apps.materiales.models import Material
from apps.pedidos.models import SolicitudCotizacion, Pedido, ItemPedido, ConfiguracionPago, Pago
from apps.productos.models import Producto, VarianteProducto
from apps.clientes.models import PerfilCliente
from apps.usuarios.models import Usuario
from apps.core.models import CardPublica
from apps.usuarios.decorators import cliente_required


# Importación de Formularios
from .forms import SolicitudCotizacionForm, GuestCheckoutForm,PerfilClienteForm

# ==========================================
#  VISTAS PÚBLICAS
# ==========================================

def index(request):
    from apps.productos.models import Producto
    from apps.core.models import ConfiguracionSitio, CardPublica

    config = ConfiguracionSitio.obtener()
    cards_materiales = CardPublica.objects.filter(
        seccion='materiales',
        activo=True
    ).order_by('orden')

    productos_destacados = []
    if config.mostrar_seccion_productos_destacados:
        productos_destacados = Producto.objects.filter(
            activo=True,
            mostrar_en_web=True
        )[:config.max_productos_destacados]

    return render(request, 'publico/index.html', {
        'productos_destacados': productos_destacados,
        'cards_materiales': cards_materiales,
    })

def materiales_view(request):
    from apps.materiales.models import Material
    from apps.core.models import CardPublica

    materiales = Material.objects.select_related('marca', 'tipo', 'color').order_by('tipo__nombre')
    cards_materiales = CardPublica.objects.filter(
        seccion='materiales',
        activo=True
    ).order_by('orden')

    return render(request, 'publico/materiales.html', {
        'materiales': materiales,
        'cards_materiales': cards_materiales,
    })

def proceso_view(request):
    from apps.core.models import ConfiguracionSitio

    config = ConfiguracionSitio.obtener()
    cards_proceso    = CardPublica.objects.filter(seccion='proceso', activo=True).order_by('orden')
    return render(request, 'publico/proceso.html', {'config': config, 'cards_proceso': cards_proceso})

def productos(request):
    """Catálogo completo de productos"""
    productos = Producto.objects.filter(mostrar_en_web=True)
    return render(request, "publico/productos.html", {"productos": productos})

def detalle_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk, mostrar_en_web=True)
    # Solo variantes activas
    variantes = producto.variantes.filter(activa=True).prefetch_related('detalles_material__material')
    
    # Si no hay variantes activas, podrías querer manejar ese error o mostrar un mensaje
    variante_default = variantes.filter(es_default=True).first() or variantes.first()
    
    return render(request, "publico/detalle_producto.html", {
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
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

    # Notas públicas
    notas_publicas = pedido.anotaciones.filter(
        visible_para_cliente=True
    ).order_by('-fecha_creacion')

    # Ítems
    items = pedido.items.all()

    # Configuración de datos bancarios del negocio
    from apps.pedidos.models import ConfiguracionPago
    config_pago = ConfiguracionPago.obtener()

    # Tipo de pedido
    es_pedido_cotizacion = pedido.solicitud is not None
    tiene_items_catalogo = pedido.items.filter(variante__isnull=False).exists()
    tiene_items_personalizados = pedido.items.filter(variante__isnull=True).exists()

    # Determinar si ya tiene comprobante o pago registrado
    pago_existente = pedido.pagos.order_by('-fecha_pago').first()

    # Anticipo calculado (para pedidos personalizados cotizados)
    anticipo = None
    if config_pago and es_pedido_cotizacion and pedido.precio_total > 0:
        from decimal import Decimal
        pct = config_pago.porcentaje_anticipo / Decimal('100')
        anticipo = (pedido.precio_total * pct).quantize(Decimal('0.01'))

    # Estados en los que el cliente puede interactuar con el pago
    estados_pago_activos = ['En_Espera', 'Confirmado']
    puede_seleccionar_pago = (
        pedido.estado_pedido in estados_pago_activos
        and pedido.precio_total > 0
    )

    return render(request, 'clientes/detalle_pedido.html', {
        'pedido': pedido,
        'items': items,
        'notas': notas_publicas,
        'config_pago': config_pago,
        'pago_existente': pago_existente,
        'es_pedido_cotizacion': es_pedido_cotizacion,
        'tiene_items_catalogo': tiene_items_catalogo,
        'tiene_items_personalizados': tiene_items_personalizados,
        'anticipo': anticipo,
        'puede_seleccionar_pago': puede_seleccionar_pago,
    })


@login_required
def seleccionar_metodo_pago(request, pedido_id):
    """El cliente elige su método de pago preferido."""
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

    if request.method != 'POST':
        return redirect('clientes:detalle_pedido', pedido_id=pedido_id)

    metodo = request.POST.get('metodo_pago', '')
    metodos_validos = ['Efectivo', 'Transferencia', 'Contraentrega']

    if metodo not in metodos_validos:
        messages.error(request, "Método de pago no válido.")
        return redirect('clientes:detalle_pedido', pedido_id=pedido_id)

    estados_permitidos = ['En_Espera', 'Confirmado']
    if pedido.estado_pedido not in estados_permitidos:
        messages.error(request, "No es posible modificar el método de pago en este momento.")
        return redirect('clientes:detalle_pedido', pedido_id=pedido_id)

    pedido.metodo_pago_preferido = metodo
    # Limpiamos el comprobante anterior si cambia de método
    if metodo != 'Transferencia':
        pedido.comprobante_cliente = None
        pedido.comprobante_estado = ''
    pedido.save(update_fields=['metodo_pago_preferido', 'comprobante_cliente', 'comprobante_estado'])

    labels = {
        'Efectivo': 'Efectivo en mano',
        'Transferencia': 'Transferencia bancaria',
        'Contraentrega': 'Pago contraentrega',
    }
    messages.success(request, f"Método de pago seleccionado: {labels[metodo]}.")
    return redirect('clientes:detalle_pedido', pedido_id=pedido_id)


@login_required
def subir_comprobante(request, pedido_id):
    """El cliente sube la captura de su transferencia."""
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)

    if request.method != 'POST':
        return redirect('clientes:detalle_pedido', pedido_id=pedido_id)

    comprobante = request.FILES.get('comprobante')
    if not comprobante:
        messages.error(request, "Debes seleccionar una imagen como comprobante.")
        return redirect('clientes:detalle_pedido', pedido_id=pedido_id)

    # Validar tipo de archivo
    tipos_permitidos = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
    if comprobante.content_type not in tipos_permitidos:
        messages.error(request, "Solo se aceptan imágenes (JPG, PNG, WEBP).")
        return redirect('clientes:detalle_pedido', pedido_id=pedido_id)

    # Guardar en el campo del pedido
    pedido.comprobante_cliente = comprobante
    pedido.comprobante_estado = 'Pendiente'
    pedido.save(update_fields=['comprobante_cliente', 'comprobante_estado'])

    messages.success(
        request,
        "Comprobante enviado correctamente. Lo revisaremos y confirmaremos tu pedido en breve."
    )
    return redirect('clientes:detalle_pedido', pedido_id=pedido_id)




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
def configuracion_cliente(request):
    """
    Página de configuración del cliente.
    Edita datos del Usuario (nombre, apellido, teléfono)
    y del PerfilCliente (dirección, ciudad, empresa, etc.)
    """
    perfil, _ = PerfilCliente.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        usuario = request.user

        # ── Actualizar campos del Usuario ──
        usuario.first_name = request.POST.get('first_name', '').strip()
        usuario.last_name  = request.POST.get('last_name', '').strip()
        usuario.telefono   = request.POST.get('telefono', '').strip()
        usuario.save(update_fields=['first_name', 'last_name', 'telefono'])

        # ── Actualizar campos del Perfil ──
        perfil.direccion              = request.POST.get('direccion', '').strip()
        perfil.ciudad                 = request.POST.get('ciudad', '').strip()
        perfil.codigo_postal          = request.POST.get('codigo_postal', '').strip()
        perfil.empresa                = request.POST.get('empresa', '').strip()
        perfil.recibir_notificaciones = 'recibir_notificaciones' in request.POST
        perfil.save()

        messages.success(request, "Datos actualizados correctamente.")
        return redirect('clientes:configuracion')

    return render(request, 'clientes/config_cliente.html', {
        'perfil': perfil,
    })


@login_required
def solicitar_cotizacion(request):
    """Procesa la subida de archivos personalizados con validación de mensajes"""
    if request.method == 'POST':
        form = SolicitudCotizacionForm(request.POST, request.FILES)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = request.user
            solicitud.estado = 'Pendiente'
            solicitud.save()
            messages.success(request, "¡Recibido! Revisaremos tu solicitud y te avisaremos pronto.")
            return redirect('clientes:home')
        else:
            # Si hay errores, los enviamos uno a uno al SweetAlert
            for field, errors in form.errors.items():
                for error in errors:
                    # Obtenemos el nombre legible del campo (label)
                    label = form.fields[field].label if field in form.fields else "Formulario"
                    messages.error(request, f"{label}: {error}")
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
    Checkpoint que decide qué template mostrar:
    - Usuario autenticado  → checkout_usuario.html    (sin formulario)
    - Invitado             → checkout_invitado.html   (con formulario)
    """
    carrito = request.session.get('carrito', {})

    # ── POST: procesar pedido ──
    if request.method == 'POST':

        if request.user.is_authenticated:
            # Cliente con cuenta: usamos sus datos directamente
            datos_cliente = {
                'usuario': request.user,
                'descripcion': f"Pedido de {request.user.get_full_name() or request.user.username}",
            }
            try:
                nuevo_pedido = _crear_pedido_con_items(datos_cliente, carrito)
                request.session['carrito'] = {}
                messages.success(request, f"¡Pedido #{nuevo_pedido.id} creado con éxito!")
                return redirect('clientes:detalle_pedido', pedido_id=nuevo_pedido.id)
            except Exception as e:
                messages.error(request, f"Hubo un error al procesar tu pedido: {str(e)}")
                return redirect('clientes:checkout_express')

        else:
            # Invitado: validar formulario
            form = GuestCheckoutForm(request.POST)
            if not form.is_valid():
                return render(request, 'clientes/checkout_invitado.html', {
                    'form': form,
                    'carrito': carrito,
                })
            datos_cliente = {
                'usuario': None,
                'guest_nombre': f"{form.cleaned_data['nombre']} {form.cleaned_data['apellido']}",
                'guest_email': form.cleaned_data['email'],
                'guest_telefono': form.cleaned_data['telefono'],
                'guest_direccion': form.cleaned_data['direccion'],
                'guest_ciudad': form.cleaned_data['ciudad'],
                'descripcion': f"Pedido invitado: {form.cleaned_data['nombre']}",
            }
            try:
                nuevo_pedido = _crear_pedido_con_items(datos_cliente, carrito)
                request.session['carrito'] = {}
                request.session['ultimo_pedido_id'] = nuevo_pedido.id
                messages.success(request, "¡Pedido realizado con éxito!")
                return redirect('clientes:pedido_confirmado_invitado')
            except Exception as e:
                messages.error(request, f"Hubo un error al procesar tu pedido: {str(e)}")
                return redirect('clientes:checkout_express')

    # ── GET: mostrar el template correcto ──
    if request.user.is_authenticated:
        perfil, _ = PerfilCliente.objects.get_or_create(usuario=request.user)
        return render(request, 'clientes/checkout_usuario.html', {
            'carrito': carrito,
            'perfil': perfil,
        })
    else:
        return render(request, 'clientes/checkout_invitado.html', {
            'form': GuestCheckoutForm(),
            'carrito': carrito,
        })


def _crear_pedido_con_items(datos_cliente, carrito):
    """
    Helper unificado. Crea Pedido + Items desde el carrito de sesión.
    """
    with transaction.atomic():
        pedido = Pedido.objects.create(
            estado_pedido='En_Espera',
            peso_estimado_g=0,
            tiempo_estimado_h=0,
            precio_total=0,
            **datos_cliente,
        )
        for v_id, item_data in carrito.items():
            variante = get_object_or_404(VarianteProducto, id=v_id)
            ItemPedido.objects.create(
                pedido=pedido,
                variante=variante,
                cantidad=item_data['cantidad'],
                precio_unitario=variante.precio_final,
                gramos_por_unidad=variante.peso_total or 0,
            )
        return pedido


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