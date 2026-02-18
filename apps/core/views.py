from django.shortcuts import render, redirect
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
from apps.pedidos.models import Pago
from apps.finanzas.models import Gasto
from apps.materiales.models import Material
from apps.pedidos.models import Pedido
from apps.usuarios.decorators import admin_required
from django.contrib import messages
import os
from django.conf import settings
from apps.productos.models import Categoria, Producto
from apps.finanzas.models import Gasto
from django.shortcuts import get_object_or_404
from apps.core.forms import ImpresoraForm
from .models import Impresora
from django.db.models import Q, Count


@admin_required
def gestionar_media_huerfana(request):
    # Mapeo de carpetas -> (Modelo, campo_en_el_modelo)
    # Si tienes un modelo para la galería o gastos, añádelos aquí.
    mapeo_config = {
        'categorias': (Categoria, 'imagen'),
        'productos': (Producto, 'imagen'),
        'finanzas/comprobantes': (Gasto, 'comprobante'),
    }
    
    archivos_huerfanos = []
    
    # Archivos protegidos que NUNCA deben borrarse (Logo, .gitkeep, etc.)
    protegidos = ['.gitkeep', 'Logo.png', 'Log.png', 'Logo-figura.ico']

    for subcarpeta, (Modelo, campo_imagen) in mapeo_config.items():
        ruta_absoluta_carpeta = os.path.join(settings.MEDIA_ROOT, subcarpeta)
        
        if os.path.exists(ruta_absoluta_carpeta):
            # Obtener archivos en BD (solo el nombre del archivo)
            archivos_en_bd = Modelo.objects.exclude(**{f"{campo_imagen}": ""}).values_list(campo_imagen, flat=True)
            nombres_en_bd = [os.path.basename(str(path)) for path in archivos_en_bd]

            # Listar contenido de la carpeta
            for nombre_item in os.listdir(ruta_absoluta_carpeta):
                ruta_completa_item = os.path.join(ruta_absoluta_carpeta, nombre_item)
                
                # REGLA DE ORO: Solo procesar si es ARCHIVO
                if os.path.isfile(ruta_completa_item):
                    if nombre_item not in protegidos and nombre_item not in nombres_en_bd:
                        ruta_relativa = os.path.join(subcarpeta, nombre_item)
                        archivos_huerfanos.append({
                            'nombre': nombre_item,
                            'ruta_relativa': ruta_relativa,
                            'url': f"{settings.MEDIA_URL}{ruta_relativa}".replace('\\', '/'),
                            'tipo': subcarpeta.split('/')[0] # 'productos' o 'categorias'
                        })
    
    # Manejo del borrado (POST)
    if request.method == "POST":
        archivos_a_borrar = request.POST.getlist('archivos')
        count = 0
        for ruta_rel in archivos_a_borrar:
            # Evitar que alguien intente borrar archivos fuera de media por seguridad
            if '..' in ruta_rel or protegidos[0] in ruta_rel:
                continue
                
            ruta_final = os.path.join(settings.MEDIA_ROOT, ruta_rel)
            
            if os.path.exists(ruta_final) and os.path.isfile(ruta_final):
                try:
                    os.remove(ruta_final)
                    count += 1
                except Exception as e:
                    print(f"Error borrando {ruta_final}: {e}")
        
        messages.success(request, f"¡Limpieza completada! Se eliminaron {count} archivos.")
        return redirect('core:config_media')

    return render(request, 'core/configuraciones/config_media.html', {
        'segment': 'configuracion',
        'archivos': archivos_huerfanos
    })


@admin_required
def dashboard_admin(request):
    """
    Vista principal del dashboard administrativo.
    Muestra resumen de ingresos, gastos, utilidad y alertas de stock.
    """
    ahora = timezone.now()
    ingresos_mes = Pago.objects.filter(
        fecha_pago__month=ahora.month, fecha_pago__year=ahora.year
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    gastos_mes = Gasto.objects.filter(
        fecha__month=ahora.month, fecha__year=ahora.year
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    materiales = Material.objects.all()
    total_gramos = materiales.aggregate(Sum("stock_actual"))[
        "stock_actual__sum"] or 0
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
    return render(request, "core/calculadora.html")

@admin_required
def configuracion(request):
    """
    Vista principal de configuración.
    """
    return render(request, "core/configuraciones/configuracion.html", {
        'segment': 'configuracion'
    })

@admin_required
def lista_impresoras(request):
    impresoras = Impresora.objects.all().order_by('estado', 'nombre')
    rescatadas = 0

    for imp in impresoras:
        if imp.actualizar_estado_automatico():
            rescatadas += 1
    if rescatadas > 0:
        messages.info(request, f"Se han liberado {rescatadas} impresoras que no tenían trabajo activo.")
    
    

    stats = Impresora.objects.aggregate(
        total=Count('id'),
        disponibles=Count('id', filter=Q(estado='Disponible')),
        imprimiendo=Count('id', filter=Q(estado='Imprimiendo')),
        offline=Count('id', filter=Q(estado='Offline')),
        mantenimiento=Count('id', filter=Q(estado='Mantenimiento'))
    )
    
    form = ImpresoraForm()
    return render(request, "core/configuraciones/config_impresoras.html", {
        'impresoras': impresoras,
        'segment': 'configuracion',
        'form': form,
        'stats': stats
    })

@admin_required
def gestionar_impresora(request, accion, id_impresora=None):
    if request.method == 'POST':
        if accion == 'crear':
            form = ImpresoraForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Impresora agregada con éxito.")
                return redirect('core:lista_impresoras') 
            else:
                impresoras = Impresora.objects.all().order_by('estado', 'nombre')
                for errors in form.errors.values():
                    for error in errors:
                        messages.error(request, error)
                
                return render(request, "core/configuraciones/config_impresoras.html", {
                    'segment': 'configuracion',
                    'impresoras': impresoras,
                    'form': form
                })
        
        elif accion == 'eliminar' and id_impresora:
            impresora = get_object_or_404(Impresora, id=id_impresora)
            impresora.delete()
            messages.success(request, "Máquina eliminada del sistema.")
            
        elif accion == 'toggle' and id_impresora:
            impresora = get_object_or_404(Impresora, id=id_impresora)
            # Si está Offline la ponemos Disponible, y viceversa
            # Nota: Si estaba en mantenimiento, esto también la saca de mantenimiento
            if impresora.estado == "Offline":
                impresora.estado = "Disponible"
            else:
                impresora.estado = "Offline"
            impresora.save()
            messages.success(request, f"Estado de {impresora.nombre} actualizado.")

        # --- NUEVA ACCIÓN DE MANTENIMIENTO ---
        elif accion == 'mantenimiento' and id_impresora:
            impresora = get_object_or_404(Impresora, id=id_impresora)
            
            if impresora.estado == "Mantenimiento":
                impresora.estado = "Disponible"
                messages.success(request, f"{impresora.nombre} ya está operativa y disponible.")
            else:
                impresora.estado = "Mantenimiento"
                messages.info(request, f"{impresora.nombre} se ha marcado en mantenimiento.")
            
            impresora.save()

    return redirect('core:lista_impresoras')