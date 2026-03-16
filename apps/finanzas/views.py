from django.shortcuts import render, redirect
from apps.usuarios.decorators import admin_required
from django.contrib import messages
from decimal import Decimal
from .forms import GastoForm, GastoFormExtendido
from .models import Gasto
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth
from datetime import date
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse


@admin_required
def gastos_list(request):
    """
    Lista los gastos registrados mostrando información clave simplificada:
    Fecha, Descripción, Categoría, Monto y Estado.
    Permite filtrar por tipo y buscar por descripción o proveedor.
    """
    gastos = Gasto.objects.all().order_by("-fecha", "-id")

    # Búsqueda por descripción o proveedor
    search_query = request.GET.get("search", "")
    if search_query:
        gastos = gastos.filter(
            Q(descripcion__icontains=search_query) |
            Q(proveedor__icontains=search_query)
        )

    # Filtro por tipo de gasto
    tipo_filtro = request.GET.get("tipo", "")
    if tipo_filtro:
        gastos = gastos.filter(tipo=tipo_filtro)

    # Cálculo de totales — sobre el queryset ya filtrado
    conteo = gastos.count()
    total_gastos = gastos.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    promedio = total_gastos / conteo if conteo > 0 else Decimal("0.00")

    context = {
        "gastos": gastos,
        "total_gastos": total_gastos,
        "tipos": Gasto.TIPOS,
        "search_query": search_query,
        "tipo_filtro": tipo_filtro,
        "promedio": promedio,
    }

    return render(request, "finanzas/gastos/gastos_list.html", context)


@admin_required
def dashboard_finanzas(request):
    """
    Renderiza el dashboard de finanzas.
    Los datos se cargan de forma asíncrona vía AJAX desde gastos_por_mes().
    """
    return render(request, "finanzas/gastos/dashboard_gastos.html")


@admin_required
def gasto_detalle(request, gasto_id):
    """
    Vista detallada de un gasto que permite su edición.
    Maneja eliminación de comprobantes usando el flag del formulario.
    """
    gasto = get_object_or_404(Gasto, id=gasto_id)

    if request.method == "POST":
        data  = request.POST.copy()
        files = request.FILES.copy() if request.FILES else {}

        if gasto.es_automatico:
            data["monto"] = gasto.monto
            data["fecha"]  = gasto.fecha
            data["tipo"]   = gasto.tipo
        else:
            try:
                monto_str  = data.get("monto", "0").replace(",", "")
                data["monto"] = abs(Decimal(monto_str))
            except (ValueError, TypeError):
                messages.error(request, "El monto ingresado no es válido.")
                return redirect("finanzas:gasto_detalle", gasto_id=gasto_id)

        usar_extendido = (
            bool(files.get("comprobante")) or
            bool(data.get("proveedor")) or
            data.get("eliminar_comprobante") == "true"
        )

        FormClass = GastoFormExtendido if usar_extendido else GastoForm
        form = FormClass(data, files, instance=gasto) if usar_extendido else FormClass(data, instance=gasto)

        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Gasto actualizado correctamente.")
            except Exception as e:
                messages.error(request, f"Error al guardar: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return redirect("finanzas:gasto_detalle", gasto_id=gasto_id)

    return render(request, "finanzas/gastos/gasto_detalle.html", {"gasto": gasto})


@admin_required
@require_http_methods(["POST"])
def crear_gasto(request):
    """
    Procesa la creación de un nuevo gasto.
    Maneja la limpieza de datos monetarios y redireccionamiento inteligente.
    """
    data  = request.POST.copy()
    files = request.FILES.copy()

    try:
        monto_str  = data.get("monto", "0").replace(",", "")
        data["monto"] = abs(Decimal(monto_str))
    except (ValueError, TypeError):
        messages.error(request, "El monto ingresado no es válido.")
        return redirect("finanzas:gastos")

    usar_extendido = any([
        files.get("comprobante"),
        data.get("proveedor"),
        data.get("numero_factura"),
        data.get("es_recurrente"),
    ])

    FormClass = GastoFormExtendido if usar_extendido else GastoForm
    form = FormClass(data, files)

    if form.is_valid():
        try:
            gasto = form.save()
            messages.success(request, "Gasto registrado exitosamente.")

            next_url = request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect("finanzas:gasto_detalle", gasto_id=gasto.id)

        except Exception as e:
            messages.error(request, f"Error al guardar: {str(e)}")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect("finanzas:gastos")


@admin_required
@require_http_methods(["POST"])
def editar_gasto(request, gasto_id):
    """
    Edita un gasto existente manejando restricciones de campos.
    """
    gasto    = get_object_or_404(Gasto, id=gasto_id)
    next_url = request.META.get("HTTP_REFERER", reverse("finanzas:gastos"))

    data  = request.POST.copy()
    files = request.FILES.copy() if request.FILES else {}

    if gasto.es_automatico:
        data["monto"] = gasto.monto
        data["fecha"]  = gasto.fecha
        data["tipo"]   = gasto.tipo
    else:
        try:
            monto_str  = data.get("monto", "0").replace(",", "")
            data["monto"] = abs(Decimal(monto_str))
        except (ValueError, TypeError):
            messages.error(request, "El monto ingresado no es válido.")
            return redirect("finanzas:gastos")

    usar_extendido = (
        gasto.es_recurrente or
        bool(gasto.comprobante) or
        bool(data.get("es_recurrente")) or
        bool(files.get("comprobante")) or
        bool(data.get("proveedor")) or
        bool(data.get("numero_factura")) or
        data.get("eliminar_comprobante") == "true"
    )

    if "es_recurrente" not in data and usar_extendido:
        data["es_recurrente"] = False

    FormClass = GastoFormExtendido if usar_extendido else GastoForm
    form = FormClass(data, files, instance=gasto) if usar_extendido else FormClass(data, instance=gasto)

    if form.is_valid():
        try:
            form.save()
            messages.success(request, "Gasto actualizado correctamente.")
        except Exception as e:
            messages.error(request, f"Error al actualizar: {str(e)}")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")

    return redirect(next_url)


@admin_required
def gasto_detalle_api(request, gasto_id):
    """API endpoint para obtener detalles de un gasto en formato JSON."""
    gasto = get_object_or_404(Gasto, id=gasto_id)

    data = {
        "id":             gasto.id,
        "descripcion":    gasto.descripcion,
        "monto":          float(gasto.monto),
        "fecha":          gasto.fecha.strftime("%Y-%m-%d"),
        "tipo":           gasto.tipo,
        "notas":          gasto.notas,
        "es_automatico":  gasto.es_automatico,
        "proveedor":      gasto.proveedor or "",
        "numero_factura": gasto.numero_factura or "",
        "comprobante":    gasto.comprobante.url if gasto.comprobante else None,
        "es_recurrente":  gasto.es_recurrente,
    }
    return JsonResponse(data)


@admin_required
def eliminar_gasto(request, gasto_id):
    """
    Elimina un gasto del sistema.
    Impide la eliminación de gastos automáticos vinculados a inventario.
    """
    gasto = get_object_or_404(Gasto, id=gasto_id)

    if gasto.es_automatico:
        return JsonResponse({
            "success": False,
            "message": "No se pueden eliminar gastos automáticos. Elimina la entrada de inventario.",
        })

    try:
        gasto.delete()
        return JsonResponse({"success": True, "message": "Gasto eliminado correctamente."})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error al eliminar: {str(e)}"})


@admin_required
def gastos_por_mes(request):
    """
    API endpoint para estadísticas de gastos.
    Retorna datos agrupados por mes y por tipo para visualización en gráficos.
    Usa agregación en DB en vez de cargar todos los registros a Python.
    """
    # ── Totales por mes ──────────────────────────────────────────
    totales_qs = (
        Gasto.objects
        .annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(total=Sum("monto"))
        .order_by("mes")
    )

    meses_con_datos = [row["mes"].strftime("%Y-%m") for row in totales_qs]
    totales_por_mes = {row["mes"].strftime("%Y-%m"): float(row["total"]) for row in totales_qs}

    # ── Por tipo y mes ───────────────────────────────────────────
    tipos_qs = (
        Gasto.objects
        .annotate(mes=TruncMonth("fecha"))
        .values("tipo", "mes")
        .annotate(total=Sum("monto"))
        .order_by("tipo", "mes")
    )

    gastos_por_tipo = {tipo[0]: {m: 0.0 for m in meses_con_datos} for tipo in Gasto.TIPOS}
    for row in tipos_qs:
        tipo = row["tipo"]
        mes  = row["mes"].strftime("%Y-%m")
        if tipo in gastos_por_tipo and mes in gastos_por_tipo[tipo]:
            gastos_por_tipo[tipo][mes] = float(row["total"])

    return JsonResponse({
        "meses":    meses_con_datos,
        "totales":  [totales_por_mes[m] for m in meses_con_datos],
        "por_tipo": gastos_por_tipo,
    })

@admin_required
def exportar_gastos_excel(request):
    """
    Exporta el historial de gastos a Excel.
    Acepta los mismos filtros GET que gastos_list: ?tipo=&desde=&hasta=
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from datetime import date

    # ── Filtros ──────────────────────────────────────────────────
    tipo_filtro     = request.GET.get("tipo", "")
    fecha_desde_str = request.GET.get("desde", "")
    fecha_hasta_str = request.GET.get("hasta", "")

    qs = Gasto.objects.all().order_by("-fecha", "-id")

    if tipo_filtro:
        qs = qs.filter(tipo=tipo_filtro)

    try:
        if fecha_desde_str:
            qs = qs.filter(fecha__gte=date.fromisoformat(fecha_desde_str))
        if fecha_hasta_str:
            qs = qs.filter(fecha__lte=date.fromisoformat(fecha_hasta_str))
    except ValueError:
        pass

    gastos = list(qs)
    total  = sum(g.monto for g in gastos)
    hoy    = date.today()

    # ── Paleta ───────────────────────────────────────────────────
    C_BG     = "0F172A"   # slate-900
    C_HEADER = "1E3A5F"   # azul oscuro para encabezados de columna
    C_ACCENT = "EF4444"   # rojo para gastos
    C_ALT    = "162032"   # fila alternada
    C_DARK   = "1E293B"   # slate-800
    C_WHITE  = "FFFFFF"
    C_TEXT   = "E2E8F0"
    C_MUTED  = "94A3B8"
    C_AUTO   = "1E3A2F"   # verde oscuro para gastos automáticos

    def _fill(hex_color):
        return PatternFill("solid", fgColor=hex_color)

    def _font(bold=False, color=C_WHITE, size=10):
        return Font(bold=bold, color=color, size=size, name="Calibri")

    def _border():
        s = Side(style="thin", color="334155")
        return Border(left=s, right=s, top=s, bottom=s)

    # ── Libro y hoja ─────────────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Gastos"

    # ── Fila 1: Título ───────────────────────────────────────────
    ws.merge_cells("A1:H1")
    c = ws["A1"]
    c.value     = "A.N.T Studio — Reporte de Gastos"
    c.font      = _font(bold=True, color=C_ACCENT, size=14)
    c.fill      = _fill(C_BG)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    # ── Fila 2: Período / filtros ────────────────────────────────
    filtro_desc = f"Tipo: {tipo_filtro}" if tipo_filtro else "Todos los tipos"
    if fecha_desde_str or fecha_hasta_str:
        rango = f"{fecha_desde_str or '—'}  →  {fecha_hasta_str or '—'}"
        filtro_desc += f"   |   Período: {rango}"
    filtro_desc += f"   |   Generado: {hoy.strftime('%d/%m/%Y')}"

    ws.merge_cells("A2:H2")
    c2          = ws["A2"]
    c2.value    = filtro_desc
    c2.font     = _font(color=C_MUTED, size=9)
    c2.fill     = _fill(C_BG)
    c2.alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 18

    # ── Fila 3: Espaciado ────────────────────────────────────────
    ws.row_dimensions[3].height = 8
    for col in range(1, 9):
        ws.cell(row=3, column=col).fill = _fill(C_BG)

    # ── Fila 4: Encabezados ──────────────────────────────────────
    HEADERS    = ["#", "Fecha", "Descripción", "Categoría", "Proveedor", "Referencia", "Tipo", "Monto (RD$)"]
    COL_WIDTHS = [5, 14, 36, 18, 22, 18, 14, 16]

    for i, (header, width) in enumerate(zip(HEADERS, COL_WIDTHS), start=1):
        cell            = ws.cell(row=4, column=i, value=header)
        cell.font       = _font(bold=True, size=10)
        cell.fill       = _fill(C_HEADER)
        cell.alignment  = Alignment(horizontal="center", vertical="center")
        cell.border     = _border()
        ws.column_dimensions[get_column_letter(i)].width = width

    ws.row_dimensions[4].height = 22

    # ── Filas de datos ───────────────────────────────────────────
    LABELS_TIPO = dict(Gasto.TIPOS)

    for row_idx, gasto in enumerate(gastos, start=5):
        alt = (row_idx % 2 == 0)
        # Gastos automáticos tienen fondo verde oscuro para distinguirlos
        if gasto.es_automatico:
            bg = _fill(C_AUTO)
            fg = "6EE7B7"   # verde claro
        else:
            bg = _fill(C_DARK if alt else C_ALT)
            fg = C_TEXT

        valores = [
            row_idx - 4,                                          # #
            gasto.fecha.strftime("%d/%m/%Y"),                     # Fecha
            gasto.descripcion,                                    # Descripción
            LABELS_TIPO.get(gasto.tipo, gasto.tipo),              # Categoría
            gasto.proveedor or "—",                               # Proveedor
            getattr(gasto, "numero_factura", None) or "—",        # Referencia
            "Automático" if gasto.es_automatico else "Manual",    # Tipo
            float(gasto.monto),                                   # Monto
        ]

        for col_idx, valor in enumerate(valores, start=1):
            cell            = ws.cell(row=row_idx, column=col_idx, value=valor)
            cell.fill       = bg
            cell.border     = _border()
            cell.font       = _font(color=fg)
            cell.alignment  = Alignment(vertical="center")

            if col_idx == 1:   # índice centrado
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.font      = _font(bold=True, color=C_MUTED)
            elif col_idx == 2:  # fecha centrada
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 8:  # monto
                cell.number_format = "#,##0.00"
                cell.alignment     = Alignment(horizontal="right", vertical="center")
                cell.font          = _font(bold=True, color=C_ACCENT if not gasto.es_automatico else "6EE7B7")

        ws.row_dimensions[row_idx].height = 18

    # ── Fila de Total ────────────────────────────────────────────
    total_row = len(gastos) + 5
    ws.merge_cells(f"A{total_row}:G{total_row}")
    lc            = ws[f"A{total_row}"]
    lc.value      = f"TOTAL  ({len(gastos)} registros)"
    lc.font       = _font(bold=True, color=C_ACCENT, size=11)
    lc.fill       = _fill(C_BG)
    lc.alignment  = Alignment(horizontal="right", vertical="center")
    lc.border     = _border()

    tc                = ws[f"H{total_row}"]
    tc.value          = float(total)
    tc.font           = _font(bold=True, color=C_ACCENT, size=12)
    tc.fill           = _fill(C_BG)
    tc.number_format  = "#,##0.00"
    tc.alignment      = Alignment(horizontal="right", vertical="center")
    tc.border         = _border()
    ws.row_dimensions[total_row].height = 24

    # ── Segunda hoja: resumen por categoría ──────────────────────
    ws2       = wb.create_sheet("Resumen por Categoría")
    ws2.merge_cells("A1:C1")
    c         = ws2["A1"]
    c.value   = "Resumen de Gastos por Categoría"
    c.font    = _font(bold=True, color=C_ACCENT, size=13)
    c.fill    = _fill(C_BG)
    c.alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 28

    for i, h in enumerate(["Categoría", "Cantidad", "Total (RD$)"], start=1):
        cell           = ws2.cell(row=2, column=i, value=h)
        cell.font      = _font(bold=True)
        cell.fill      = _fill(C_HEADER)
        cell.alignment = Alignment(horizontal="center")
        cell.border    = _border()

    # Calcular totales por tipo
    resumen = {}
    for g in gastos:
        label = LABELS_TIPO.get(g.tipo, g.tipo)
        if label not in resumen:
            resumen[label] = {"count": 0, "total": Decimal("0")}
        resumen[label]["count"] += 1
        resumen[label]["total"] += g.monto

    for i, (label, data) in enumerate(sorted(resumen.items()), start=3):
        alt = (i % 2 == 0)
        bg  = _fill(C_DARK if alt else C_ALT)
        for col, val in enumerate([label, data["count"], float(data["total"])], start=1):
            cell           = ws2.cell(row=i, column=col, value=val)
            cell.font      = _font(color=C_TEXT)
            cell.fill      = bg
            cell.border    = _border()
            cell.alignment = Alignment(vertical="center")
            if col == 3:
                cell.number_format = "#,##0.00"
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.font = _font(bold=True, color=C_ACCENT)

    for col, w in enumerate([28, 12, 18], start=1):
        ws2.column_dimensions[get_column_letter(col)].width = w

    # ── Freeze panes ─────────────────────────────────────────────
    ws.freeze_panes  = "A5"
    ws2.freeze_panes = "A3"

    # ── Respuesta ────────────────────────────────────────────────
    desde_s = fecha_desde_str.replace("-", "") if fecha_desde_str else "todo"
    hasta_s = fecha_hasta_str.replace("-", "") if fecha_hasta_str else hoy.strftime("%Y%m%d")
    filename = f"gastos_{desde_s}_{hasta_s}.xlsx"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response