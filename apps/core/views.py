# Librerías estándar de Python
import json
import os
from decimal import Decimal, ROUND_HALF_UP

# Django: Núcleo y Utilidades
from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

# Django: Decoradores
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST

# Apps locales: Modelos y Decoradores externos
from apps.finanzas.models import Gasto
from apps.materiales.models import Material
from apps.pedidos.models import ConfiguracionPago, Pago, Pedido
from apps.productos.models import Categoria, Producto
from apps.usuarios.decorators import admin_required

# Directorio actual: Modelos y Formularios
from .forms import (
    CardPublicaForm, ConfiguracionCalculadoraForm, ContactoForm,
    EstadisticasForm, ImpresoraForm, MaterialesForm,
    ProcesoForm, ProductosDestacadosForm
)
from .models import CardPublica, ConfiguracionCalculadora, ConfiguracionSitio, Impresora

# ════════════════════════════════════════════════════════════════════
# UTILIDADES PRIVADAS (Helper Functions)
# ════════════════════════════════════════════════════════════════════

def _cambiar_estado_impresora(impresora, nuevo_estado):
    """
    Cambia el estado de una impresora de forma segura.
    
    Args:
        impresora: Instancia de Impresora
        nuevo_estado: Estado nuevo ('Disponible', 'Imprimiendo', 'Mantenimiento', 'Offline')
    
    Returns:
        tuple: (success: bool, message: str, message_type: str)
    """
    ESTADOS_VALIDOS = dict(Impresora.ESTADOS)
    
    if nuevo_estado not in ESTADOS_VALIDOS:
        return False, f"Estado inválido: {nuevo_estado}", 'error'
    
    if impresora.estado == nuevo_estado:
        return False, f"La impresora ya está en estado {nuevo_estado}", 'info'
    
    impresora.estado = nuevo_estado
    impresora.save()
    
    return True, f"Estado de {impresora.nombre} actualizado a {nuevo_estado}", 'success'


def _procesar_archivos_huerfanos():
    """
    Identifica archivos en /media que no están referenciados en la BD.
    
    Returns:
        list: Lista de archivos huérfanos con sus metadatos
    """
    mapeo_config = {
        'categorias': (Categoria, 'imagen'),
        'productos': (Producto, 'imagen'),
        'finanzas/comprobantes': (Gasto, 'comprobante'),
    }
    
    archivos_huerfanos = []
    protegidos = ['.gitkeep', 'Logo.png', 'Log.png', 'Logo-figura.ico']

    for subcarpeta, (Modelo, campo_imagen) in mapeo_config.items():
        ruta_absoluta_carpeta = os.path.join(settings.MEDIA_ROOT, subcarpeta)
        
        if not os.path.exists(ruta_absoluta_carpeta):
            continue
        
        # Obtener archivos en BD
        archivos_en_bd = Modelo.objects.exclude(**{f"{campo_imagen}": ""}).values_list(campo_imagen, flat=True)
        nombres_en_bd = {os.path.basename(str(path)) for path in archivos_en_bd}

        # Listar contenido de la carpeta
        for nombre_item in os.listdir(ruta_absoluta_carpeta):
            ruta_completa_item = os.path.join(ruta_absoluta_carpeta, nombre_item)
            
            # Solo procesar archivos, no directorios
            if not os.path.isfile(ruta_completa_item):
                continue
            
            if nombre_item not in protegidos and nombre_item not in nombres_en_bd:
                ruta_relativa = os.path.join(subcarpeta, nombre_item)
                archivos_huerfanos.append({
                    'nombre': nombre_item,
                    'ruta_relativa': ruta_relativa,
                    'url': f"{settings.MEDIA_URL}{ruta_relativa}".replace('\\', '/'),
                    'tipo': subcarpeta.split('/')[0]
                })
    
    return archivos_huerfanos


def _eliminar_archivos(rutas_relativas, protegidos):
    """
    Elimina archivos de forma segura validando rutas.
    
    Args:
        rutas_relativas: Lista de rutas relativas a eliminar
        protegidos: Lista de nombres de archivos protegidos
    
    Returns:
        int: Cantidad de archivos eliminados
    """
    count = 0
    for ruta_rel in rutas_relativas:
        # Validación de seguridad
        if '..' in ruta_rel or any(prot in ruta_rel for prot in protegidos):
            continue
        
        ruta_final = os.path.join(settings.MEDIA_ROOT, ruta_rel)
        
        if os.path.exists(ruta_final) and os.path.isfile(ruta_final):
            try:
                os.remove(ruta_final)
                count += 1
            except Exception as e:
                print(f"Error borrando {ruta_final}: {e}")
    
    return count


# ════════════════════════════════════════════════════════════════════
# VISTAS PÚBLICAS
# ════════════════════════════════════════════════════════════════════

@admin_required
def gestionar_media_huerfana(request):
    """
    Gestiona archivos huérfanos en /media.
    Identifica y permite eliminar archivos que no están en la BD.
    """
    archivos_huerfanos = _procesar_archivos_huerfanos()
    
    if request.method == "POST":
        archivos_a_borrar = request.POST.getlist('archivos')
        protegidos = ['.gitkeep', 'Logo.png', 'Log.png', 'Logo-figura.ico']
        count = _eliminar_archivos(archivos_a_borrar, protegidos)
        
        messages.success(request, f"¡Limpieza completada! Se eliminaron {count} archivos.")
        return redirect('core:config_media')

    return render(request, 'core/configuraciones/config_media.html', {
        'segment': 'configuracion',
        'archivos': archivos_huerfanos
    })


@admin_required
def dashboard_admin(request):
    """
    Dashboard principal del administrador.
    Muestra resumen de ingresos, gastos, utilidad y alertas de stock.
    """
    ahora = timezone.now()
    
    # Calcular métricas del mes
    ingresos_mes = Pago.objects.filter(
        fecha_pago__month=ahora.month, 
        fecha_pago__year=ahora.year
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    gastos_mes = Gasto.objects.filter(
        fecha__month=ahora.month, 
        fecha__year=ahora.year
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    # Información de materiales
    materiales = Material.objects.all()
    total_gramos = materiales.aggregate(Sum("stock_actual"))["stock_actual__sum"] or 0
    
    # Alertas de stock
    alertas_stock = [m for m in materiales if m.stock_actual <= m.stock_minimo]
    materiales_ok = [m for m in materiales if m.stock_actual > m.stock_minimo]

    context = {
        "ingresos_mes": ingresos_mes,
        "gastos_mes": gastos_mes,
        "utilidad_neta": ingresos_mes - gastos_mes,
        "pedidos_activos": Pedido.objects.exclude(
            estado_pedido__in=["Entregado", "Cancelado"]
        ).count(),
        "total_kg": total_gramos / 1000,
        "materiales": materiales,
        "alertas_stock": alertas_stock[:5],
        "materiales_ok": materiales_ok[:5],
    }
    return render(request, "core/dashboard_admin.html", context)

@admin_required
def calculadora(request):
    """
    Muestra la calculadora. Los valores predeterminados vienen de
    ConfiguracionCalculadora y pre-rellenan los inputs de gastos fijos.
    No guarda ningún cálculo en BD.
    """
    config = ConfiguracionCalculadora.obtener()
    return render(request, 'core/calculadora.html', {'config': config})


@csrf_exempt
@require_http_methods(["POST"])
def calcular_ajax(request):
    """
    Recibe JSON con todos los valores del formulario,
    calcula y devuelve resultados. Nunca toca la BD.
    """
    try:
        data = json.loads(request.body)

        def d(key, default=0):
            return Decimal(str(data.get(key, default) or 0))

        precio_kg= d('precio_kg')
        precio_kwh= d('precio_kwh')
        consumo_watts= d('consumo_watts')
        vida_util_horas= d('vida_util_horas')
        precio_repuestos= d('precio_repuestos')
        margen_error_pct= d('margen_error_porcentaje')
        tiempo_horas= d('tiempo_horas')
        tiempo_minutos= d('tiempo_minutos')
        gramos= d('gramos')
        insumos= d('insumos')
        multiplicador= d('multiplicador', 4)

        # Tiempo total en horas
        tiempo_total = tiempo_horas + (tiempo_minutos / Decimal('60'))

        # Cálculos
        precio_material= (gramos * precio_kg) / Decimal('1000')
        precio_luz= (consumo_watts * precio_kwh / Decimal('1000')) * tiempo_total
        desgaste= (tiempo_total * precio_repuestos / vida_util_horas) if vida_util_horas > 0 else Decimal('0')
        base= precio_material + precio_luz
        margen_error= base * (margen_error_pct / Decimal('100'))
        costo_total= base + desgaste + margen_error + insumos
        total_cobrar= costo_total * multiplicador

        def fmt(val):
            return float(val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        return JsonResponse({
            'success': True,
            'precio_material': fmt(precio_material),
            'precio_luz': fmt(precio_luz),
            'desgaste_maquina': fmt(desgaste),
            'margen_error': fmt(margen_error),
            'insumos': fmt(insumos),
            'costo_total': fmt(costo_total),
            'total_cobrar': fmt(total_cobrar),
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@admin_required
def configurar_calculadora(request):
    """
    Permite al admin editar los valores predeterminados de la calculadora.
    """
    config = ConfiguracionCalculadora.obtener()

    if request.method == 'POST':
        form = ConfiguracionCalculadoraForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración de la calculadora guardada.")
            return redirect('core:configurar_calculadora')
    else:
        form = ConfiguracionCalculadoraForm(instance=config)

    return render(request, 'core/configuraciones/config_calculadora.html', {'form': form})

@admin_required
def configurar_factura(request):
    from apps.core.models import ConfiguracionFactura
    from apps.core.forms import ConfiguracionFacturaForm

    config = ConfiguracionFactura.obtener()

    if request.method == "POST":
        # ── Eliminar logo si el usuario presionó la X ──
        eliminar_logo = request.POST.get("eliminar_logo") == "true"
        if eliminar_logo and config.logo:
            config.logo.delete(save=False)
            config.logo = None
            config.save(update_fields=["logo"])

        form = ConfiguracionFacturaForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos de factura guardados correctamente.")
            return redirect("core:configurar_factura")
    else:
        form = ConfiguracionFacturaForm(instance=config)

    return render(request, "core/configuraciones/config_factura.html", {"form": form, "config": config})

@admin_required
def configuracion(request):
    """
    Página principal de configuración del sistema.
    Muestra menú de todas las opciones de configuración disponibles.
    """
    return render(request, "core/configuraciones/configuracion.html", {
        'segment': 'configuracion'
    })


@admin_required
def lista_impresoras(request):
    """
    Lista todas las impresoras 3D con sus estados.
    Actualiza automáticamente el estado de impresoras sin trabajo activo.
    """
    impresoras = Impresora.objects.all().order_by('estado', 'nombre')
    
    # Actualizar estados automáticamente
    rescatadas = sum(1 for imp in impresoras if imp.actualizar_estado_automatico())
    if rescatadas > 0:
        messages.info(request, f"Se han liberado {rescatadas} impresoras que no tenían trabajo activo.")
    
    # Estadísticas
    stats = Impresora.objects.aggregate(
        total=Count('id'),
        disponibles=Count('id', filter=Q(estado='Disponible')),
        imprimiendo=Count('id', filter=Q(estado='Imprimiendo')),
        offline=Count('id', filter=Q(estado='Offline')),
        mantenimiento=Count('id', filter=Q(estado='Mantenimiento'))
    )
    
    return render(request, "core/configuraciones/config_impresoras.html", {
        'impresoras': impresoras,
        'segment': 'configuracion',
        'form': ImpresoraForm(),
        'stats': stats
    })


@admin_required
def gestionar_impresora(request, accion, id_impresora=None):
    """
    Gestiona impresoras: crear, eliminar, cambiar estado.
    
    Acciones:
    - 'crear': Crea nueva impresora (POST)
    - 'eliminar': Elimina impresora (POST)
    - 'toggle': Alterna entre Disponible y Offline (POST)
    - 'mantenimiento': Alterna entre Mantenimiento y Disponible (POST)
    """
    if request.method == 'POST':
        
        if accion == 'crear':
            form = ImpresoraForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Impresora agregada con éxito.")
            else:
                # Mostrar errores en formulario
                impresoras = Impresora.objects.all().order_by('estado', 'nombre')
                for field_errors in form.errors.values():
                    for error in field_errors:
                        messages.error(request, error)
                
                return render(request, "core/configuraciones/config_impresoras.html", {
                    'segment': 'configuracion',
                    'impresoras': impresoras,
                    'form': form
                })
        
        elif accion == 'eliminar' and id_impresora:
            impresora = get_object_or_404(Impresora, id=id_impresora)
            nombre = impresora.nombre
            impresora.delete()
            messages.success(request, f"Impresora '{nombre}' eliminada del sistema.")
        
        elif accion == 'toggle' and id_impresora:
            impresora = get_object_or_404(Impresora, id=id_impresora)
            nuevo_estado = "Disponible" if impresora.estado == "Offline" else "Offline"
            success, msg, msg_type = _cambiar_estado_impresora(impresora, nuevo_estado)
            getattr(messages, msg_type)(request, msg)
        
        elif accion == 'mantenimiento' and id_impresora:
            impresora = get_object_or_404(Impresora, id=id_impresora)
            nuevo_estado = "Disponible" if impresora.estado == "Mantenimiento" else "Mantenimiento"
            success, msg, msg_type = _cambiar_estado_impresora(impresora, nuevo_estado)
            getattr(messages, msg_type)(request, msg)

    return redirect('core:lista_impresoras')


@admin_required
def configuracion_pago(request):
    """
    Gestión de datos bancarios y condiciones de cobro.
    """
    config = ConfiguracionPago.objects.first()

    if request.method == 'POST':
        datos = {
            'banco': request.POST.get('banco', '').strip(),
            'titular': request.POST.get('titular', '').strip(),
            'numero_cuenta': request.POST.get('numero_cuenta', '').strip(),
            'tipo_cuenta': request.POST.get('tipo_cuenta', '').strip(),
            'cedula': request.POST.get('cedula', '').strip(),
            'telefono_pago': request.POST.get('telefono_pago', '').strip(),
            'instrucciones_adicionales': request.POST.get('instrucciones_adicionales', '').strip(),
            'porcentaje_anticipo': request.POST.get('porcentaje_anticipo', '50'),
            'activo': 'activo' in request.POST,
        }

        # Validaciones
        if not datos['banco'] or not datos['titular'] or not datos['numero_cuenta']:
            messages.error(request, "Banco, titular y número de cuenta son obligatorios.")
            return render(request, 'core/configuraciones/config_pago.html', {
                'config': config, 
                'segment': 'configuracion'
            })

        try:
            datos['porcentaje_anticipo'] = float(datos['porcentaje_anticipo'])
            if not (1 <= datos['porcentaje_anticipo'] <= 100):
                raise ValueError("Rango inválido")
        except (ValueError, TypeError):
            messages.error(request, "El porcentaje debe ser un número entre 1 y 100.")
            return render(request, 'core/configuraciones/config_pago.html', {
                'config': config, 
                'segment': 'configuracion'
            })

        # Guardar o actualizar
        if config:
            for campo, valor in datos.items():
                setattr(config, campo, valor)
            config.save()
        else:
            ConfiguracionPago.objects.create(**datos)

        messages.success(request, "Configuración de cobros guardada correctamente.")
        return redirect('core:configuracion_pago')

    return render(request, 'core/configuraciones/config_pago.html', {
        'config': config,
        'segment': 'configuracion',
    })

@admin_required
def configuracion_sitio_publico(request):
    """
    Configuración SIMPLIFICADA del sitio público.
    
    Solo permite editar:
    - Estadísticas
    - Dónde mostrar materiales
    - Productos destacados
    - Proceso
    - Contacto
    
    Y gestionar cards de materiales y proceso.
    """
    config = ConfiguracionSitio.obtener()
    cards_materiales = CardPublica.objects.filter(seccion='materiales').order_by('orden')
    cards_proceso = CardPublica.objects.filter(seccion='proceso').order_by('orden')

    if request.method == 'POST':
        seccion = request.POST.get('seccion', 'estadisticas')
        
        form_map = {
            'estadisticas': EstadisticasForm,
            'materiales': MaterialesForm,
            'productos': ProductosDestacadosForm,
            'proceso': ProcesoForm,
            'contacto': ContactoForm,
        }
        
        FormClass = form_map.get(seccion, EstadisticasForm)
        form = FormClass(request.POST, instance=config)
        
        if form.is_valid():
            form.save()
            messages.success(request, f"{seccion.title()} actualizado.")
            return redirect('core:configuracion_sitio_publico')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return render(request, 'core/configuraciones/config_sitio.html', {
        'config': config,
        'cards_materiales': cards_materiales,
        'cards_proceso': cards_proceso,
        'badge_colores': CardPublica.BADGE_COLOR_CHOICES,
        'segment': 'configuracion',
        # Forms
        'stats_form': EstadisticasForm(instance=config),
        'materiales_form': MaterialesForm(instance=config),
        'prod_dest_form': ProductosDestacadosForm(instance=config),
        'proceso_form': ProcesoForm(instance=config),
        'contacto_form': ContactoForm(instance=config),
    })


@admin_required
def crear_card(request):
    """Crea un nuevo card (material o proceso)."""
    if request.method == 'POST':
        form = CardPublicaForm(request.POST, request.FILES)
        if form.is_valid():
            card = form.save(commit=False)
            if not card.orden:
                last_orden = CardPublica.objects.filter(
                    seccion=card.seccion
                ).aggregate(max_orden=Count('id'))['max_orden'] or 0
                card.orden = last_orden
            card.save()
            messages.success(request, f"Card '{card.titulo}' creado.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return redirect('core:configuracion_sitio_publico')


@admin_required
def editar_card(request, card_id):
    """Edita un card existente."""
    card = get_object_or_404(CardPublica, pk=card_id)
    
    if request.method == 'POST':
        form = CardPublicaForm(request.POST, request.FILES, instance=card)
        if form.is_valid():
            card = form.save(commit=False)
            if 'limpiar_imagen' in request.POST:
                if card.imagen:
                    card.imagen.delete(save=False)
                card.imagen = None
            card.save()
            messages.success(request, f"Card '{card.titulo}' actualizado.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    return redirect('core:configuracion_sitio_publico')


@admin_required
@require_POST
def eliminar_card(request, card_id):
    """Elimina un card."""
    card = get_object_or_404(CardPublica, pk=card_id)
    titulo = card.titulo
    card.delete()
    messages.success(request, f"Card '{titulo}' eliminado.")
    return redirect('core:configuracion_sitio_publico')


@admin_required
@require_POST
def reordenar_cards(request):
    """Reordena cards mediante AJAX."""
    try:
        data = json.loads(request.body)
        
        if not isinstance(data, list):
            return JsonResponse({'ok': False, 'error': 'Formato inválido'}, status=400)
        
        for item in data:
            if 'id' not in item or 'orden' not in item:
                return JsonResponse({'ok': False, 'error': 'Campos requeridos'}, status=400)
            CardPublica.objects.filter(pk=item['id']).update(orden=item['orden'])
        
        return JsonResponse({'ok': True})
    
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
