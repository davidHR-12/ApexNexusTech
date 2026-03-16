import os
import io
from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage,
)

# ════════════════════════════════════════════════════════════════
# PALETA
# ════════════════════════════════════════════════════════════════
VERDE    = colors.HexColor("#10b981")
OSCURO   = colors.HexColor("#0f172a")
GRIS_MED = colors.HexColor("#475569")
GRIS_CLR = colors.HexColor("#e2e8f0")
GRIS_BG  = colors.HexColor("#f8fafc")
GRIS_ALT = colors.HexColor("#f1f5f9")
BLANCO   = colors.white
AMARILLO = colors.HexColor("#f59e0b")
ROJO     = colors.HexColor("#ef4444")
AZUL     = colors.HexColor("#3b82f6")

W, H = A4
MG   = 15 * mm
UTIL = W - 2 * MG


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════
def _estilos():
    b = getSampleStyleSheet()
    def P(n, **k): return ParagraphStyle(n, parent=b["Normal"], **k)
    return {
        "empresa":  P("empresa",  fontSize=18, textColor=OSCURO,   leading=22, fontName="Helvetica-Bold"),
        "slogan":   P("slogan",   fontSize=8,  textColor=GRIS_MED, leading=11),
        "contacto": P("contacto", fontSize=7,  textColor=GRIS_MED, leading=10),
        "fac_lbl":  P("fac_lbl",  fontSize=8,  textColor=GRIS_MED, leading=10, alignment=TA_RIGHT, fontName="Helvetica-Bold"),
        "fac_num":  P("fac_num",  fontSize=28, textColor=VERDE,    leading=33, fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "fecha":    P("fecha",    fontSize=8,  textColor=GRIS_MED, leading=10, alignment=TA_RIGHT),
        "sec":      P("sec",      fontSize=7,  textColor=VERDE,    leading=9,  fontName="Helvetica-Bold"),
        "cli_nom":  P("cli_nom",  fontSize=10, textColor=OSCURO,   leading=13, fontName="Helvetica-Bold"),
        "cli_sub":  P("cli_sub",  fontSize=7,  textColor=GRIS_MED, leading=10),
        "badge":    P("badge",    fontSize=8,  textColor=BLANCO,   leading=10, fontName="Helvetica-Bold", alignment=TA_CENTER),
        "th":       P("th",       fontSize=7,  textColor=BLANCO,   leading=9,  fontName="Helvetica-Bold", alignment=TA_CENTER),
        "th_l":     P("th_l",     fontSize=7,  textColor=BLANCO,   leading=9,  fontName="Helvetica-Bold"),
        "td_c":     P("td_c",     fontSize=8,  textColor=OSCURO,   leading=10, alignment=TA_CENTER),
        "td_l":     P("td_l",     fontSize=8,  textColor=OSCURO,   leading=10),
        "td_sub":   P("td_sub",   fontSize=6,  textColor=GRIS_MED, leading=8),
        "td_r":     P("td_r",     fontSize=8,  textColor=OSCURO,   leading=10, alignment=TA_RIGHT, fontName="Courier"),
        "tot_lbl":  P("tot_lbl",  fontSize=8,  textColor=GRIS_MED, leading=10, alignment=TA_RIGHT),
        "tot_val":  P("tot_val",  fontSize=8,  textColor=OSCURO,   leading=10, fontName="Helvetica-Bold", alignment=TA_RIGHT),
        "gran_l":   P("gran_l",   fontSize=10, textColor=BLANCO,   leading=12, fontName="Helvetica-Bold"),
        "gran_v":   P("gran_v",   fontSize=10, textColor=BLANCO,   leading=12, fontName="Courier-Bold",   alignment=TA_RIGHT),
        "nota":     P("nota",     fontSize=7,  textColor=GRIS_MED, leading=9),
        "nota_tit": P("nota_tit", fontSize=7,  textColor=VERDE,    leading=9,  fontName="Helvetica-Bold"),
        "footer":   P("footer",   fontSize=7,  textColor=GRIS_MED, leading=9,  alignment=TA_CENTER),
        "pag_th":   P("pag_th",   fontSize=7,  textColor=GRIS_MED, leading=9,  fontName="Helvetica-Bold"),
        "pag_td":   P("pag_td",   fontSize=7,  textColor=OSCURO,   leading=9),
        "pag_mon":  P("pag_mon",  fontSize=7,  textColor=OSCURO,   leading=9,  fontName="Courier", alignment=TA_RIGHT),
    }


def _color_estado(estado):
    return {
        "En_Espera":     AMARILLO,
        "Confirmado":    AZUL,
        "En_Produccion": colors.HexColor("#8b5cf6"),
        "Listo":         colors.HexColor("#06b6d4"),
        "Entregado":     VERDE,
        "Cancelado":     ROJO,
    }.get(estado, GRIS_MED)


def _materiales_contenedor(item):
    """
    Devuelve una cadena con los materiales únicos de los componentes del contenedor.
    Ejemplo: "ABS Rojo · PLA Amarillo"
    """
    materiales = []
    vistos = set()
    for comp in item.componentes.all():
        mp = getattr(comp, "material_personalizado", None)
        if not mp:
            continue
        if mp.pk in vistos:
            continue
        vistos.add(mp.pk)
        tipo  = str(getattr(mp, "tipo", "") or "")
        color = getattr(mp, "color", None)
        color_str = (str(color.nombre) if hasattr(color, "nombre") else str(color)) if color else ""
        label = " ".join(filter(None, [tipo, color_str]))
        materiales.append(label or str(mp))
    return " · ".join(materiales) if materiales else "—"


# ════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ════════════════════════════════════════════════════════════════
def generar_factura_pdf(request, pedido_id):
    """
    Genera y devuelve el PDF de factura del pedido.

    Reglas de visibilidad en la factura:
    • Ítems de catálogo  → una línea normal.
    • Contenedor         → una línea con nombre, materiales agregados de componentes
                           y precio final al cliente. Los componentes NO aparecen.
    • Ítem manual legacy → una línea normal (flujo antiguo, sin item_padre).
    • Componentes        → nunca se muestran (son detalle interno de producción).
    """
    from apps.pedidos.models import Pedido
    from apps.core.models import ConfiguracionFactura

    pedido = get_object_or_404(Pedido, pk=pedido_id)
    config = ConfiguracionFactura.obtener()

    # Solo raíz — excluye componentes (item_padre__isnull=True)
    items = (
        pedido.items
        .filter(item_padre__isnull=True)
        .select_related("variante__producto", "material_personalizado")
        .prefetch_related(
            "componentes",
            "componentes__material_personalizado",
            "componentes__material_personalizado__color",
        )
    )
    pagos = pedido.pagos.all()

    S   = _estilos()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MG, rightMargin=MG,
        topMargin=MG,  bottomMargin=MG,
        title=f"Factura #{pedido.id}",
        author=config.nombre_negocio,
    )

    story = []
    mitad = UTIL / 2

    # ── 1. CABECERA ─────────────────────────────────────────────
    izq = []
    if config.logo and os.path.exists(config.logo.path):
        try:
            logo = RLImage(config.logo.path, width=40*mm, height=14*mm)
            logo.hAlign = "LEFT"
            izq.append(logo)
            izq.append(Spacer(1, 2*mm))
        except Exception:
            pass

    izq.append(Paragraph(config.nombre_negocio, S["empresa"]))
    if config.slogan:
        izq.append(Paragraph(config.slogan, S["slogan"]))
    izq.append(Spacer(1, 2*mm))
    for line in filter(None, [
        f"Tel: {config.telefono}" if config.telefono else None,
        config.email or None,
        config.direccion or None,
        f"RNC: {config.rnc}" if getattr(config, "rnc", None) else None,
    ]):
        izq.append(Paragraph(line, S["contacto"]))

    fecha_str = (pedido.fecha_creacion.strftime("%d/%m/%Y")
                 if getattr(pedido, "fecha_creacion", None) else "—")
    der = [
        Paragraph("FACTURA", S["fac_lbl"]),
        Paragraph(f"#{pedido.id:04d}", S["fac_num"]),
        Spacer(1, 1*mm),
        Paragraph(f"Fecha: {fecha_str}", S["fecha"]),
    ]

    cab = Table([[izq, der]], colWidths=[mitad, mitad])
    cab.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("ALIGN",         (1,0),(1, 0),  "RIGHT"),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
    ]))
    story.append(cab)
    story.append(Spacer(1, 3*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=VERDE, spaceAfter=3*mm))

    # ── 2. CLIENTE + ESTADO ─────────────────────────────────────
    nombre_cliente = (
        pedido.usuario.get_full_name() if getattr(pedido, "usuario_id", None)
        else getattr(pedido, "guest_nombre", "—")
    ) or "—"
    email_cliente = None
    if getattr(pedido, "usuario_id", None):
        u = pedido.usuario
        # Si es manual y el email es ficticio, no lo mostramos
        if not (getattr(u, "is_manual", False) and u.email.startswith("manual_")):
            email_cliente = u.email
    else:
        email_cliente = getattr(pedido, "guest_email", None)

    email_cliente = email_cliente or None
    if getattr(pedido, "usuario_id", None):
        tel_cliente = getattr(pedido.usuario, "telefono", "") or ""
    else:
        tel_cliente = getattr(pedido, "guest_telefono", "") or ""

    badge = Table(
        [[Paragraph(pedido.get_estado_pedido_display().upper(), S["badge"])]],
        colWidths=[42*mm],
    )
    badge.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), _color_estado(pedido.estado_pedido)),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
    ]))

    izq2 = [
    Paragraph("DATOS DEL CLIENTE", S["sec"]),
    Paragraph(nombre_cliente, S["cli_nom"]),
    ]
    if email_cliente:
        izq2.append(Paragraph(email_cliente, S["cli_sub"]))
    if tel_cliente:
        izq2.append(Paragraph(tel_cliente, S["cli_sub"]))

    metodo = (pedido.get_metodo_pago_preferido_display()
              if getattr(pedido, "metodo_pago_preferido", None) else "—")
    der2 = [
        Paragraph("ESTADO DEL PEDIDO", S["sec"]),
        badge,
        Spacer(1, 2*mm),
        Paragraph(f"Método: {metodo}", S["cli_sub"]),
    ]

    info = Table([[izq2, der2]], colWidths=[mitad, mitad])
    info.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GRIS_BG),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("BOX",           (0,0),(-1,-1), 0.5, GRIS_CLR),
    ]))
    story.append(info)

    # ── Descripción + notas públicas ────────────────────────────
    col_descripcion = []
    if getattr(pedido, "descripcion", None):
        col_descripcion.append(Paragraph("DESCRIPCIÓN DEL PEDIDO", S["nota_tit"]))
        col_descripcion.append(Spacer(1, 1*mm))
        col_descripcion.append(Paragraph(pedido.descripcion, S["nota"]))

    col_notas = []
    notas_visibles = pedido.anotaciones.filter(visible_para_cliente=True).order_by("fecha_creacion")
    if notas_visibles.exists():
        col_notas.append(Paragraph("NOTAS DEL PEDIDO", S["nota_tit"]))
        col_notas.append(Spacer(1, 1*mm))
        for nota in notas_visibles:
            col_notas.append(Paragraph(
                f"<b>{nota.fecha_creacion.strftime('%d/%m/%Y')}:</b> {nota.contenido}",
                S["nota"],
            ))
            col_notas.append(Spacer(1, 1*mm))

    if col_descripcion or col_notas:
        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_CLR))
        story.append(Spacer(1, 2*mm))
        ancho_col = 90*mm
        tabla_notas = Table([[col_descripcion, col_notas]], colWidths=[ancho_col, ancho_col])
        tabla_notas.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 5*mm),
        ]))
        story.append(tabla_notas)
        story.append(Spacer(1, 4*mm))

    # ── 3. TABLA DE ÍTEMS ────────────────────────────────────────
    fijos_mm = 8 + 22 + 14 + 30 + 30
    desc_w   = UTIL - fijos_mm * mm
    col_ws   = [8*mm, desc_w, 22*mm, 14*mm, 30*mm, 30*mm]

    filas = [[
        Paragraph("#",            S["th"]),
        Paragraph("Descripción",  S["th_l"]),
        Paragraph("Origen",       S["th"]),
        Paragraph("Cant.",        S["th"]),
        Paragraph("Precio Unit.", S["th"]),
        Paragraph("Subtotal",     S["th"]),
    ]]

    for i, item in enumerate(items, 1):

        # ── Catálogo ──────────────────────────────────────────────
        if getattr(item, "variante", None):
            nombre    = item.variante.producto.nombre
            mat_str   = "Catálogo"
            precio_u  = item.precio_unitario
            subtotal  = item.subtotal
            desc_cell = [Paragraph(nombre, S["td_l"])]

        # ── Personalizado (contenedor con componentes) ───────────
        else:
            nombre   = getattr(item, "descripcion", None) or "Producto personalizado"
            mat_str  = "Personalizado"
            subtotal = item.subtotal          # suma de subtotales de componentes
            cantidad = item.cantidad or 1
            precio_u = (subtotal / cantidad).quantize(Decimal("0.01")) if subtotal else Decimal("0")
            desc_cell = [Paragraph(nombre, S["td_l"])]

        precio_str = f"RD$ {precio_u:,.2f}" if precio_u else "—"

        filas.append([
            Paragraph(str(i),                 S["td_c"]),
            desc_cell,
            Paragraph(mat_str,                S["td_c"]),
            Paragraph(str(item.cantidad),     S["td_c"]),
            Paragraph(precio_str,             S["td_r"]),
            Paragraph(f"RD$ {subtotal:,.2f}", S["td_r"]),
        ])

    tbl_items = Table(filas, colWidths=col_ws, repeatRows=1)
    tbl_items.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1, 0), OSCURO),
        ("TOPPADDING",    (0,0),(-1, 0), 7),
        ("BOTTOMPADDING", (0,0),(-1, 0), 7),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [BLANCO, GRIS_ALT]),
        ("TOPPADDING",    (0,1),(-1,-1), 5),
        ("BOTTOMPADDING", (0,1),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ("VALIGN",        (0,1),(-1,-1), "TOP"),
        ("ALIGN",         (0,1),(0,-1),  "CENTER"),
        ("ALIGN",         (2,1),(3,-1),  "CENTER"),
        ("ALIGN",         (4,1),(-1,-1), "RIGHT"),
        ("LINEBELOW",     (0,0),(-1,-1), 0.3, GRIS_CLR),
        ("BOX",           (0,0),(-1,-1), 0.5, GRIS_CLR),
    ]))
    story.append(tbl_items)
    story.append(Spacer(1, 4*mm))

    # ── 4. PAGOS + TOTALES ───────────────────────────────────────
    # Total calculado directo de ítems — no usar pedido.precio_total porque
    # los contenedores tienen precio_unitario=0 y no se reflejan ahí.
    subtotal_items  = sum(item.subtotal for item in items)
    otros_costos    = pedido.otros_costos or Decimal("0")
    total           = subtotal_items + otros_costos
    pagado = sum(p.monto for p in pagos) if pagos.exists() else Decimal("0")
    saldo  = total - pagado

    tot_rows = [[
        Paragraph("Subtotal:",  S["tot_lbl"]),
        Paragraph(f"RD$ {subtotal_items:,.2f}", S["tot_val"]),
    ]]
    if otros_costos > 0:
        tot_rows.append([
            Paragraph("Otros costos:", S["tot_lbl"]),
            Paragraph(f"RD$ {otros_costos:,.2f}", S["tot_val"]),
        ])
    if pagado > 0:
        tot_rows.append([
            Paragraph("Abonado:", S["tot_lbl"]),
            Paragraph(f"RD$ {pagado:,.2f}", S["tot_val"]),
        ])
    tbl_tot = Table(tot_rows, colWidths=[46*mm, 32*mm])
    tbl_tot.setStyle(TableStyle([
        ("ALIGN",         (0,0),(-1,-1), "RIGHT"),
        ("TOPPADDING",    (0,0),(-1,-1), 3),
        ("BOTTOMPADDING", (0,0),(-1,-1), 3),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("LINEBELOW",     (0,-2),(-1,-2), 0.5, GRIS_CLR),
    ]))

    gran_rows = [[
        Paragraph("TOTAL A COBRAR", S["gran_l"]),
        Paragraph(f"RD$ {total:,.2f}", S["gran_v"]),
    ]]
    if saldo is not None and saldo != total:
        gran_rows.append([
            Paragraph("SALDO PENDIENTE", S["gran_l"]),
            Paragraph(f"RD$ {saldo:,.2f}", S["gran_v"]),
        ])
    tbl_gran = Table(gran_rows, colWidths=[46*mm, 32*mm])
    tbl_gran.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), OSCURO),
        ("ALIGN",         (0,0),(-1,-1), "RIGHT"),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
    ]))

    der_cell = [tbl_tot, Spacer(1, 3*mm), tbl_gran]
    der_w    = 78 * mm
    izq_w    = UTIL - der_w - 5*mm

    if pagos.exists():
        pf = [[
            Paragraph("Método", S["pag_th"]),
            Paragraph("Monto",  S["pag_th"]),
            Paragraph("Ref.",   S["pag_th"]),
            Paragraph("Fecha",  S["pag_th"]),
        ]]
        for p in pagos:
            pf.append([
                Paragraph(p.get_metodo_display(),                                     S["pag_td"]),
                Paragraph(f"RD$ {p.monto:,.2f}",                                      S["pag_mon"]),
                Paragraph(getattr(p, "referencia", None) or "—",                      S["pag_td"]),
                Paragraph(p.fecha_pago.strftime("%d/%m/%y") if p.fecha_pago else "—", S["pag_td"]),
            ])
        pw = [izq_w * r for r in (.30, .28, .25, .17)]
        tbl_pagos = Table(pf, colWidths=pw)
        tbl_pagos.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1, 0), GRIS_ALT),
            ("FONTNAME",      (0,0),(-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 7),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("RIGHTPADDING",  (0,0),(-1,-1), 4),
            ("LINEBELOW",     (0,0),(-1,-1), 0.3, GRIS_CLR),
            ("BOX",           (0,0),(-1,-1), 0.5, GRIS_CLR),
        ]))
        izq_cell = [Paragraph("PAGOS REGISTRADOS", S["nota_tit"]), Spacer(1, 2*mm), tbl_pagos]
    else:
        izq_cell = [Paragraph("Sin pagos registrados.", S["nota"])]

    tbl_bot = Table([[izq_cell, der_cell]], colWidths=[izq_w, der_w])
    tbl_bot.setStyle(TableStyle([
        ("VALIGN",        (0,0),(-1,-1), "BOTTOM"),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
        ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 0),
        ("ALIGN",         (1,0),(1, 0),  "RIGHT"),
    ]))
    story.append(tbl_bot)

    # ── 5. FOOTER ───────────────────────────────────────────────
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=VERDE, spaceAfter=3*mm))
    for txt in filter(None, [
        getattr(config, "footer_texto", None),
        getattr(config, "nota_legal", None),
    ]):
        story.append(Paragraph(txt, S["footer"]))
    story.append(Paragraph(
        f"{config.nombre_negocio}  ·  {config.telefono}  ·  {config.email}",
        S["footer"],
    ))

    # ── Build & Response ────────────────────────────────────────
    doc.build(story)
    buf.seek(0)

    raw      = f"Factura_{pedido.id:04d}_{getattr(pedido, 'nombre_cliente', '') or 'cliente'}.pdf"
    filename = "".join(c if c.isalnum() or c in "-_." else "_" for c in raw)

    response = HttpResponse(buf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response