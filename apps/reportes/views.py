"""
Vistas de Reportes y Analytics — A.N.T Studio
ACTUALIZADO: + Reporte Operativo, + Pérdidas de Material, corregido consumo de materiales
"""
import io
import json
from decimal import Decimal
from datetime import date, timedelta
from calendar import monthrange

from django.shortcuts import render
from django.db.models import Sum, Count, F, Avg, ExpressionWrapper, DurationField
from django.http import HttpResponse

from apps.finanzas.models import Gasto
from apps.materiales.models import Material

from apps.usuarios.decorators import admin_required
from apps.pedidos.models import Pedido, ItemPedido, Pago, PerdidaMaterial, SolicitudCotizacion

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _inicio_mes(d=None):
    d = d or date.today()
    return d.replace(day=1)

def _fin_mes(d=None):
    d = d or date.today()
    ultimo = monthrange(d.year, d.month)[1]
    return d.replace(day=ultimo)

def _mes_anterior(d=None):
    d = d or date.today()
    primer_dia = d.replace(day=1)
    return (primer_dia - timedelta(days=1)).replace(day=1)

def _fmt(valor):
    if valor is None:
        return 0.0
    return float(Decimal(str(valor)).quantize(Decimal("0.01")))

def _variacion(actual, anterior):
    if not anterior:
        return None
    try:
        return round(((actual - anterior) / anterior) * 100, 1)
    except Exception:
        return None

def _rango_mes(offset_desde_hoy, hoy=None):
    hoy = hoy or date.today()
    d = _inicio_mes(hoy)
    for _ in range(offset_desde_hoy):
        d = _mes_anterior(d)
    return d, _fin_mes(d)


# ═══════════════════════════════════════════════════════════════════
# VISTA PRINCIPAL — DASHBOARD
# ═══════════════════════════════════════════════════════════════════

@admin_required
def dashboard(request):
    hoy = date.today()

    inicio_mes, fin_mes = _rango_mes(0, hoy)
    inicio_ant, fin_ant = _rango_mes(1, hoy)

    ingresos_mes = Pago.objects.filter(
        fecha_pago__date__gte=inicio_mes,
        fecha_pago__date__lte=fin_mes,
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    ingresos_ant = Pago.objects.filter(
        fecha_pago__date__gte=inicio_ant,
        fecha_pago__date__lte=fin_ant,
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    gastos_mes = Gasto.objects.filter(
        fecha__gte=inicio_mes, fecha__lte=fin_mes
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    gastos_ant = Gasto.objects.filter(
        fecha__gte=inicio_ant, fecha__lte=fin_ant
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    ganancia_mes = ingresos_mes - gastos_mes
    ganancia_ant = ingresos_ant - gastos_ant

    pedidos_activos_qs = Pedido.objects.filter(
        estado_pedido__in=['En_Espera', 'Confirmado', 'En_Produccion', 'Listo']
    ).prefetch_related('pagos')
    saldo_pendiente_total = sum(p.saldo_pendiente for p in pedidos_activos_qs)

    pedidos_mes = Pedido.objects.filter(
        fecha_creacion__date__gte=inicio_mes
    ).count()
    pedidos_ant_cnt = Pedido.objects.filter(
        fecha_creacion__date__gte=inicio_ant,
        fecha_creacion__date__lte=fin_ant,
    ).count()

    materiales_criticos = Material.objects.filter(
        activo=True, stock_actual__lte=F('stock_minimo')
    ).count()

    perdidas_mes = PerdidaMaterial.objects.filter(
        fecha__date__gte=inicio_mes
    ).aggregate(t=Sum('gramos_perdidos'))['t'] or Decimal('0')

    kpis = {
        'ingresos_mes':          ingresos_mes,
        'ingresos_var':          _variacion(ingresos_mes, ingresos_ant),
        'gastos_mes':            gastos_mes,
        'gastos_var':            _variacion(gastos_mes, gastos_ant),
        'ganancia_mes':          ganancia_mes,
        'ganancia_var':          _variacion(ganancia_mes, ganancia_ant),
        'saldo_pendiente_total': saldo_pendiente_total,
        'pedidos_mes':           pedidos_mes,
        'pedidos_var':           _variacion(pedidos_mes, pedidos_ant_cnt),
        'materiales_criticos':   materiales_criticos,
        'perdidas_mes_g':        perdidas_mes,
        'solicitudes_nuevas':    SolicitudCotizacion.objects.filter(estado='Pendiente').count(),
    }

    estados_raw = (
        Pedido.objects
        .values('estado_pedido')
        .annotate(total=Count('id'))
        .order_by('estado_pedido')
    )
    LABELS_ESTADO = {
        'En_Espera':     'En Espera',
        'Confirmado':    'Confirmado',
        'En_Produccion': 'En Producción',
        'Listo':         'Listo',
        'Entregado':     'Entregado',
        'Cancelado':     'Cancelado',
    }
    COLORES_ESTADO = {
        'En_Espera':     '#f59e0b',
        'Confirmado':    '#3b82f6',
        'En_Produccion': '#8b5cf6',
        'Listo':         '#06b6d4',
        'Entregado':     '#10b981',
        'Cancelado':     '#ef4444',
    }
    estados_chart = {
        'labels': [LABELS_ESTADO.get(e['estado_pedido'], e['estado_pedido']) for e in estados_raw],
        'data':   [e['total'] for e in estados_raw],
        'colors': [COLORES_ESTADO.get(e['estado_pedido'], '#64748b') for e in estados_raw],
    }

    NOMBRES_MES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                   'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

    meses_chart_labels = []
    meses_ingresos     = []
    meses_gastos       = []
    meses_ganancias    = []

    for offset in range(5, -1, -1):
        primer_dia, ultimo_dia = _rango_mes(offset, hoy)

        ing = Pago.objects.filter(
            fecha_pago__date__gte=primer_dia,
            fecha_pago__date__lte=ultimo_dia,
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

        gas = Gasto.objects.filter(
            fecha__gte=primer_dia, fecha__lte=ultimo_dia
        ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

        meses_chart_labels.append(f"{NOMBRES_MES[primer_dia.month - 1]} {primer_dia.year}")
        meses_ingresos.append(_fmt(ing))
        meses_gastos.append(_fmt(gas))
        meses_ganancias.append(_fmt(ing - gas))

    chart_ingresos_gastos = {
        'labels':    meses_chart_labels,
        'ingresos':  meses_ingresos,
        'gastos':    meses_gastos,
        'ganancias': meses_ganancias,
    }

    top_productos = (
        ItemPedido.objects
        .filter(variante__isnull=False, item_padre__isnull=True)
        .values('variante__producto__nombre')
        .annotate(
            unidades=Sum('cantidad'),
            ingresos=Sum(F('precio_unitario') * F('cantidad')),
        )
        .order_by('-unidades')[:5]
    )

    top_contenedores = (
        ItemPedido.objects
        .filter(variante__isnull=True, item_padre__isnull=True)
        .values('descripcion')
        .annotate(unidades=Sum('cantidad'))
        .order_by('-unidades')[:5]
    )

    todos_materiales = Material.objects.filter(activo=True).select_related('tipo', 'color', 'marca')
    materiales_bajos = (
        Material.objects
        .filter(activo=True, stock_actual__lte=F('stock_minimo'))
        .select_related('tipo', 'color', 'marca')
        .order_by('stock_actual')[:5]
    )
    total_gramos = todos_materiales.aggregate(t=Sum('stock_actual'))['t'] or 0
    total_kg     = float(total_gramos) / 1000

    ultimos_pedidos = (
        Pedido.objects
        .select_related('usuario')
        .order_by('-fecha_creacion')[:5]
    )

    gastos_cat = (
        Gasto.objects
        .filter(fecha__gte=inicio_mes, fecha__lte=fin_mes)
        .values('tipo')
        .annotate(total=Sum('monto'))
        .order_by('-total')
    )
    LABELS_GASTO = dict(Gasto.TIPOS)
    gastos_cat_chart = {
        'labels': [LABELS_GASTO.get(g['tipo'], g['tipo']) for g in gastos_cat],
        'data':   [_fmt(g['total']) for g in gastos_cat],
    }

    from apps.core.models import Impresora
    impresoras = Impresora.objects.all()
    impresoras_stats = {
        'total':         impresoras.count(),
        'disponibles':   impresoras.filter(estado='Disponible').count(),
        'imprimiendo':   impresoras.filter(estado='Imprimiendo').count(),
        'mantenimiento': impresoras.filter(estado__in=['Mantenimiento', 'Offline']).count(),
    }

    mostrar_recordatorio_reporte = hoy.day <= 3

    context = {
        'segment':   'reportes',
        'hoy':       hoy,
        'kpis':      kpis,
        'estados_chart_json':         json.dumps(estados_chart),
        'chart_ingresos_gastos_json': json.dumps(chart_ingresos_gastos),
        'gastos_cat_chart_json':      json.dumps(gastos_cat_chart),
        'top_productos':    top_productos,
        'top_contenedores': top_contenedores,
        'materiales_bajos': materiales_bajos,
        'total_kg':         total_kg,
        'ultimos_pedidos':  ultimos_pedidos,
        'impresoras_stats': impresoras_stats,
        'mostrar_recordatorio_reporte': mostrar_recordatorio_reporte,
        'mes_anterior_label': f"{['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'][_rango_mes(1,hoy)[0].month - 1]} {_rango_mes(1,hoy)[0].year}",
        'fin_ant':    fin_ant,
        'inicio_mes': inicio_mes,
        'inicio_ant': inicio_ant,
    }
    return render(request, 'reportes/dashboard.html', context)


# ═══════════════════════════════════════════════════════════════════
# VISTA — REPORTE DE VENTAS
# ═══════════════════════════════════════════════════════════════════

@admin_required
def reporte_ventas(request):
    hoy = date.today()
    fecha_desde_str = request.GET.get('desde', _inicio_mes(hoy).isoformat())
    fecha_hasta_str = request.GET.get('hasta', hoy.isoformat())

    try:
        fecha_desde = date.fromisoformat(fecha_desde_str)
        fecha_hasta = date.fromisoformat(fecha_hasta_str)
    except ValueError:
        fecha_desde = _inicio_mes(hoy)
        fecha_hasta = hoy

    pagos = (
        Pago.objects
        .filter(fecha_pago__date__gte=fecha_desde, fecha_pago__date__lte=fecha_hasta)
        .select_related('pedido__usuario')
        .order_by('-fecha_pago')
    )
    total_recaudado = pagos.aggregate(t=Sum('monto'))['t'] or Decimal('0')
    total_pedidos   = Pedido.objects.filter(
        fecha_creacion__date__gte=fecha_desde,
        fecha_creacion__date__lte=fecha_hasta,
    ).count()

    context = {
        'segment':         'reportes',
        'pagos':           pagos,
        'total_recaudado': total_recaudado,
        'total_pedidos':   total_pedidos,
        'fecha_desde':     fecha_desde,
        'fecha_hasta':     fecha_hasta,
    }
    return render(request, 'reportes/ventas.html', context)


# ═══════════════════════════════════════════════════════════════════
# VISTA — REPORTE DE INVENTARIO
# ═══════════════════════════════════════════════════════════════════

@admin_required
def reporte_inventario(request):
    from django.core.paginator import Paginator

    filtro_estado = request.GET.get('estado', '')
    filtro_tipo   = request.GET.get('tipo', '')

    qs = (
        Material.objects
        .filter(activo=True)
        .select_related('tipo', 'color', 'marca')
        .order_by('tipo__nombre', 'color__nombre')
    )

    if filtro_tipo:
        qs = qs.filter(tipo__nombre=filtro_tipo)

    if filtro_estado == 'critico':
        qs = qs.filter(stock_actual__lte=F('stock_minimo'))
    elif filtro_estado == 'ok':
        qs = qs.filter(stock_actual__gt=F('stock_minimo'))

    todos_base          = Material.objects.filter(activo=True).select_related('tipo', 'color', 'marca')
    total_criticos      = todos_base.filter(stock_actual__lte=F('stock_minimo')).count()
    valor_total_inventario = sum(
        m.stock_actual * m.costo_por_gramo
        for m in todos_base
    )

    paginator   = Paginator(qs, 50)
    page_number = request.GET.get('page', 1)
    page_obj    = paginator.get_page(page_number)

    tipos_disponibles = (
        Material.objects
        .filter(activo=True)
        .values_list('tipo__nombre', flat=True)
        .distinct()
        .order_by('tipo__nombre')
    )

    context = {
        'segment':                'reportes',
        'page_obj':               page_obj,
        'paginator':              paginator,
        'valor_total_inventario': valor_total_inventario,
        'total_activos':          todos_base.count(),
        'total_filtrados':        qs.count(),
        'total_criticos':         total_criticos,
        'filtro_estado':          filtro_estado,
        'filtro_tipo':            filtro_tipo,
        'tipos_disponibles':      tipos_disponibles,
    }
    return render(request, 'reportes/inventario.html', context)


# ═══════════════════════════════════════════════════════════════════
# VISTA — REPORTE OPERATIVO ← NUEVA
# ═══════════════════════════════════════════════════════════════════

@admin_required
def reporte_operativo(request):
    """
    Reporte de desempeño operativo del taller.
    Muestra tiempos de producción, tasa de cumplimiento y pedidos activos.
    """
    hoy = date.today()
    fecha_desde_str = request.GET.get('desde', _inicio_mes(hoy).isoformat())
    fecha_hasta_str = request.GET.get('hasta', hoy.isoformat())

    try:
        fecha_desde = date.fromisoformat(fecha_desde_str)
        fecha_hasta = date.fromisoformat(fecha_hasta_str)
    except ValueError:
        fecha_desde = _inicio_mes(hoy)
        fecha_hasta = hoy

    pedidos_qs = (
        Pedido.objects
        .filter(
            fecha_creacion__date__gte=fecha_desde,
            fecha_creacion__date__lte=fecha_hasta,
        )
        .select_related('usuario')
        .order_by('-fecha_creacion')
    )

    total_pedidos     = pedidos_qs.count()
    entregados        = pedidos_qs.filter(estado_pedido='Entregado').count()
    cancelados        = pedidos_qs.filter(estado_pedido='Cancelado').count()
    en_produccion     = pedidos_qs.filter(estado_pedido='En_Produccion').count()
    listos            = pedidos_qs.filter(estado_pedido='Listo').count()
    tasa_completacion = round((entregados / total_pedidos * 100), 1) if total_pedidos > 0 else 0

    # Tiempo promedio de producción (fecha_inicio_produccion → fecha_entrega)
    # Solo pedidos entregados con ambas fechas registradas
    pedidos_con_tiempos = pedidos_qs.filter(
        estado_pedido='Entregado',
        fecha_inicio_produccion__isnull=False,
        fecha_entrega__isnull=False,
    )

    tiempo_promedio_horas = None
    if pedidos_con_tiempos.exists():
        tiempos = []
        for p in pedidos_con_tiempos:
            delta = p.fecha_entrega - p.fecha_inicio_produccion
            tiempos.append(delta.total_seconds() / 3600)
        tiempo_promedio_horas = round(sum(tiempos) / len(tiempos), 1)

    # Tiempo promedio desde solicitud hasta inicio de producción (capacidad de respuesta)
    pedidos_con_inicio = pedidos_qs.filter(
        fecha_inicio_produccion__isnull=False,
    )
    tiempo_respuesta_horas = None
    if pedidos_con_inicio.exists():
        tiempos_resp = []
        for p in pedidos_con_inicio:
            delta = p.fecha_inicio_produccion - p.fecha_creacion
            tiempos_resp.append(delta.total_seconds() / 3600)
        tiempo_respuesta_horas = round(sum(tiempos_resp) / len(tiempos_resp), 1)

    # Pedidos activos con tiempo transcurrido (para detectar cuellos de botella)
    pedidos_activos = (
        Pedido.objects
        .filter(estado_pedido__in=['En_Espera', 'Confirmado', 'En_Produccion', 'Listo'])
        .select_related('usuario')
        .order_by('fecha_creacion')
    )
    pedidos_activos_data = []
    from django.utils import timezone
    ahora = timezone.now()
    for p in pedidos_activos:
        dias_transcurridos = (ahora - p.fecha_creacion).days
        pedidos_activos_data.append({
            'pedido': p,
            'dias_transcurridos': dias_transcurridos,
            'alerta': dias_transcurridos > 7,  # Alerta si lleva más de 7 días
        })

    # Pérdidas del período
    perdidas_periodo = (
        PerdidaMaterial.objects
        .filter(fecha__date__gte=fecha_desde, fecha__date__lte=fecha_hasta)
        .select_related('material__tipo', 'material__color', 'pedido')
        .order_by('-fecha')
    )
    total_gramos_perdidos = perdidas_periodo.aggregate(t=Sum('gramos_perdidos'))['t'] or Decimal('0')

    context = {
        'segment':               'reportes',
        'fecha_desde':           fecha_desde,
        'fecha_hasta':           fecha_hasta,
        'pedidos':               pedidos_qs,
        'total_pedidos':         total_pedidos,
        'entregados':            entregados,
        'cancelados':            cancelados,
        'en_produccion':         en_produccion,
        'listos':                listos,
        'tasa_completacion':     tasa_completacion,
        'tiempo_promedio_horas': tiempo_promedio_horas,
        'tiempo_respuesta_horas': tiempo_respuesta_horas,
        'pedidos_activos_data':  pedidos_activos_data,
        'perdidas_periodo':      perdidas_periodo,
        'total_gramos_perdidos': total_gramos_perdidos,
    }
    return render(request, 'reportes/operativo.html', context)


# ═══════════════════════════════════════════════════════════════════
# PALETA CLARA — compartida por ambos exports
# ═══════════════════════════════════════════════════════════════════
P = {
    'header_bg':    '1E3A5F',
    'title_bg':     '0F2744',
    'subheader_bg': '2D5B8E',
    'row_a':        'F8FAFC',
    'row_b':        'EFF6FF',
    'total_bg':     'DBEAFE',
    'critico_bg':   'FFFBEB',
    'critico_bd':   'F59E0B',
    'header_fg':    'FFFFFF',
    'title_fg':     '10B981',
    'body_fg':      '1E293B',
    'muted_fg':     '64748B',
    'accent_green': '065F46',
    'accent_blue':  '1E40AF',
    'total_fg':     '1E3A5F',
    'critico_fg':   '92400E',
    'ok_fg':        '065F46',
    'reponer_fg':   'B45309',
}

def _p_fill(hex_color):
    return PatternFill('solid', fgColor=hex_color)

def _p_font(bold=False, color='1E293B', size=10, italic=False):
    return Font(bold=bold, color=color, size=size, name='Arial', italic=italic)

def _p_border(color='CBD5E1', style='thin'):
    s = Side(style=style, color=color)
    return Border(left=s, right=s, top=s, bottom=s)

def _p_border_critico():
    s_h = Side(style='medium', color=P['critico_bd'])
    s_v = Side(style='thin', color=P['critico_bd'])
    return Border(left=s_v, right=s_v, top=s_h, bottom=s_h)

def _p_align(h='left', v='center'):
    return Alignment(horizontal=h, vertical=v)

def _bloque_titulo(ws, titulo, subtitulo, n_cols, periodo='', generado=''):
    ws.merge_cells(f'A1:{get_column_letter(n_cols)}1')
    c = ws['A1']
    c.value = titulo
    c.font = _p_font(bold=True, color=P['title_fg'], size=15)
    c.fill = _p_fill(P['title_bg'])
    c.alignment = _p_align('center')
    ws.row_dimensions[1].height = 32

    ws.merge_cells(f'A2:{get_column_letter(n_cols)}2')
    c2 = ws['A2']
    c2.value = (f'Periodo: {periodo}' if periodo else subtitulo) + (f'   |   Generado: {generado}' if generado else '')
    c2.font = _p_font(color=P['muted_fg'], size=9, italic=True)
    c2.fill = _p_fill(P['title_bg'])
    c2.alignment = _p_align('center')
    ws.row_dimensions[2].height = 16

    ws.merge_cells(f'A3:{get_column_letter(n_cols)}3')
    ws['A3'].fill = _p_fill('10B981')
    ws.row_dimensions[3].height = 3

    ws.row_dimensions[4].height = 5
    for col in range(1, n_cols + 1):
        ws.cell(row=4, column=col).fill = _p_fill(P['title_bg'])

def _fila_encabezado(ws, row, values, height=22):
    for col, val in enumerate(values, 1):
        c = ws.cell(row=row, column=col, value=val)
        c.font = _p_font(bold=True, color=P['header_fg'], size=10)
        c.fill = _p_fill(P['header_bg'])
        c.alignment = _p_align('center')
        c.border = _p_border()
    ws.row_dimensions[row].height = height

def _fila_total_clara(ws, row, n_cols, label, formula_cols):
    for col in range(1, n_cols + 1):
        c = ws.cell(row=row, column=col)
        c.fill = _p_fill(P['total_bg'])
        c.border = _p_border('93C5FD', 'medium')

    c1 = ws.cell(row=row, column=1, value=label)
    c1.font = _p_font(bold=True, color=P['total_fg'], size=11)
    c1.fill = _p_fill(P['total_bg'])
    c1.alignment = _p_align('right')
    c1.border = _p_border('93C5FD', 'medium')

    for col, formula, fmt in formula_cols:
        tc = ws.cell(row=row, column=col, value=formula)
        tc.font = _p_font(bold=True, color=P['accent_green'], size=11)
        tc.fill = _p_fill(P['total_bg'])
        tc.number_format = fmt
        tc.alignment = _p_align('right')
        tc.border = _p_border('93C5FD', 'medium')

    ws.row_dimensions[row].height = 24


# ═══════════════════════════════════════════════════════════════════
# EXPORT VENTAS
# ═══════════════════════════════════════════════════════════════════

@admin_required
def exportar_ventas_excel(request):
    hoy = date.today()
    fecha_desde_str = request.GET.get('desde', _inicio_mes(hoy).isoformat())
    fecha_hasta_str = request.GET.get('hasta', hoy.isoformat())

    try:
        fecha_desde = date.fromisoformat(fecha_desde_str)
        fecha_hasta = date.fromisoformat(fecha_hasta_str)
    except ValueError:
        fecha_desde = _inicio_mes(hoy)
        fecha_hasta = hoy

    pagos = (
        Pago.objects
        .filter(fecha_pago__date__gte=fecha_desde, fecha_pago__date__lte=fecha_hasta)
        .select_related('pedido__usuario')
        .order_by('-fecha_pago')
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Ventas'
    ws.sheet_view.showGridLines = False

    N_COLS = 7
    periodo = f"{fecha_desde.strftime('%d/%m/%Y')} — {fecha_hasta.strftime('%d/%m/%Y')}"
    _bloque_titulo(ws, 'A.N.T Studio — Reporte de Ventas',
                   'Pagos recibidos en el periodo', N_COLS,
                   periodo=periodo, generado=hoy.strftime('%d/%m/%Y'))

    total_pagos = pagos.aggregate(t=Sum('monto'))['t'] or Decimal('0')
    n_pagos = pagos.count()

    kpi_data = [
        ('Total recaudado', f'RD$ {float(total_pagos):,.2f}', P['accent_green']),
        ('Pagos registrados', str(n_pagos), P['accent_blue']),
        ('Ticket promedio', f"RD$ {float(total_pagos / n_pagos):,.2f}" if n_pagos else 'RD$ 0.00', P['total_fg']),
    ]
    for i, (label, valor, color) in enumerate(kpi_data):
        col_l = i * 2 + 1
        col_v = col_l + 1
        ws.merge_cells(f'{get_column_letter(col_l)}5:{get_column_letter(col_v)}5')
        cl = ws.cell(row=5, column=col_l, value=label)
        cl.font = _p_font(color=P['muted_fg'], size=8)
        cl.fill = _p_fill('F1F5F9')
        cl.alignment = _p_align('center')
        cl.border = _p_border()
        ws.row_dimensions[5].height = 16

        ws.merge_cells(f'{get_column_letter(col_l)}6:{get_column_letter(col_v)}6')
        cv = ws.cell(row=6, column=col_l, value=valor)
        cv.font = _p_font(bold=True, color=color, size=13)
        cv.fill = _p_fill('F8FAFC')
        cv.alignment = _p_align('center')
        cv.border = _p_border()
        ws.row_dimensions[6].height = 28

    for col in range(1, N_COLS + 1):
        ws.cell(row=7, column=col).fill = _p_fill('E2E8F0')
    ws.row_dimensions[7].height = 3

    HEADERS = ['# Pedido', 'Cliente', 'Email', 'Metodo de Pago', 'Referencia', 'Fecha', 'Monto (RD$)']
    COL_WIDTHS = [11, 26, 28, 17, 20, 17, 16]
    _fila_encabezado(ws, 8, HEADERS)
    for i, w in enumerate(COL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A9'
    ws.auto_filter.ref = f'A8:{get_column_letter(N_COLS)}8'

    data_start = 9
    for row_idx, pago in enumerate(pagos, start=data_start):
        alt = (row_idx % 2 == 0)
        bg = P['row_a'] if alt else P['row_b']

        valores = [
            f'#{pago.pedido.id:04d}',
            pago.pedido.nombre_cliente,
            pago.pedido.email_cliente,
            pago.get_metodo_display(),
            pago.referencia or '—',
            pago.fecha_pago.strftime('%d/%m/%Y %H:%M'),
            float(pago.monto),
        ]
        for col_idx, valor in enumerate(valores, 1):
            c = ws.cell(row=row_idx, column=col_idx, value=valor)
            c.fill = _p_fill(bg)
            c.border = _p_border()
            c.font = _p_font(color=P['body_fg'])
            c.alignment = _p_align()

            if col_idx == 1:
                c.font = _p_font(bold=True, color=P['accent_blue'])
                c.alignment = _p_align('center')
            elif col_idx == 7:
                c.font = _p_font(bold=True, color=P['accent_green'])
                c.number_format = '#,##0.00'
                c.alignment = _p_align('right')
            elif col_idx == 6:
                c.font = _p_font(color=P['muted_fg'], size=9)
                c.alignment = _p_align('center')
        ws.row_dimensions[row_idx].height = 18

    total_row = data_start + n_pagos
    if n_pagos > 0:
        _fila_total_clara(ws, total_row, N_COLS, 'TOTAL RECAUDADO', [
            (7, f'=SUM(G{data_start}:G{total_row-1})', '#,##0.00'),
        ])
    else:
        ws.merge_cells(f'A{total_row}:{get_column_letter(N_COLS)}{total_row}')
        c = ws.cell(row=total_row, column=1, value='Sin pagos en este periodo.')
        c.font = _p_font(italic=True, color=P['muted_fg'])
        c.fill = _p_fill(P['row_a'])
        c.alignment = _p_align('center')
        c.border = _p_border()
        ws.row_dimensions[total_row].height = 30

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"ventas_{fecha_desde.strftime('%Y%m%d')}_{fecha_hasta.strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ═══════════════════════════════════════════════════════════════════
# EXPORT INVENTARIO
# ═══════════════════════════════════════════════════════════════════

@admin_required
def exportar_inventario_excel(request):
    materiales = list(
        Material.objects
        .filter(activo=True)
        .select_related('tipo', 'color', 'marca')
        .order_by('tipo__nombre', 'color__nombre')
    )

    hoy = date.today()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Inventario'
    ws.sheet_view.showGridLines = False

    N_COLS = 9
    _bloque_titulo(ws, 'A.N.T Studio — Inventario de Materiales',
                   f'{len(materiales)} materiales activos', N_COLS,
                   generado=hoy.strftime('%d/%m/%Y'))

    total_criticos = sum(1 for m in materiales if m.necesita_reposicion)
    valor_total = sum(m.stock_actual * m.costo_por_gramo for m in materiales)

    kpis_inv = [
        ('Materiales activos', str(len(materiales)), P['accent_blue']),
        ('Stock critico', str(total_criticos), P['reponer_fg'] if total_criticos > 0 else P['ok_fg']),
        ('Valor total inventario', f'RD$ {float(valor_total):,.2f}', P['accent_green']),
    ]
    for i, (label, valor, color) in enumerate(kpis_inv):
        col_l = i * 3 + 1
        col_v = col_l + 2
        ws.merge_cells(f'{get_column_letter(col_l)}5:{get_column_letter(col_v)}5')
        cl = ws.cell(row=5, column=col_l, value=label)
        cl.font = _p_font(color=P['muted_fg'], size=8)
        cl.fill = _p_fill('F1F5F9')
        cl.alignment = _p_align('center')
        cl.border = _p_border()
        ws.row_dimensions[5].height = 16

        ws.merge_cells(f'{get_column_letter(col_l)}6:{get_column_letter(col_v)}6')
        cv = ws.cell(row=6, column=col_l, value=valor)
        cv.font = _p_font(bold=True, color=color, size=13)
        cv.fill = _p_fill('F8FAFC')
        cv.alignment = _p_align('center')
        cv.border = _p_border()
        ws.row_dimensions[6].height = 28

    for col in range(1, N_COLS + 1):
        ws.cell(row=7, column=col).fill = _p_fill('E2E8F0')
    ws.row_dimensions[7].height = 3

    HEADERS = ['#', 'Tipo', 'Color', 'Marca', 'Stock (g)', 'Minimo (g)', 'Costo/g (RD$)', 'Valor Total (RD$)', 'Estado']
    COL_WIDTHS = [5, 13, 14, 14, 13, 13, 16, 18, 11]
    _fila_encabezado(ws, 8, HEADERS)
    for i, w in enumerate(COL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A9'
    ws.auto_filter.ref = f'A8:{get_column_letter(N_COLS)}8'

    data_start = 9
    for i, m in enumerate(materiales):
        row = data_start + i
        alt = (i % 2 == 0)
        critico = m.necesita_reposicion

        if critico:
            bg = P['critico_bg']
            brd = _p_border_critico()
            fg_mat = P['critico_fg']
        else:
            bg = P['row_a'] if alt else P['row_b']
            brd = _p_border()
            fg_mat = P['body_fg']

        data = [
            i + 1,
            m.tipo.nombre,
            m.color.nombre,
            m.marca.nombre,
            float(m.stock_actual),
            float(m.stock_minimo),
            float(m.costo_por_gramo),
            f'=E{row}*G{row}',
            'Reponer' if critico else 'OK',
        ]
        for col, val in enumerate(data, 1):
            c = ws.cell(row=row, column=col, value=val)
            c.fill = _p_fill(bg)
            c.border = brd
            c.alignment = _p_align()

            if col == 1:
                c.font = _p_font(color=P['muted_fg'], size=9)
                c.alignment = _p_align('center')
            elif col in (2, 3, 4):
                c.font = _p_font(bold=(col == 2), color=fg_mat)
            elif col in (5, 6):
                c.font = _p_font(
                    bold=critico and col == 5,
                    color=P['reponer_fg'] if (critico and col == 5) else fg_mat
                )
                c.number_format = '#,##0.00'
                c.alignment = _p_align('right')
            elif col == 7:
                c.font = _p_font(color=P['muted_fg'], size=9)
                c.number_format = '#,##0.0000'
                c.alignment = _p_align('right')
            elif col == 8:
                c.font = _p_font(bold=True, color=P['accent_green'])
                c.number_format = '#,##0.00'
                c.alignment = _p_align('right')
            elif col == 9:
                if critico:
                    c.font = _p_font(bold=True, color=P['reponer_fg'])
                else:
                    c.font = _p_font(bold=True, color=P['ok_fg'])
                c.alignment = _p_align('center')

        ws.row_dimensions[row].height = 18

    total_row = data_start + len(materiales)
    _fila_total_clara(ws, total_row, N_COLS, 'VALOR TOTAL DEL INVENTARIO', [
        (8, f'=SUM(H{data_start}:H{total_row-1})', '#,##0.00'),
    ])

    ley_row = total_row + 2
    ws.merge_cells(f'A{ley_row}:{get_column_letter(N_COLS)}{ley_row}')
    c = ws.cell(row=ley_row, column=1,
                value='Fondo amarillo = stock igual o por debajo del minimo configurado. Verificar y reponer.')
    c.font = _p_font(italic=True, color=P['reponer_fg'], size=8)
    c.fill = _p_fill(P['critico_bg'])
    c.border = _p_border_critico()
    ws.row_dimensions[ley_row].height = 16

    criticos_list = [m for m in materiales if m.necesita_reposicion]
    if criticos_list:
        ws2 = wb.create_sheet('Stock Critico')
        ws2.sheet_view.showGridLines = False
        _bloque_titulo(ws2, 'Materiales que necesitan reposicion',
                       f'{len(criticos_list)} materiales en stock critico', N_COLS,
                       generado=hoy.strftime('%d/%m/%Y'))

        ws2.merge_cells(f'A3:{get_column_letter(N_COLS)}3')
        ws2['A3'].fill = _p_fill(P['critico_bd'])
        ws2.row_dimensions[3].height = 3

        _fila_encabezado(ws2, 5,
                         ['#', 'Tipo', 'Color', 'Marca', 'Stock (g)', 'Minimo (g)', 'Costo/g (RD$)', 'Valor Total (RD$)', 'Deficit (g)'],
                         height=22)
        for i, w in enumerate(COL_WIDTHS, 1):
            ws2.column_dimensions[get_column_letter(i)].width = w
        ws2.freeze_panes = 'A6'

        for i, m in enumerate(criticos_list):
            row = 6 + i
            bg = P['critico_bg']
            brd = _p_border_critico()
            deficit = float(m.stock_minimo - m.stock_actual)

            data = [
                i + 1,
                m.tipo.nombre,
                m.color.nombre,
                m.marca.nombre,
                float(m.stock_actual),
                float(m.stock_minimo),
                float(m.costo_por_gramo),
                f'=E{row}*G{row}',
                deficit,
            ]
            for col, val in enumerate(data, 1):
                c = ws2.cell(row=row, column=col, value=val)
                c.fill = _p_fill(bg)
                c.border = brd
                c.alignment = _p_align()
                if col == 1:
                    c.font = _p_font(color=P['muted_fg'], size=9)
                    c.alignment = _p_align('center')
                elif col in (2, 3, 4):
                    c.font = _p_font(bold=(col == 2), color=P['critico_fg'])
                elif col == 5:
                    c.font = _p_font(bold=True, color=P['reponer_fg'])
                    c.number_format = '#,##0.00'
                    c.alignment = _p_align('right')
                elif col in (6, 8):
                    c.font = _p_font(color=P['critico_fg'])
                    c.number_format = '#,##0.00'
                    c.alignment = _p_align('right')
                elif col == 7:
                    c.font = _p_font(color=P['muted_fg'], size=9)
                    c.number_format = '#,##0.0000'
                    c.alignment = _p_align('right')
                elif col == 9:
                    c.font = _p_font(bold=True, color=P['reponer_fg'])
                    c.number_format = '#,##0.00'
                    c.alignment = _p_align('right')
            ws2.row_dimensions[row].height = 18

        tr2 = 6 + len(criticos_list)
        _fila_total_clara(ws2, tr2, N_COLS, 'TOTAL A REPONER (estimado)', [
            (8, f'=SUM(H6:H{tr2-1})', '#,##0.00'),
            (9, f'=SUM(I6:I{tr2-1})', '#,##0.00'),
        ])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"inventario_{hoy.strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ═══════════════════════════════════════════════════════════════════
# HELPERS — ESTILOS OSCUROS (para reporte ejecutivo)
# ═══════════════════════════════════════════════════════════════════

C = {
    'bg_dark':      '0F172A',
    'bg_mid':       '1E293B',
    'bg_card':      '1A2744',
    'accent':       '10B981',
    'accent_dark':  '059669',
    'accent_blue':  '3B82F6',
    'accent_amber': 'F59E0B',
    'accent_red':   'EF4444',
    'accent_purple':'8B5CF6',
    'white':        'FFFFFF',
    'gray_light':   'E2E8F0',
    'gray_mid':     '94A3B8',
    'row_alt':      '162032',
    'row_normal':   '0F1C2E',
}

def _fill(hex_color):
    return PatternFill('solid', fgColor=hex_color)

def _font(bold=False, color='FFFFFF', size=10, italic=False):
    return Font(bold=bold, color=color, size=size, name='Arial', italic=italic)

def _border(color='1E3A5F'):
    s = Side(style='thin', color=color)
    return Border(left=s, right=s, top=s, bottom=s)

def _align(h='left', v='center', wrap=False):
    return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

def _set_col_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

def _titulo_hoja(ws, titulo, subtitulo, n_cols, periodo=''):
    ws.merge_cells(f'A1:{get_column_letter(n_cols)}1')
    c = ws['A1']
    c.value = titulo
    c.font = _font(bold=True, color=C['accent'], size=16)
    c.fill = _fill(C['bg_dark'])
    c.alignment = _align('center')
    ws.row_dimensions[1].height = 36

    ws.merge_cells(f'A2:{get_column_letter(n_cols)}2')
    c2 = ws['A2']
    c2.value = subtitulo + (f'  ·  {periodo}' if periodo else '')
    c2.font = _font(color=C['gray_mid'], size=9, italic=True)
    c2.fill = _fill(C['bg_dark'])
    c2.alignment = _align('center')
    ws.row_dimensions[2].height = 16

    ws.merge_cells(f'A3:{get_column_letter(n_cols)}3')
    ws['A3'].fill = _fill(C['accent'])
    ws.row_dimensions[3].height = 3

    ws.row_dimensions[4].height = 6
    for col in range(1, n_cols + 1):
        ws.cell(row=4, column=col).fill = _fill(C['bg_dark'])

def _header_row(ws, row, values, bg=None, height=22):
    bg = bg or C['bg_card']
    for col, val in enumerate(values, 1):
        c = ws.cell(row=row, column=col, value=val)
        c.font = _font(bold=True, color='FFFFFF', size=10)
        c.fill = _fill(bg)
        c.alignment = _align('center')
        c.border = _border()
    ws.row_dimensions[row].height = height

def _kpi_card(ws, row, col, label, valor, formato='#,##0.00', color=None):
    color = color or C['accent']
    c_label = ws.cell(row=row, column=col, value=label)
    c_label.font = _font(color=C['gray_mid'], size=9)
    c_label.fill = _fill(C['bg_mid'])
    c_label.alignment = _align('center')
    c_label.border = _border()
    ws.row_dimensions[row].height = 18

    c_val = ws.cell(row=row + 1, column=col, value=valor)
    c_val.font = _font(bold=True, color=color, size=16)
    c_val.fill = _fill(C['bg_mid'])
    c_val.alignment = _align('center')
    c_val.number_format = formato
    c_val.border = _border()
    ws.row_dimensions[row + 1].height = 32

def _data_row(ws, row, col_start, values, alt=False, number_cols=None, right_cols=None, center_cols=None, highlight_col=None, highlight_color=None):
    bg = C['row_alt'] if alt else C['row_normal']
    number_cols = number_cols or []
    right_cols = right_cols or []
    center_cols = center_cols or []
    for i, val in enumerate(values):
        col = col_start + i
        c = ws.cell(row=row, column=col, value=val)
        c.fill = _fill(bg)
        c.border = _border()
        c.font = _font(color=C['gray_light'])
        c.alignment = _align()
        if col in number_cols:
            c.number_format = '#,##0.00'
            c.alignment = _align('right')
        if col in right_cols:
            c.alignment = _align('right')
        if col in center_cols:
            c.alignment = _align('center')
        if highlight_col and col == highlight_col:
            c.font = _font(bold=True, color=highlight_color or C['accent'])
    ws.row_dimensions[row].height = 20

def _fila_totales(ws, row, n_cols, label_cols, formula_cols, label='TOTALES'):
    ws.merge_cells(f'A{row}:{get_column_letter(label_cols)}{row}')
    c = ws.cell(row=row, column=1, value=label)
    c.font = _font(bold=True, color=C['accent'], size=11)
    c.fill = _fill(C['bg_dark'])
    c.alignment = _align('right')
    c.border = _border()
    for col in range(2, label_cols + 1):
        ws.cell(row=row, column=col).fill = _fill(C['bg_dark'])
        ws.cell(row=row, column=col).border = _border()

    for col, formula, fmt in formula_cols:
        tc = ws.cell(row=row, column=col, value=formula)
        tc.font = _font(bold=True, color=C['accent'], size=11)
        tc.fill = _fill(C['bg_dark'])
        tc.number_format = fmt
        tc.alignment = _align('right')
        tc.border = _border()

    for col in range(1, n_cols + 1):
        c = ws.cell(row=row, column=col)
        if not c.value:
            c.fill = _fill(C['bg_dark'])
            c.border = _border()
    ws.row_dimensions[row].height = 24

def _fila_sin_datos(ws, row, n_cols, mensaje='Sin datos para el período seleccionado.'):
    ws.merge_cells(f'A{row}:{get_column_letter(n_cols)}{row}')
    c = ws.cell(row=row, column=1, value=f'— {mensaje} —')
    c.font = _font(italic=True, color=C['gray_mid'], size=10)
    c.fill = _fill(C['bg_mid'])
    c.alignment = _align('center')
    c.border = _border()
    ws.row_dimensions[row].height = 36


# ═══════════════════════════════════════════════════════════════════
# QUERIES — DATOS REALES
# ═══════════════════════════════════════════════════════════════════

def _get_kpis(fecha_desde, fecha_hasta):
    ingresos = Pago.objects.filter(
        fecha_pago__date__gte=fecha_desde,
        fecha_pago__date__lte=fecha_hasta,
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    gastos = Gasto.objects.filter(
        fecha__gte=fecha_desde,
        fecha__lte=fecha_hasta,
    ).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    ganancia = ingresos - gastos
    margen = (ganancia / ingresos * 100) if ingresos > 0 else Decimal('0')

    pedidos_qs = Pedido.objects.filter(
        fecha_creacion__date__gte=fecha_desde,
        fecha_creacion__date__lte=fecha_hasta,
    )
    total_pedidos = pedidos_qs.count()
    entregados = pedidos_qs.filter(estado_pedido='Entregado').count()

    total_ingresos_pedidos = pedidos_qs.aggregate(t=Sum('precio_total'))['t'] or Decimal('0')
    ticket_promedio = (total_ingresos_pedidos / total_pedidos) if total_pedidos > 0 else Decimal('0')

    clientes_activos = pedidos_qs.filter(
        usuario__isnull=False
    ).values('usuario').distinct().count()

    materiales_criticos = Material.objects.filter(
        activo=True,
        stock_actual__lte=F('stock_minimo')
    ).count()

    tasa = (entregados / total_pedidos * 100) if total_pedidos > 0 else 0

    return {
        'ingresos': float(ingresos),
        'gastos': float(gastos),
        'ganancia': float(ganancia),
        'margen': float(margen),
        'pedidos_total': total_pedidos,
        'pedidos_entregados': entregados,
        'ticket_promedio': float(ticket_promedio),
        'clientes_activos': clientes_activos,
        'materiales_criticos': materiales_criticos,
        'tasa_completacion': float(tasa),
    }


def _get_estados_pedido(fecha_desde, fecha_hasta):
    LABELS = {
        'En_Espera':     'En Espera',
        'Confirmado':    'Confirmado',
        'En_Produccion': 'En Producción',
        'Listo':         'Listo',
        'Entregado':     'Entregado',
        'Cancelado':     'Cancelado',
    }
    COLORES = {
        'En_Espera':     C['accent_amber'],
        'Confirmado':    C['accent_blue'],
        'En_Produccion': C['accent_purple'],
        'Listo':         '06B6D4',
        'Entregado':     C['accent'],
        'Cancelado':     C['accent_red'],
    }
    qs = Pedido.objects.filter(
        fecha_creacion__date__gte=fecha_desde,
        fecha_creacion__date__lte=fecha_hasta,
    ).values('estado_pedido').annotate(total=Count('id')).order_by('estado_pedido')

    return [
        (LABELS.get(r['estado_pedido'], r['estado_pedido']), r['total'], COLORES.get(r['estado_pedido'], '64748b'))
        for r in qs
    ]


def _get_metodos_pago(fecha_desde, fecha_hasta):
    LABELS = {
        'Efectivo':       'Efectivo',
        'Transferencia':  'Transferencia',
        'Contraentrega':  'Contraentrega',
        'Tarjeta':        'Tarjeta',
        'PayPal':         'PayPal',
        'Otro':           'Otro',
    }
    qs = Pago.objects.filter(
        fecha_pago__date__gte=fecha_desde,
        fecha_pago__date__lte=fecha_hasta,
    ).values('metodo').annotate(
        n_pagos=Count('id'),
        total=Sum('monto'),
    ).order_by('-total')

    total_global = sum(r['total'] or Decimal('0') for r in qs)

    result = []
    for r in qs:
        total = r['total'] or Decimal('0')
        pct = float(total / total_global * 100) if total_global > 0 else 0
        result.append((
            LABELS.get(r['metodo'], r['metodo']),
            r['n_pagos'],
            float(total),
            pct,
        ))
    return result


def _get_productos_vendidos(fecha_desde, fecha_hasta, limit=15):
    qs = (
        ItemPedido.objects
        .filter(
            variante__isnull=False,
            item_padre__isnull=True,
            pedido__fecha_creacion__date__gte=fecha_desde,
            pedido__fecha_creacion__date__lte=fecha_hasta,
        )
        .values('variante__producto__nombre', 'variante__codigo_sku')
        .annotate(
            unidades=Sum('cantidad'),
            n_pedidos=Count('pedido', distinct=True),
            ingresos=Sum(F('precio_unitario') * F('cantidad')),
            costo_est=Sum(F('costo_material_unitario') * F('cantidad')),
        )
        .order_by('-unidades')[:limit]
    )

    result = []
    for r in qs:
        ingresos = float(r['ingresos'] or 0)
        costo = float(r['costo_est'] or 0)
        result.append((
            r['variante__producto__nombre'],
            r['variante__codigo_sku'] or '—',
            r['unidades'],
            r['n_pedidos'],
            ingresos,
            costo,
        ))
    return result


def _get_contenedores_vendidos(fecha_desde, fecha_hasta, limit=10):
    qs = (
        ItemPedido.objects
        .filter(
            variante__isnull=True,
            item_padre__isnull=True,
            pedido__fecha_creacion__date__gte=fecha_desde,
            pedido__fecha_creacion__date__lte=fecha_hasta,
        )
        .exclude(descripcion__isnull=True)
        .values('descripcion')
        .annotate(
            unidades=Sum('cantidad'),
            n_pedidos=Count('pedido', distinct=True),
        )
        .order_by('-unidades')[:limit]
    )
    return [(r['descripcion'], r['unidades'], r['n_pedidos']) for r in qs]


# ══════════════════════════════════════════════════════════════════
# Materiales mas utilizados
# ══════════════════════════════════════════════════════════════════
def _get_materiales_usados(fecha_desde, fecha_hasta, limit=15):
    """
    Materiales más consumidos dentro de pedidos en el período.
    Suma gramos de ítems componentes y de ítems personalizados simples.
    """
    qs = (
        ItemPedido.objects
        .filter(
            material_personalizado__isnull=False,
            pedido__fecha_creacion__date__gte=fecha_desde,
            pedido__fecha_creacion__date__lte=fecha_hasta,
        )
        .values(
            'material_personalizado__tipo__nombre',
            'material_personalizado__color__nombre',
            'material_personalizado__marca__nombre',
            'material_personalizado__costo_por_gramo',
        )
        .annotate(
            gramos_total=Sum(F('gramos_por_unidad') * F('cantidad')),
            veces_usado=Count('id'),
        )
        .order_by('-gramos_total')[:limit]
    )
 
    result = []
    for r in qs:
        gramos = float(r['gramos_total'] or 0)
        cxg = float(r['material_personalizado__costo_por_gramo'] or 0)
        result.append((
            r['material_personalizado__tipo__nombre'],
            r['material_personalizado__color__nombre'],
            r['material_personalizado__marca__nombre'],
            gramos,
            r['veces_usado'],
            cxg,
        ))
    return result


def _get_rentabilidad_pedidos(fecha_desde, fecha_hasta, limit=50):
    pedidos = (
        Pedido.objects
        .filter(
            fecha_creacion__date__gte=fecha_desde,
            fecha_creacion__date__lte=fecha_hasta,
        )
        .prefetch_related('pagos')
        .order_by('-precio_total')[:limit]
    )

    result = []
    for p in pedidos:
        costo = float(p.costo_total_produccion)
        precio = float(p.precio_total)
        ganancia = precio - costo
        margen = (ganancia / precio * 100) if precio > 0 else 0
        result.append((
            p.id,
            p.fecha_creacion.strftime('%d/%m/%Y'),
            p.nombre_cliente,
            p.get_estado_pedido_display(),
            precio,
            costo,
            margen,
        ))
    return result


def _get_clientes_frecuentes(fecha_desde, fecha_hasta, limit=20):
    from django.db.models import Max

    qs = (
        Pedido.objects
        .filter(
            usuario__isnull=False,
            fecha_creacion__date__gte=fecha_desde,
            fecha_creacion__date__lte=fecha_hasta,
        )
        .values('usuario__id', 'usuario__first_name', 'usuario__last_name', 'usuario__email')
        .annotate(
            n_pedidos=Count('id'),
            total_gastado=Sum('precio_total'),
            ultimo_pedido=Max('fecha_creacion'),
        )
        .order_by('-n_pedidos')[:limit]
    )

    result = []
    for r in qs:
        nombre = f"{r['usuario__first_name']} {r['usuario__last_name']}".strip() or r['usuario__email']
        ultimo_dt = r['ultimo_pedido']
        ultimo_str = ultimo_dt.strftime('%d/%m/%Y') if ultimo_dt else '—'

        metodo_qs = (
            Pago.objects
            .filter(
                pedido__usuario_id=r['usuario__id'],
                fecha_pago__date__gte=fecha_desde,
                fecha_pago__date__lte=fecha_hasta,
            )
            .values('metodo')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')
            .first()
        )
        metodo = metodo_qs['metodo'] if metodo_qs else '—'

        result.append((
            nombre,
            r['usuario__email'],
            r['n_pedidos'],
            float(r['total_gastado'] or 0),
            ultimo_str,
            metodo,
        ))
    return result


def _get_productos_bajo_movimiento(fecha_desde, fecha_hasta):
    from apps.productos.models import VarianteProducto

    todas_variantes = VarianteProducto.objects.filter(activa=True).select_related('producto')

    vendidas = dict(
        ItemPedido.objects
        .filter(
            variante__isnull=False,
            item_padre__isnull=True,
            pedido__fecha_creacion__date__gte=fecha_desde,
            pedido__fecha_creacion__date__lte=fecha_hasta,
        )
        .values('variante_id')
        .annotate(total=Sum('cantidad'))
        .values_list('variante_id', 'total')
    )

    result = []
    for v in todas_variantes:
        unidades = vendidas.get(v.id, 0)
        if unidades <= 3:
            ingresos = float(v.precio_final * unidades)
            result.append((
                v.producto.nombre,
                str(v),
                unidades,
                ingresos,
                v.stock_disponible,
            ))

    result.sort(key=lambda x: x[2])
    return result[:15]


# ══════════════════════════════════════════════════════════════════
# NUEVA QUERY: Pérdidas de material por período
# ══════════════════════════════════════════════════════════════════
def _get_perdidas_material(fecha_desde, fecha_hasta, limit=20):
    """
    Detalle de pérdidas de material registradas en el período.
    Incluye: material, gramos perdidos, motivo, pedido asociado.
    """
    qs = (
        PerdidaMaterial.objects
        .filter(
            fecha__date__gte=fecha_desde,
            fecha__date__lte=fecha_hasta,
        )
        .select_related('material__tipo', 'material__color', 'material__marca', 'pedido')
        .order_by('-fecha')[:limit]
    )

    result = []
    for p in qs:
        costo_perdida = float(p.gramos_perdidos * p.material.costo_por_gramo)
        result.append((
            p.fecha.strftime('%d/%m/%Y'),
            f'#{p.pedido.id:04d}' if p.pedido else '—',
            p.material.tipo.nombre,
            p.material.color.nombre,
            float(p.gramos_perdidos),
            costo_perdida,
            p.motivo or '—',
        ))
    return result


# ══════════════════════════════════════════════════════════════════
# NUEVA QUERY: KPIs operativos para hoja Operativo
# ══════════════════════════════════════════════════════════════════
def _get_datos_operativos(fecha_desde, fecha_hasta, limit=50):
    """
    Datos para la hoja de Desempeño Operativo del reporte ejecutivo.
    """
    pedidos = (
        Pedido.objects
        .filter(
            fecha_creacion__date__gte=fecha_desde,
            fecha_creacion__date__lte=fecha_hasta,
        )
        .select_related('usuario')
        .order_by('-fecha_creacion')[:limit]
    )

    result = []
    for p in pedidos:
        # Tiempo desde creación hasta inicio de producción
        tiempo_respuesta = None
        if p.fecha_inicio_produccion:
            delta = p.fecha_inicio_produccion - p.fecha_creacion
            tiempo_respuesta = round(delta.total_seconds() / 3600, 1)

        # Tiempo de producción (inicio → entrega)
        tiempo_produccion = None
        if p.fecha_inicio_produccion and p.fecha_entrega:
            delta = p.fecha_entrega - p.fecha_inicio_produccion
            tiempo_produccion = round(delta.total_seconds() / 3600, 1)

        result.append((
            p.id,
            p.fecha_creacion.strftime('%d/%m/%Y'),
            p.nombre_cliente,
            p.get_estado_pedido_display(),
            tiempo_respuesta,   # horas hasta iniciar producción
            tiempo_produccion,  # horas de producción
            p.fecha_entrega.strftime('%d/%m/%Y') if p.fecha_entrega else '—',
        ))
    return result


# ═══════════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DEL WORKBOOK
# ═══════════════════════════════════════════════════════════════════

def _build_hoja_resumen(ws, kpis, estados, metodos, periodo):
    ws.sheet_view.showGridLines = False
    _titulo_hoja(ws, 'A.N.T Studio — Reporte Ejecutivo',
                 'Dashboard de métricas clave del negocio', 8, periodo)

    kpi1 = [
        ('INGRESOS DEL MES',  kpis['ingresos'],         '#,##0.00', C['accent_blue']),
        ('GASTOS DEL MES',    kpis['gastos'],            '#,##0.00', C['accent_red']),
        ('GANANCIA NETA',     kpis['ganancia'],          '#,##0.00', C['accent']),
        ('MARGEN %',          kpis['margen'] / 100,     '0.0%',     C['accent']),
    ]
    for i, (lbl, val, fmt, col_c) in enumerate(kpi1):
        _kpi_card(ws, 5, i + 1, lbl, val, fmt, col_c)

    kpi2 = [
        ('PEDIDOS TOTALES',   kpis['pedidos_total'],      '#,##0',     C['accent_blue']),
        ('ENTREGADOS',        kpis['pedidos_entregados'], '#,##0',     C['accent']),
        ('TICKET PROMEDIO',   kpis['ticket_promedio'],    '#,##0.00',  C['accent_amber']),
        ('CLIENTES ACTIVOS',  kpis['clientes_activos'],   '#,##0',     C['accent_purple']),
    ]
    for i, (lbl, val, fmt, col_c) in enumerate(kpi2):
        _kpi_card(ws, 8, i + 1, lbl, val, fmt, col_c)

    for col in range(1, 9):
        ws.cell(row=11, column=col).fill = _fill(C['accent_dark'])
    ws.row_dimensions[11].height = 3

    ws.merge_cells('A12:D12')
    c = ws.cell(row=12, column=1, value='DISTRIBUCIÓN POR ESTADO')
    c.font = _font(bold=True, color=C['accent_amber'], size=11)
    c.fill = _fill(C['bg_dark'])
    ws.row_dimensions[12].height = 20

    _header_row(ws, 13, ['Estado', 'Pedidos', 'Distribución %', ''])
    ws.cell(row=13, column=4).fill = _fill(C['bg_card'])
    ws.cell(row=13, column=4).border = _border()

    total_estados = sum(r[1] for r in estados) or 1
    for i, (estado, cnt, color_e) in enumerate(estados):
        row = 14 + i
        alt = (i % 2 == 0)
        bg = C['row_alt'] if alt else C['row_normal']

        for col in range(1, 5):
            ws.cell(row=row, column=col).fill = _fill(bg)
            ws.cell(row=row, column=col).border = _border()

        c1 = ws.cell(row=row, column=1, value=estado)
        c1.font = _font(bold=True, color=color_e)
        c1.fill = _fill(bg)

        c2 = ws.cell(row=row, column=2, value=cnt)
        c2.font = _font(color=C['gray_light'])
        c2.fill = _fill(bg)
        c2.alignment = _align('center')

        c3 = ws.cell(row=row, column=3, value=cnt / total_estados)
        c3.font = _font(color=C['gray_light'])
        c3.fill = _fill(bg)
        c3.number_format = '0.0%'
        c3.alignment = _align('right')
        ws.row_dimensions[row].height = 18

    ws.merge_cells('E12:H12')
    c = ws.cell(row=12, column=5, value='MÉTODOS DE PAGO')
    c.font = _font(bold=True, color=C['accent_blue'], size=11)
    c.fill = _fill(C['bg_dark'])

    metodo_headers = ['Método', 'N° Pagos', 'Total (RD$)', '% del Total']
    for hi, hv in enumerate(metodo_headers, 5):
        ch = ws.cell(row=13, column=hi, value=hv)
        ch.font = _font(bold=True)
        ch.fill = _fill(C['bg_card'])
        ch.border = _border()
        ch.alignment = _align('center')

    for i, (metodo, n_pagos, total, pct) in enumerate(metodos):
        row = 14 + i
        alt = (i % 2 == 0)
        bg = C['row_alt'] if alt else C['row_normal']
        vals = [metodo, n_pagos, total, pct / 100]
        for col_off, val in enumerate(vals):
            c = ws.cell(row=row, column=5 + col_off, value=val)
            c.fill = _fill(bg)
            c.font = _font(color=C['gray_light'])
            c.border = _border()
            c.alignment = _align('right' if col_off >= 2 else 'left')
        ws.cell(row=row, column=7).number_format = '#,##0.00'
        ws.cell(row=row, column=8).number_format = '0.0%'
        ws.row_dimensions[row].height = 18

    _set_col_widths(ws, [22, 14, 16, 14, 20, 12, 18, 14])


def _build_hoja_productos(ws, datos_catalogo, datos_contenedores, periodo):
    ws.sheet_view.showGridLines = False
    n_cols = 8
    _titulo_hoja(ws, 'Productos mas vendidos',
                 'Ranking por unidades vendidas en el periodo', n_cols, periodo)

    ws.merge_cells(f'A5:{get_column_letter(n_cols)}5')
    c = ws.cell(row=5, column=1, value='PRODUCTOS DEL CATALOGO')
    c.font = _font(bold=True, color=C['accent_blue'], size=11)
    c.fill = _fill(C['bg_dark'])
    ws.row_dimensions[5].height = 20

    headers = ['#', 'Producto', 'SKU', 'Unidades', 'Pedidos', 'Ingresos (RD$)', 'Costo Est. (RD$)', 'Ganancia (RD$)']
    _header_row(ws, 6, headers)
    ws.row_dimensions[6].height = 24
    ws.freeze_panes = 'A7'

    data_start = 7
    if datos_catalogo:
        for i, (nombre, sku, unidades, n_pedidos, ingresos, costo) in enumerate(datos_catalogo):
            row = data_start + i
            alt = (i % 2 == 0)
            bg = C['row_alt'] if alt else C['row_normal']

            vals = [i + 1, nombre, sku, unidades, n_pedidos, ingresos, costo, f'=F{row}-G{row}']
            for col, val in enumerate(vals, 1):
                c = ws.cell(row=row, column=col, value=val)
                c.fill = _fill(bg)
                c.border = _border()
                c.alignment = _align()
                if col == 1:
                    c.font = _font(bold=True, color=C['accent_amber'])
                    c.alignment = _align('center')
                elif col == 2:
                    c.font = _font(bold=True, color='FFFFFF')
                elif col == 8:
                    c.font = _font(bold=True, color=C['accent'])
                    c.number_format = '#,##0.00'
                    c.alignment = _align('right')
                elif col in (4, 5):
                    c.font = _font(color=C['gray_light'])
                    c.alignment = _align('center')
                elif col in (6, 7):
                    c.font = _font(color=C['gray_light'])
                    c.number_format = '#,##0.00'
                    c.alignment = _align('right')
                else:
                    c.font = _font(color=C['gray_light'])
            ws.row_dimensions[row].height = 20

        tr_cat = data_start + len(datos_catalogo)
        _fila_totales(ws, tr_cat, n_cols, 3, [
            (4, f'=SUM(D{data_start}:D{tr_cat-1})', '#,##0'),
            (6, f'=SUM(F{data_start}:F{tr_cat-1})', '#,##0.00'),
            (7, f'=SUM(G{data_start}:G{tr_cat-1})', '#,##0.00'),
            (8, f'=SUM(H{data_start}:H{tr_cat-1})', '#,##0.00'),
        ], 'SUBTOTAL CATALOGO')
        ws.auto_filter.ref = f'A6:{get_column_letter(n_cols)}{tr_cat - 1}'
    else:
        _fila_sin_datos(ws, data_start, n_cols, 'Sin ventas de catalogo en el periodo.')
        tr_cat = data_start + 1

    sec_row = tr_cat + 2
    ws.merge_cells(f'A{sec_row}:{get_column_letter(n_cols)}{sec_row}')
    c = ws.cell(row=sec_row, column=1, value='PRODUCTOS PERSONALIZADOS (CONTENEDORES)')
    c.font = _font(bold=True, color=C['accent_purple'], size=11)
    c.fill = _fill(C['bg_dark'])
    ws.row_dimensions[sec_row].height = 20

    hdr_row_cont = sec_row + 1
    _header_row(ws, hdr_row_cont, ['#', 'Descripcion del Producto', '', 'Unidades', 'Pedidos', '', '', ''])
    ws.row_dimensions[hdr_row_cont].height = 22

    ds_cont = hdr_row_cont + 1
    if datos_contenedores:
        for i, (descripcion, unidades, n_pedidos) in enumerate(datos_contenedores):
            row = ds_cont + i
            alt = (i % 2 == 0)
            bg = C['row_alt'] if alt else C['row_normal']
            for col in range(1, n_cols + 1):
                ws.cell(row=row, column=col).fill = _fill(bg)
                ws.cell(row=row, column=col).border = _border()

            ws.cell(row=row, column=1).value = i + 1
            ws.cell(row=row, column=1).font = _font(bold=True, color=C['accent_purple'])
            ws.cell(row=row, column=1).alignment = _align('center')
            ws.merge_cells(f'B{row}:C{row}')
            ws.cell(row=row, column=2).value = descripcion
            ws.cell(row=row, column=2).font = _font(bold=True, color='FFFFFF')
            ws.cell(row=row, column=4).value = unidades
            ws.cell(row=row, column=4).font = _font(color=C['gray_light'])
            ws.cell(row=row, column=4).alignment = _align('center')
            ws.cell(row=row, column=5).value = n_pedidos
            ws.cell(row=row, column=5).font = _font(color=C['gray_light'])
            ws.cell(row=row, column=5).alignment = _align('center')
            ws.row_dimensions[row].height = 20
    else:
        _fila_sin_datos(ws, ds_cont, n_cols, 'Sin productos personalizados en el periodo.')

    _set_col_widths(ws, [5, 30, 18, 12, 10, 18, 18, 18])

    nota_row = ds_cont + max(len(datos_contenedores), 1) + 1
    ws.merge_cells(f'A{nota_row}:{get_column_letter(n_cols)}{nota_row}')
    c = ws.cell(row=nota_row, column=1,
                value='* Costo estimado = costo de materiales de la variante x cantidad. Ganancia = Ingresos - Costo estimado.')
    c.font = _font(italic=True, color=C['gray_mid'], size=8)
    c.fill = _fill(C['bg_dark'])


def _build_hoja_materiales(ws, datos, periodo):
    ws.sheet_view.showGridLines = False
    n_cols = 8
    _titulo_hoja(ws, 'Materiales mas utilizados',
                 'Consumo real en pedidos del periodo analizado', n_cols, periodo)
 
    headers = ['#', 'Tipo', 'Color', 'Marca', 'Gramos consumidos', 'Veces usado', 'Costo/g (RD$)', 'Costo total (RD$)']
    _header_row(ws, 5, headers)
    ws.row_dimensions[5].height = 24
    ws.freeze_panes = 'A6'
 
    data_start = 6
    if datos:
        for i, (tipo, color, marca, gramos, veces, cxg) in enumerate(datos):
            row = data_start + i
            alt = (i % 2 == 0)
            bg = C['row_alt'] if alt else C['row_normal']
 
            vals = [i + 1, tipo, color, marca, gramos, veces, cxg, f'=E{row}*G{row}']
            for col, val in enumerate(vals, 1):
                c = ws.cell(row=row, column=col, value=val)
                c.fill = _fill(bg)
                c.border = _border()
                c.alignment = _align()
                if col == 1:
                    c.font = _font(bold=True, color=C['accent_amber'])
                    c.alignment = _align('center')
                elif col == 2:
                    c.font = _font(bold=True, color='FFFFFF')
                elif col == 5:
                    c.font = _font(color=C['gray_light'])
                    c.number_format = '#,##0.00'
                    c.alignment = _align('right')
                elif col == 6:
                    c.font = _font(color=C['gray_light'])
                    c.number_format = '#,##0'
                    c.alignment = _align('center')
                elif col == 7:
                    c.font = _font(color=C['gray_light'])
                    c.number_format = '#,##0.0000'
                    c.alignment = _align('right')
                elif col == 8:
                    c.font = _font(bold=True, color=C['accent'])
                    c.number_format = '#,##0.00'
                    c.alignment = _align('right')
                else:
                    c.font = _font(color=C['gray_light'])
            ws.row_dimensions[row].height = 20
 
        tr = data_start + len(datos)
        ws.auto_filter.ref = f'A5:{get_column_letter(n_cols)}{tr - 1}'
        _fila_totales(ws, tr, n_cols, 4, [
            (5, f'=SUM(E{data_start}:E{tr-1})', '#,##0.00'),
            (6, f'=SUM(F{data_start}:F{tr-1})', '#,##0'),
            (8, f'=SUM(H{data_start}:H{tr-1})', '#,##0.00'),
        ])
        ws.cell(row=tr, column=7).fill = _fill(C['bg_dark'])
        ws.cell(row=tr, column=7).border = _border()
    else:
        _fila_sin_datos(ws, data_start, n_cols, 'Sin consumo de materiales registrado en el periodo.')
 
    _set_col_widths(ws, [5, 14, 16, 16, 20, 14, 16, 20])


def _build_hoja_rentabilidad(ws, datos, periodo):
    ws.sheet_view.showGridLines = False
    n_cols = 8
    _titulo_hoja(ws, 'Rentabilidad por Pedido',
                 'Analisis de ingresos, costos y margenes por pedido', n_cols, periodo)

    headers = ['# Pedido', 'Fecha', 'Cliente', 'Estado', 'Ingresos (RD$)', 'Costo Est. (RD$)', 'Ganancia (RD$)', 'Margen %']
    _header_row(ws, 5, headers)
    ws.row_dimensions[5].height = 24
    ws.freeze_panes = 'A6'

    data_start = 6
    if datos:
        for i, (pid, fecha, cliente, estado, precio, costo, margen) in enumerate(datos):
            row = data_start + i
            alt = (i % 2 == 0)
            bg = C['row_alt'] if alt else C['row_normal']

            for col in range(1, n_cols + 1):
                ws.cell(row=row, column=col).fill = _fill(bg)
                ws.cell(row=row, column=col).border = _border()

            ws.cell(row=row, column=1).value = f'#{pid:04d}'
            ws.cell(row=row, column=1).font = _font(bold=True, color=C['accent_blue'])
            ws.cell(row=row, column=1).alignment = _align('center')
            ws.cell(row=row, column=2).value = fecha
            ws.cell(row=row, column=2).font = _font(color=C['gray_light'])
            ws.cell(row=row, column=2).alignment = _align('center')
            ws.cell(row=row, column=3).value = cliente
            ws.cell(row=row, column=3).font = _font(bold=True, color='FFFFFF')
            ws.cell(row=row, column=4).value = estado
            ws.cell(row=row, column=4).font = _font(color=C['gray_mid'], italic=True)
            ws.cell(row=row, column=4).alignment = _align('center')
            ws.cell(row=row, column=5).value = precio
            ws.cell(row=row, column=5).font = _font(color=C['gray_light'])
            ws.cell(row=row, column=5).number_format = '#,##0.00'
            ws.cell(row=row, column=5).alignment = _align('right')
            ws.cell(row=row, column=6).value = costo
            ws.cell(row=row, column=6).font = _font(color=C['gray_light'])
            ws.cell(row=row, column=6).number_format = '#,##0.00'
            ws.cell(row=row, column=6).alignment = _align('right')
            ws.cell(row=row, column=7).value = f'=E{row}-F{row}'
            ws.cell(row=row, column=7).font = _font(bold=True, color=C['accent'])
            ws.cell(row=row, column=7).number_format = '#,##0.00'
            ws.cell(row=row, column=7).alignment = _align('right')
            ws.cell(row=row, column=8).value = f'=IFERROR(G{row}/E{row},0)'
            ws.cell(row=row, column=8).number_format = '0.0%'
            ws.cell(row=row, column=8).alignment = _align('right')
            if margen >= 50:
                ws.cell(row=row, column=8).font = _font(bold=True, color=C['accent'])
            elif margen >= 30:
                ws.cell(row=row, column=8).font = _font(bold=True, color=C['accent_amber'])
            else:
                ws.cell(row=row, column=8).font = _font(bold=True, color=C['accent_red'])

            ws.row_dimensions[row].height = 20

        tr = data_start + len(datos)
        ws.auto_filter.ref = f'A5:{get_column_letter(n_cols)}{tr - 1}'
        _fila_totales(ws, tr, n_cols, 4, [
            (5, f'=SUM(E{data_start}:E{tr-1})', '#,##0.00'),
            (6, f'=SUM(F{data_start}:F{tr-1})', '#,##0.00'),
            (7, f'=SUM(G{data_start}:G{tr-1})', '#,##0.00'),
            (8, f'=IFERROR(AVERAGE(H{data_start}:H{tr-1}),0)', '0.0%'),
        ], 'TOTAL / MARGEN PROMEDIO')

        ley_row = tr + 2
        ws.merge_cells(f'A{ley_row}:H{ley_row}')
        c = ws.cell(row=ley_row, column=1,
                    value='Margen %: Verde >= 50%  |  Ambar 30-49%  |  Rojo < 30%')
        c.font = _font(italic=True, color=C['gray_mid'], size=8)
        c.fill = _fill(C['bg_dark'])
    else:
        _fila_sin_datos(ws, data_start, n_cols, 'Sin pedidos en el periodo seleccionado.')

    _set_col_widths(ws, [10, 13, 26, 20, 16, 16, 16, 12])


def _build_hoja_clientes(ws, datos, periodo):
    ws.sheet_view.showGridLines = False
    n_cols = 7
    _titulo_hoja(ws, 'Clientes más frecuentes',
                 'Ranking por cantidad de pedidos y volumen de gasto', n_cols, periodo)

    headers = ['#', 'Cliente', 'Email', 'N° Pedidos', 'Total gastado (RD$)', 'Último pedido', 'Método preferido']
    _header_row(ws, 5, headers)
    ws.row_dimensions[5].height = 24

    data_start = 6
    medallas = ['🥇', '🥈', '🥉']
    for i, (nombre, email, n_pedidos, total, ultimo, metodo) in enumerate(datos):
        row = data_start + i
        alt = (i % 2 == 0)
        bg = C['row_alt'] if alt else C['row_normal']

        for col in range(1, n_cols + 1):
            ws.cell(row=row, column=col).fill = _fill(bg)
            ws.cell(row=row, column=col).border = _border()

        num_label = medallas[i] if i < 3 else str(i + 1)
        ws.cell(row=row, column=1).value = num_label
        ws.cell(row=row, column=1).font = _font(bold=True, color=C['accent_amber'])
        ws.cell(row=row, column=1).alignment = _align('center')
        ws.cell(row=row, column=2).value = nombre
        ws.cell(row=row, column=2).font = _font(bold=True, color='FFFFFF')
        ws.cell(row=row, column=3).value = email
        ws.cell(row=row, column=3).font = _font(color=C['gray_mid'])
        ws.cell(row=row, column=4).value = n_pedidos
        ws.cell(row=row, column=4).font = _font(bold=True, color=C['accent_blue'])
        ws.cell(row=row, column=4).alignment = _align('center')
        ws.cell(row=row, column=5).value = total
        ws.cell(row=row, column=5).font = _font(bold=True, color=C['accent'])
        ws.cell(row=row, column=5).number_format = '#,##0.00'
        ws.cell(row=row, column=5).alignment = _align('right')
        ws.cell(row=row, column=6).value = ultimo
        ws.cell(row=row, column=6).font = _font(color=C['gray_light'])
        ws.cell(row=row, column=6).alignment = _align('center')
        ws.cell(row=row, column=7).value = metodo
        ws.cell(row=row, column=7).font = _font(color=C['gray_light'])
        ws.cell(row=row, column=7).alignment = _align('center')
        ws.row_dimensions[row].height = 20

    tr = data_start + len(datos)
    if datos:
        _fila_totales(ws, tr, n_cols, 3, [
            (4, f'=SUM(D{data_start}:D{tr-1})', '#,##0'),
            (5, f'=SUM(E{data_start}:E{tr-1})', '#,##0.00'),
        ])
    else:
        _fila_sin_datos(ws, tr, n_cols)

    _set_col_widths(ws, [6, 26, 26, 12, 20, 14, 18])


def _build_hoja_bajo_movimiento(ws, datos, periodo):
    ws.sheet_view.showGridLines = False
    n_cols = 5
    _titulo_hoja(ws, 'Productos con bajo movimiento',
                 'Items con poca salida — menos de 4 unidades vendidas en el periodo', n_cols, periodo)

    headers = ['#', 'Producto', 'Variante', 'Unidades vendidas', 'Stock disponible']
    _header_row(ws, 5, headers, bg='3F1212')
    ws.row_dimensions[5].height = 24
    ws.freeze_panes = 'A6'

    data_start = 6
    if datos:
        for i, (nombre, variante, unidades, ingresos, stock) in enumerate(datos):
            row = data_start + i
            alt = (i % 2 == 0)
            bg = '1F0A0A' if alt else '2A0E0E'

            for col in range(1, n_cols + 1):
                ws.cell(row=row, column=col).fill = _fill(bg)
                ws.cell(row=row, column=col).border = _border('3F1212')

            ws.cell(row=row, column=1).value = i + 1
            ws.cell(row=row, column=1).font = _font(bold=True, color=C['accent_red'])
            ws.cell(row=row, column=1).alignment = _align('center')
            ws.cell(row=row, column=2).value = nombre
            ws.cell(row=row, column=2).font = _font(bold=True, color='FFAAAA')
            ws.cell(row=row, column=3).value = variante
            ws.cell(row=row, column=3).font = _font(color='FCA5A5')
            ws.cell(row=row, column=4).value = unidades
            ws.cell(row=row, column=4).font = _font(
                bold=True,
                color=C['accent_red'] if unidades == 0 else C['accent_amber']
            )
            ws.cell(row=row, column=4).alignment = _align('center')
            ws.cell(row=row, column=4).number_format = '#,##0'
            ws.cell(row=row, column=5).value = stock
            ws.cell(row=row, column=5).font = _font(color='FCA5A5')
            ws.cell(row=row, column=5).alignment = _align('center')
            ws.cell(row=row, column=5).number_format = '#,##0'
            ws.row_dimensions[row].height = 20

        ws.auto_filter.ref = f'A5:{get_column_letter(n_cols)}{data_start + len(datos) - 1}'
        nota_row = data_start + len(datos) + 2
    else:
        _fila_sin_datos(ws, data_start, n_cols, 'Todos los productos tienen buena rotacion en el periodo.')
        nota_row = data_start + 3

    ws.merge_cells(f'A{nota_row}:{get_column_letter(n_cols)}{nota_row}')
    c = ws.cell(row=nota_row, column=1,
                value='Productos con 3 unidades o menos vendidas. Revisar precio, visibilidad en catalogo o discontinuar.')
    c.font = _font(italic=True, color=C['accent_red'], size=8)
    c.fill = _fill(C['bg_dark'])

    _set_col_widths(ws, [5, 30, 28, 18, 18])


# ══════════════════════════════════════════════════════════════════
# NUEVA HOJA: Desempeño Operativo
# ══════════════════════════════════════════════════════════════════
def _build_hoja_operativo(ws, datos, periodo):
    """
    Hoja de desempeño operativo: tiempos de respuesta y producción por pedido.
    """
    ws.sheet_view.showGridLines = False
    n_cols = 7
    _titulo_hoja(ws, 'Desempeño Operativo del Taller',
                 'Tiempos de respuesta y producción por pedido', n_cols, periodo)

    # Nota explicativa
    ws.merge_cells(f'A5:{get_column_letter(n_cols)}5')
    c = ws.cell(row=5, column=1,
                value='Tiempo de respuesta = horas desde solicitud hasta inicio de producción. '
                      'Tiempo producción = horas entre inicio y entrega. — = dato no registrado.')
    c.font = _font(italic=True, color=C['gray_mid'], size=8)
    c.fill = _fill(C['bg_dark'])
    c.border = _border()
    ws.row_dimensions[5].height = 16

    headers = ['# Pedido', 'Fecha solicitud', 'Cliente', 'Estado',
               'T. Respuesta (h)', 'T. Producción (h)', 'Fecha entrega']
    _header_row(ws, 6, headers)
    ws.row_dimensions[6].height = 24
    ws.freeze_panes = 'A7'

    data_start = 7
    if datos:
        tiempos_resp    = [d[4] for d in datos if d[4] is not None]
        tiempos_prod    = [d[5] for d in datos if d[5] is not None]

        for i, (pid, fecha, cliente, estado, t_resp, t_prod, f_entrega) in enumerate(datos):
            row = data_start + i
            alt = (i % 2 == 0)
            bg = C['row_alt'] if alt else C['row_normal']

            for col in range(1, n_cols + 1):
                ws.cell(row=row, column=col).fill = _fill(bg)
                ws.cell(row=row, column=col).border = _border()

            ws.cell(row=row, column=1).value = f'#{pid:04d}'
            ws.cell(row=row, column=1).font = _font(bold=True, color=C['accent_blue'])
            ws.cell(row=row, column=1).alignment = _align('center')

            ws.cell(row=row, column=2).value = fecha
            ws.cell(row=row, column=2).font = _font(color=C['gray_light'])
            ws.cell(row=row, column=2).alignment = _align('center')

            ws.cell(row=row, column=3).value = cliente
            ws.cell(row=row, column=3).font = _font(bold=True, color='FFFFFF')

            ws.cell(row=row, column=4).value = estado
            ws.cell(row=row, column=4).font = _font(color=C['gray_mid'], italic=True)
            ws.cell(row=row, column=4).alignment = _align('center')

            # Tiempo de respuesta — color según umbral (>24h = ámbar, >48h = rojo)
            resp_val = t_resp if t_resp is not None else '—'
            ws.cell(row=row, column=5).value = resp_val
            if t_resp is not None:
                ws.cell(row=row, column=5).number_format = '#,##0.0'
                ws.cell(row=row, column=5).alignment = _align('center')
                if t_resp > 48:
                    ws.cell(row=row, column=5).font = _font(bold=True, color=C['accent_red'])
                elif t_resp > 24:
                    ws.cell(row=row, column=5).font = _font(bold=True, color=C['accent_amber'])
                else:
                    ws.cell(row=row, column=5).font = _font(bold=True, color=C['accent'])
            else:
                ws.cell(row=row, column=5).font = _font(color=C['gray_mid'], italic=True)
                ws.cell(row=row, column=5).alignment = _align('center')

            # Tiempo de producción
            prod_val = t_prod if t_prod is not None else '—'
            ws.cell(row=row, column=6).value = prod_val
            if t_prod is not None:
                ws.cell(row=row, column=6).number_format = '#,##0.0'
                ws.cell(row=row, column=6).alignment = _align('center')
                ws.cell(row=row, column=6).font = _font(color=C['gray_light'])
            else:
                ws.cell(row=row, column=6).font = _font(color=C['gray_mid'], italic=True)
                ws.cell(row=row, column=6).alignment = _align('center')

            ws.cell(row=row, column=7).value = f_entrega
            ws.cell(row=row, column=7).font = _font(color=C['gray_light'])
            ws.cell(row=row, column=7).alignment = _align('center')

            ws.row_dimensions[row].height = 20

        tr = data_start + len(datos)
        ws.auto_filter.ref = f'A6:{get_column_letter(n_cols)}{tr - 1}'

        # Fila de promedios
        _fila_totales(ws, tr, n_cols, 4, [
            (5, f'=IFERROR(AVERAGEIF(E{data_start}:E{tr-1},"<>—"),0)', '#,##0.0'),
            (6, f'=IFERROR(AVERAGEIF(F{data_start}:F{tr-1},"<>—"),0)', '#,##0.0'),
        ], 'PROMEDIO (horas)')

        # Leyenda de colores
        ley_row = tr + 2
        ws.merge_cells(f'A{ley_row}:{get_column_letter(n_cols)}{ley_row}')
        c = ws.cell(row=ley_row, column=1,
                    value='T. Respuesta: Verde <= 24h  |  Ámbar 24-48h  |  Rojo > 48h')
        c.font = _font(italic=True, color=C['gray_mid'], size=8)
        c.fill = _fill(C['bg_dark'])
    else:
        _fila_sin_datos(ws, data_start, n_cols, 'Sin pedidos en el periodo seleccionado.')

    _set_col_widths(ws, [10, 14, 26, 20, 16, 18, 14])


# ══════════════════════════════════════════════════════════════════
# NUEVA HOJA: Pérdidas de Material
# ══════════════════════════════════════════════════════════════════
def _build_hoja_perdidas(ws, datos, periodo):
    """
    Hoja de pérdidas de material por fallos de impresión.
    """
    ws.sheet_view.showGridLines = False
    n_cols = 7
    _titulo_hoja(ws, 'Pérdidas de Material — Fallos de Impresión',
                 'Detalle de material perdido por errores de producción', n_cols, periodo)

    headers = ['Fecha', '# Pedido', 'Tipo Material', 'Color',
               'Gramos perdidos', 'Costo pérdida (RD$)', 'Motivo']
    _header_row(ws, 5, headers, bg='4A1515')
    ws.row_dimensions[5].height = 24
    ws.freeze_panes = 'A6'

    data_start = 6
    if datos:
        for i, (fecha, pedido_ref, tipo, color, gramos, costo, motivo) in enumerate(datos):
            row = data_start + i
            alt = (i % 2 == 0)
            bg = '1F0A0A' if alt else '2A0E0E'

            for col in range(1, n_cols + 1):
                ws.cell(row=row, column=col).fill = _fill(bg)
                ws.cell(row=row, column=col).border = _border('3F1212')

            ws.cell(row=row, column=1).value = fecha
            ws.cell(row=row, column=1).font = _font(color='FCA5A5')
            ws.cell(row=row, column=1).alignment = _align('center')

            ws.cell(row=row, column=2).value = pedido_ref
            ws.cell(row=row, column=2).font = _font(bold=True, color=C['accent_blue'])
            ws.cell(row=row, column=2).alignment = _align('center')

            ws.cell(row=row, column=3).value = tipo
            ws.cell(row=row, column=3).font = _font(bold=True, color='FFAAAA')

            ws.cell(row=row, column=4).value = color
            ws.cell(row=row, column=4).font = _font(color='FCA5A5')

            ws.cell(row=row, column=5).value = gramos
            ws.cell(row=row, column=5).font = _font(bold=True, color=C['accent_red'])
            ws.cell(row=row, column=5).number_format = '#,##0.00'
            ws.cell(row=row, column=5).alignment = _align('right')

            ws.cell(row=row, column=6).value = costo
            ws.cell(row=row, column=6).font = _font(bold=True, color=C['accent_amber'])
            ws.cell(row=row, column=6).number_format = '#,##0.00'
            ws.cell(row=row, column=6).alignment = _align('right')

            ws.cell(row=row, column=7).value = motivo
            ws.cell(row=row, column=7).font = _font(color=C['gray_mid'], italic=True)
            ws.cell(row=row, column=7).alignment = _align(wrap=True)

            ws.row_dimensions[row].height = 20

        tr = data_start + len(datos)
        ws.auto_filter.ref = f'A5:{get_column_letter(n_cols)}{tr - 1}'
        _fila_totales(ws, tr, n_cols, 4, [
            (5, f'=SUM(E{data_start}:E{tr-1})', '#,##0.00'),
            (6, f'=SUM(F{data_start}:F{tr-1})', '#,##0.00'),
        ], 'TOTAL PÉRDIDAS')
    else:
        _fila_sin_datos(ws, data_start, n_cols, 'Sin pérdidas de material registradas en el periodo. ✓')

    _set_col_widths(ws, [12, 10, 14, 14, 16, 18, 35])


# ═══════════════════════════════════════════════════════════════════
# VISTA DJANGO PRINCIPAL — REPORTE EJECUTIVO (ahora con 8 hojas)
# ═══════════════════════════════════════════════════════════════════

@admin_required
def exportar_reporte_ejecutivo(request):
    hoy = date.today()

    try:
        fecha_desde = date.fromisoformat(request.GET.get('desde', _inicio_mes(hoy).isoformat()))
        fecha_hasta = date.fromisoformat(request.GET.get('hasta', hoy.isoformat()))
    except ValueError:
        fecha_desde = _inicio_mes(hoy)
        fecha_hasta = hoy

    periodo = f"{fecha_desde.strftime('%d/%m/%Y')} — {fecha_hasta.strftime('%d/%m/%Y')}"

    # Recolectar datos
    kpis          = _get_kpis(fecha_desde, fecha_hasta)
    estados       = _get_estados_pedido(fecha_desde, fecha_hasta)
    metodos       = _get_metodos_pago(fecha_desde, fecha_hasta)
    prod_catalogo = _get_productos_vendidos(fecha_desde, fecha_hasta)
    prod_custom   = _get_contenedores_vendidos(fecha_desde, fecha_hasta)
    materiales    = _get_materiales_usados(fecha_desde, fecha_hasta)   # ← ahora usa ConsumoMaterial
    rentabilidad  = _get_rentabilidad_pedidos(fecha_desde, fecha_hasta)
    clientes      = _get_clientes_frecuentes(fecha_desde, fecha_hasta)
    bajo_mov      = _get_productos_bajo_movimiento(fecha_desde, fecha_hasta)
    operativo     = _get_datos_operativos(fecha_desde, fecha_hasta)    # ← NUEVO
    perdidas      = _get_perdidas_material(fecha_desde, fecha_hasta)   # ← NUEVO

    # Construir workbook
    wb = openpyxl.Workbook()

    ws1 = wb.active
    ws1.title = 'Resumen Ejecutivo'
    _build_hoja_resumen(ws1, kpis, estados, metodos, periodo)

    ws2 = wb.create_sheet('Productos Vendidos')
    _build_hoja_productos(ws2, prod_catalogo, prod_custom, periodo)

    ws3 = wb.create_sheet('Materiales Usados')
    _build_hoja_materiales(ws3, materiales, periodo)

    ws4 = wb.create_sheet('Rentabilidad')
    _build_hoja_rentabilidad(ws4, rentabilidad, periodo)

    ws5 = wb.create_sheet('Clientes Frecuentes')
    _build_hoja_clientes(ws5, clientes, periodo)

    ws6 = wb.create_sheet('Bajo Movimiento')
    _build_hoja_bajo_movimiento(ws6, bajo_mov, periodo)

    ws7 = wb.create_sheet('Desempeño Operativo')   # ← NUEVA hoja
    _build_hoja_operativo(ws7, operativo, periodo)

    ws8 = wb.create_sheet('Pérdidas de Material')  # ← NUEVA hoja
    _build_hoja_perdidas(ws8, perdidas, periodo)

    # Respuesta HTTP
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"reporte_ejecutivo_ANT_{fecha_desde.strftime('%Y%m%d')}_{fecha_hasta.strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response