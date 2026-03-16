"""
Vistas de Reportes y Analytics — A.N.T Studio
"""
import io
import json
from decimal import Decimal
from datetime import date, timedelta
from calendar import monthrange

from django.shortcuts import render
from django.db.models import Sum, Count, F
from django.http import HttpResponse

from apps.finanzas.models import Gasto
from apps.materiales.models import Material

from apps.usuarios.decorators import admin_required
from apps.pedidos.models import Pedido, ItemPedido, Pago, PerdidaMaterial, SolicitudCotizacion

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
    """Formatea Decimal → float con 2 decimales para JSON."""
    if valor is None:
        return 0.0
    return float(Decimal(str(valor)).quantize(Decimal("0.01")))

def _variacion(actual, anterior):
    """Retorna % de variación entre dos valores."""
    if not anterior:
        return None
    try:
        return round(((actual - anterior) / anterior) * 100, 1)
    except Exception:
        return None

def _rango_mes(offset_desde_hoy, hoy=None):
    """
    Devuelve (primer_dia, ultimo_dia) del mes que está `offset_desde_hoy`
    meses atrás respecto a `hoy`. offset=0 → mes actual, offset=1 → mes anterior, etc.
    """
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

    # ── 1. KPIs principales ──────────────────────────────────────
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

    # Saldo pendiente total (suma sobre todos los pedidos activos)
    pedidos_activos_qs = Pedido.objects.filter(
        estado_pedido__in=['En_Espera', 'Confirmado', 'En_Produccion', 'Listo']
    ).prefetch_related('pagos')
    saldo_pendiente_total = sum(p.saldo_pendiente for p in pedidos_activos_qs)

    # Pedidos del mes
    pedidos_mes = Pedido.objects.filter(
        fecha_creacion__date__gte=inicio_mes
    ).count()
    pedidos_ant_cnt = Pedido.objects.filter(
        fecha_creacion__date__gte=inicio_ant,
        fecha_creacion__date__lte=fin_ant,
    ).count()

    # Materiales críticos (por debajo del stock mínimo)
    materiales_criticos = Material.objects.filter(
        activo=True, stock_actual__lte=F('stock_minimo')
    ).count()

    # Pérdidas de material este mes
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

    # ── 2. Distribución de pedidos por estado ────────────────────
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

    # ── 3. Ingresos vs Gastos — últimos 6 meses ──────────────────
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

    # ── 4. Top 5 productos más vendidos (por unidades) ───────────
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

    # ── 5. Top 5 contenedores más vendidos ───────────────────────
    top_contenedores = (
        ItemPedido.objects
        .filter(variante__isnull=True, item_padre__isnull=True)
        .values('descripcion')
        .annotate(unidades=Sum('cantidad'))
        .order_by('-unidades')[:5]
    )

    # ── 6. Materiales con stock bajo ─────────────────────────────
    todos_materiales = Material.objects.filter(activo=True).select_related('tipo', 'color', 'marca')
    materiales_bajos = (
        Material.objects
        .filter(activo=True, stock_actual__lte=F('stock_minimo'))
        .select_related('tipo', 'color', 'marca')
        .order_by('stock_actual')[:5]
    )
    total_gramos = todos_materiales.aggregate(t=Sum('stock_actual'))['t'] or 0
    total_kg     = float(total_gramos) / 1000

    # ── 7. Últimos 5 pedidos ─────────────────────────────────────
    ultimos_pedidos = (
        Pedido.objects
        .select_related('usuario')
        .order_by('-fecha_creacion')[:5]
    )

    # ── 8. Gastos por categoría (mes actual) ─────────────────────
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

    # ── 9. Resumen de impresoras ─────────────────────────────────
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
        # Charts como JSON para el JS del template
        'estados_chart_json':         json.dumps(estados_chart),
        'chart_ingresos_gastos_json': json.dumps(chart_ingresos_gastos),
        'gastos_cat_chart_json':      json.dumps(gastos_cat_chart),
        # Tablas
        'top_productos':    top_productos,
        'top_contenedores': top_contenedores,
        'materiales_bajos': materiales_bajos,
        'total_kg':         total_kg,
        'ultimos_pedidos':  ultimos_pedidos,
        'impresoras_stats': impresoras_stats,
        'mostrar_recordatorio_reporte': mostrar_recordatorio_reporte,
        'mes_anterior_label': f"{NOMBRES_MES[inicio_ant.month - 1]} {inicio_ant.year}",
        'fin_ant': fin_ant,
        'inicio_ant': inicio_ant,
    }
    return render(request, 'reportes/dashboard.html', context)


# ═══════════════════════════════════════════════════════════════════
# VISTA — REPORTE DE VENTAS (RANGO PERSONALIZADO)
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

    filtro_estado = request.GET.get('estado', '')   # 'critico' | 'ok' | ''
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

    # Totales sobre todos los materiales activos (sin filtros de estado/tipo)
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
# VISTA — EXPORT EXCEL VENTAS
# ═══════════════════════════════════════════════════════════════════

@admin_required
def exportar_ventas_excel(request):
    """
    Genera un .xlsx con los pagos del período seleccionado.
    Mismos parámetros GET que reporte_ventas: ?desde=&hasta=
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

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

    # ── Crear libro ──────────────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ventas"

    COLOR_HEADER  = "0F172A"
    COLOR_ACCENT  = "10B981"
    COLOR_ROW_ALT = "1E293B"
    COLOR_WHITE   = "FFFFFF"
    COLOR_TEXT    = "E2E8F0"

    def _fill(hex_color):
        return PatternFill("solid", fgColor=hex_color)

    def _font(bold=False, color=COLOR_WHITE, size=10):
        return Font(bold=bold, color=color, size=size, name="Calibri")

    def _border():
        s = Side(style='thin', color="334155")
        return Border(left=s, right=s, top=s, bottom=s)

    # Fila 1: Título
    ws.merge_cells("A1:G1")
    ws["A1"] = "A.N.T Studio — Reporte de Ventas"
    ws["A1"].font      = _font(bold=True, color=COLOR_ACCENT, size=14)
    ws["A1"].fill      = _fill(COLOR_HEADER)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # Fila 2: Período
    ws.merge_cells("A2:G2")
    ws["A2"] = (
        f"Período: {fecha_desde.strftime('%d/%m/%Y')} — {fecha_hasta.strftime('%d/%m/%Y')}"
        f"   |   Generado: {hoy.strftime('%d/%m/%Y')}"
    )
    ws["A2"].font      = _font(color="94A3B8", size=9)
    ws["A2"].fill      = _fill(COLOR_HEADER)
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 18

    # Fila 3: espacio
    ws.row_dimensions[3].height = 8
    for col in range(1, 8):
        ws.cell(row=3, column=col).fill = _fill(COLOR_HEADER)

    # Fila 4: Encabezados
    HEADERS    = ["# Pedido", "Cliente", "Email", "Método de Pago", "Referencia", "Fecha", "Monto (RD$)"]
    COL_WIDTHS = [12, 28, 30, 18, 22, 16, 16]

    for i, (header, width) in enumerate(zip(HEADERS, COL_WIDTHS), start=1):
        cell = ws.cell(row=4, column=i, value=header)
        cell.font      = _font(bold=True, color=COLOR_WHITE, size=10)
        cell.fill      = _fill("1E3A5F")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border    = _border()
        ws.column_dimensions[get_column_letter(i)].width = width

    ws.row_dimensions[4].height = 22

    # Filas de datos
    total = Decimal("0")
    for row_idx, pago in enumerate(pagos, start=5):
        alt = (row_idx % 2 == 0)
        bg  = _fill(COLOR_ROW_ALT if alt else "162032")

        valores = [
            f"#{pago.pedido.id:04d}",
            pago.pedido.nombre_cliente,
            pago.pedido.email_cliente,
            pago.get_metodo_display(),
            pago.referencia or "—",
            pago.fecha_pago.strftime("%d/%m/%Y %H:%M"),
            float(pago.monto),
        ]
        for col_idx, valor in enumerate(valores, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=valor)
            cell.fill      = bg
            cell.border    = _border()
            cell.font      = _font(color=COLOR_TEXT)
            cell.alignment = Alignment(vertical="center")
            if col_idx == 7:
                cell.number_format = '#,##0.00'
                cell.alignment     = Alignment(horizontal="right", vertical="center")
            elif col_idx == 1:
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font      = _font(bold=True, color=COLOR_ACCENT)

        total += pago.monto
        ws.row_dimensions[row_idx].height = 18

    # Fila de Total
    total_row = len(pagos) + 5
    ws.merge_cells(f"A{total_row}:F{total_row}")
    ws.cell(row=total_row, column=1, value="TOTAL RECAUDADO").font = _font(bold=True, color=COLOR_ACCENT, size=11)
    ws.cell(row=total_row, column=1).fill      = _fill(COLOR_HEADER)
    ws.cell(row=total_row, column=1).alignment = Alignment(horizontal="right", vertical="center")
    ws.cell(row=total_row, column=1).border    = _border()

    total_cell = ws.cell(row=total_row, column=7, value=float(total))
    total_cell.font          = _font(bold=True, color=COLOR_ACCENT, size=12)
    total_cell.fill          = _fill(COLOR_HEADER)
    total_cell.number_format = '#,##0.00'
    total_cell.alignment     = Alignment(horizontal="right", vertical="center")
    total_cell.border        = _border()
    ws.row_dimensions[total_row].height = 24

    ws.freeze_panes = "A5"

    filename = f"ventas_{fecha_desde.strftime('%Y%m%d')}_{fecha_hasta.strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


# ═══════════════════════════════════════════════════════════════════
# VISTA — EXPORTAR INVENTARIO EXCEL
# ═══════════════════════════════════════════════════════════════════

@admin_required
def exportar_inventario_excel(request):
    """
    Exporta el inventario completo a Excel (todos los materiales, sin paginar).
    Incluye: tipo, color, marca, stock, mínimo, costo/g, valor total, estado.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    materiales = list(
        Material.objects
        .filter(activo=True)
        .select_related('tipo', 'color', 'marca')
        .order_by('tipo__nombre', 'color__nombre')
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inventario"

    COLOR_HEADER_BG  = "1E3A2F"
    COLOR_HEADER_FG  = "FFFFFF"
    COLOR_CRITICO_BG = "3F1212"
    COLOR_CRITICO_FG = "FCA5A5"
    COLOR_TOTAL_BG   = "10B981"

    thin = Side(style='thin', color='D1D5DB')
    brd  = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Título
    ws.merge_cells('A1:I1')
    c = ws['A1']
    c.value = "A.N.T Studio — Inventario de Materiales"
    c.font  = Font(name='Arial', bold=True, size=14, color=COLOR_HEADER_FG)
    c.fill  = PatternFill("solid", fgColor=COLOR_HEADER_BG)
    c.alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 30

    # Subtítulo
    ws.merge_cells('A2:I2')
    c2 = ws['A2']
    c2.value = f"Generado el {date.today().strftime('%d/%m/%Y')}  ·  {len(materiales)} materiales activos"
    c2.font  = Font(name='Arial', size=10, color='6B7280')
    c2.alignment = Alignment(horizontal='center')
    ws.row_dimensions[2].height = 16

    ws.row_dimensions[3].height = 8

    # Encabezados
    headers = ['#', 'Tipo', 'Color', 'Marca', 'Stock (g)', 'Mínimo (g)', 'Costo/g (RD$)', 'Valor Total (RD$)', 'Estado']
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.font      = Font(name='Arial', bold=True, size=10, color=COLOR_HEADER_FG)
        cell.fill      = PatternFill("solid", fgColor=COLOR_HEADER_BG)
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border    = brd
    ws.row_dimensions[4].height = 22

    valor_total_global = Decimal('0')

    for i, m in enumerate(materiales, 1):
        row       = i + 4
        is_alt    = (i % 2 == 0)
        critico   = m.necesita_reposicion
        valor_mat = m.stock_actual * m.costo_por_gramo
        valor_total_global += valor_mat

        bg = COLOR_CRITICO_BG if critico else ('F0FDF4' if is_alt else 'FFFFFF')
        fg = COLOR_CRITICO_FG if critico else '111827'

        data = [
            i,
            m.tipo.nombre,
            m.color.nombre,
            m.marca.nombre,
            float(m.stock_actual),
            float(m.stock_minimo),
            float(m.costo_por_gramo),
            float(valor_mat),
            'Reponer' if critico else 'OK',
        ]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.font      = Font(name='Arial', size=10, color=fg)
            cell.fill      = PatternFill("solid", fgColor=bg)
            cell.border    = brd
            cell.alignment = Alignment(vertical='center')
            if col in (5, 6):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right', vertical='center')
            if col in (7, 8):
                cell.number_format = '#,##0.0000' if col == 7 else '#,##0.00'
                cell.alignment = Alignment(horizontal='right', vertical='center')

    # Fila de total global
    total_row = len(materiales) + 5
    ws.merge_cells(f'A{total_row}:G{total_row}')
    lc = ws[f'A{total_row}']
    lc.value = "VALOR TOTAL DEL INVENTARIO"
    lc.font  = Font(name='Arial', bold=True, size=11, color=COLOR_HEADER_FG)
    lc.fill  = PatternFill("solid", fgColor=COLOR_TOTAL_BG)
    lc.alignment = Alignment(horizontal='right', vertical='center')
    lc.border = brd

    tc = ws[f'H{total_row}']
    tc.value         = float(valor_total_global)
    tc.font          = Font(name='Arial', bold=True, size=11, color=COLOR_HEADER_FG)
    tc.fill          = PatternFill("solid", fgColor=COLOR_TOTAL_BG)
    tc.number_format = '#,##0.00'
    tc.alignment     = Alignment(horizontal='right', vertical='center')
    tc.border        = brd
    ws.row_dimensions[total_row].height = 22

    # También poner el estado en la columna I del total
    ec = ws[f'I{total_row}']
    ec.fill   = PatternFill("solid", fgColor=COLOR_TOTAL_BG)
    ec.border = brd

    # Anchos de columna
    col_widths = [5, 14, 16, 16, 13, 13, 16, 18, 10]
    for col, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.freeze_panes = 'A5'

    # Segunda hoja: solo los críticos
    criticos = [m for m in materiales if m.necesita_reposicion]
    if criticos:
        ws2 = wb.create_sheet("Stock Crítico")
        ws2.merge_cells('A1:I1')
        c = ws2['A1']
        c.value = "Materiales que necesitan reposición"
        c.font  = Font(name='Arial', bold=True, size=13, color='FFFFFF')
        c.fill  = PatternFill("solid", fgColor='7F1D1D')
        c.alignment = Alignment(horizontal='center', vertical='center')
        ws2.row_dimensions[1].height = 28

        for col, h in enumerate(headers, 1):
            cell = ws2.cell(row=2, column=col, value=h)
            cell.font      = Font(name='Arial', bold=True, size=10, color='FFFFFF')
            cell.fill      = PatternFill("solid", fgColor='991B1B')
            cell.alignment = Alignment(horizontal='center')
            cell.border    = brd

        for i, m in enumerate(criticos, 1):
            row       = i + 2
            valor_mat = m.stock_actual * m.costo_por_gramo
            data = [
                i, m.tipo.nombre, m.color.nombre, m.marca.nombre,
                float(m.stock_actual), float(m.stock_minimo),
                float(m.costo_por_gramo), float(valor_mat), 'Reponer',
            ]
            for col, val in enumerate(data, 1):
                cell = ws2.cell(row=row, column=col, value=val)
                cell.font   = Font(name='Arial', size=10)
                cell.border = brd
                cell.alignment = Alignment(vertical='center')
                if col in (5, 6, 7, 8):
                    cell.number_format = '#,##0.00'
                    cell.alignment = Alignment(horizontal='right', vertical='center')

        for col, w in enumerate(col_widths, 1):
            ws2.column_dimensions[get_column_letter(col)].width = w

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"inventario_{date.today().strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response