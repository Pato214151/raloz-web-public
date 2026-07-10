"""
RALOZ COL SAS — Servicio de Email + Generación de Factura PDF
─────────────────────────────────────────────────────────────
Genera el PDF en memoria (BytesIO) y lo envía como adjunto.
No guarda nada en disco (compatible con filesystems efímeros como Render).

Variables de entorno requeridas:
  EMAIL_REMITENTE   → tu_cuenta@gmail.com
  EMAIL_PASSWORD    → contraseña de aplicación (solo para SMTP local)
  EMAIL_NOMBRE      → Nombre visible del remitente (ej. "RALOZ COL SAS")
  BREVO_API_KEY     → xkeysib-... (producción en Render)
"""

import os
import base64
import logging
import smtplib
import requests as _requests
from io import BytesIO
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

logger = logging.getLogger(__name__)

# ─── Logo ──────────────────────────────────────────────────────────
_LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'logo.png')

# ─── Paleta de color RALOZ ────────────────────────────────────────
# Coincide con la identidad visual del POS (amber + slate)
C_HEADER_BG   = colors.HexColor('#1E293B')   # slate-800  — fondo cabecera oscura
C_AMBER       = colors.HexColor('#F59E0B')   # amber-500  — acento principal
C_AMBER_DARK  = colors.HexColor('#92400E')   # amber-800  — títulos de sección
C_AMBER_LIGHT = colors.HexColor('#FFFBEB')   # amber-50   — fondos claros
C_AMBER_MID   = colors.HexColor('#FDE68A')   # amber-200  — divisores / bordes
C_SLATE_100   = colors.HexColor('#F1F5F9')   # slate-100  — filas alternadas
C_SLATE_500   = colors.HexColor('#64748B')   # slate-500  — texto secundario
C_SLATE_700   = colors.HexColor('#334155')   # slate-700  — texto medio
C_TEXT        = colors.HexColor('#0F172A')   # slate-950  — texto principal
C_GREEN       = colors.HexColor('#16A34A')   # green-600  — montos pagados
C_RED         = colors.HexColor('#DC2626')   # red-600    — saldo pendiente
C_WHITE       = colors.white


# ══════════════════════════════════════════════════════════════════
# GENERACIÓN DE PDF EN MEMORIA
# ══════════════════════════════════════════════════════════════════

def generar_pdf_factura(factura, detalles) -> BytesIO:
    """
    Genera un PDF de factura profesional y lo devuelve como BytesIO.
    factura  → objeto Factura (modelo SQLAlchemy) o dict equivalente
    detalles → lista de objetos FacturaDetalle o dicts
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    story = []

    # ── Helpers ──────────────────────────────────────────────────
    def _v(obj, campo, default='—'):
        if isinstance(obj, dict):
            return obj.get(campo) or default
        return getattr(obj, campo, None) or default

    def _f(valor):
        try:
            return f"${float(valor):,.0f}".replace(',', '.')
        except Exception:
            return '—'

    # ── Estilos ───────────────────────────────────────────────────
    def st(name, **kw):
        return ParagraphStyle(name, **kw)

    # Encabezado
    s_company  = st('company',  fontSize=18, textColor=C_WHITE,      fontName='Helvetica-Bold', spaceAfter=2, leading=20)
    s_tagline  = st('tagline',  fontSize=8,  textColor=C_AMBER,       fontName='Helvetica',      spaceAfter=0, leading=11)
    s_nit      = st('nit',      fontSize=7.5,textColor=colors.HexColor('#94A3B8'), fontName='Helvetica', leading=10)
    s_fac_num  = st('facnum',   fontSize=22, textColor=C_AMBER,       fontName='Helvetica-Bold', alignment=TA_RIGHT, leading=24)
    s_fac_sub  = st('facsub',   fontSize=8.5,textColor=colors.HexColor('#94A3B8'), fontName='Helvetica',  alignment=TA_RIGHT, leading=12)

    # Secciones
    s_section  = st('section',  fontSize=7.5,textColor=C_AMBER_DARK,  fontName='Helvetica-Bold',
                    spaceAfter=4, leading=10, borderPad=0)

    # Cliente
    s_label    = st('label',    fontSize=7.5,textColor=C_SLATE_500,   fontName='Helvetica', leading=10)
    s_valor    = st('valor',    fontSize=8.5,textColor=C_TEXT,        fontName='Helvetica-Bold', leading=11)

    # Tabla productos
    s_th       = st('th',       fontSize=8,  textColor=C_WHITE,       fontName='Helvetica-Bold', alignment=TA_CENTER, leading=10)
    s_th_l     = st('th_l',     fontSize=8,  textColor=C_WHITE,       fontName='Helvetica-Bold', alignment=TA_LEFT,   leading=10)
    s_td       = st('td',       fontSize=8,  textColor=C_SLATE_700,   fontName='Helvetica',      alignment=TA_CENTER, leading=10)
    s_td_l     = st('td_l',     fontSize=8,  textColor=C_TEXT,        fontName='Helvetica',      alignment=TA_LEFT,   leading=10)
    s_td_r     = st('td_r',     fontSize=8,  textColor=C_SLATE_700,   fontName='Helvetica',      alignment=TA_RIGHT,  leading=10)

    # Totales / finanzas
    s_tot_l    = st('tot_l',    fontSize=9,  textColor=C_SLATE_500,   fontName='Helvetica',      alignment=TA_RIGHT, leading=12)
    s_tot_v    = st('tot_v',    fontSize=11, textColor=C_TEXT,        fontName='Helvetica-Bold', alignment=TA_RIGHT, leading=14)
    s_grand_l  = st('grand_l',  fontSize=10, textColor=C_WHITE,       fontName='Helvetica-Bold', alignment=TA_RIGHT, leading=13)
    s_grand_v  = st('grand_v',  fontSize=14, textColor=C_AMBER,       fontName='Helvetica-Bold', alignment=TA_RIGHT, leading=17)

    # Términos y footer
    s_terms_h  = st('terms_h',  fontSize=7.5,textColor=C_AMBER_DARK,  fontName='Helvetica-Bold', spaceAfter=3, leading=10)
    s_terms    = st('terms',    fontSize=6.5,textColor=C_SLATE_500,   fontName='Helvetica',      spaceAfter=2, leading=9)
    s_footer   = st('footer',   fontSize=7,  textColor=C_SLATE_500,   fontName='Helvetica',      alignment=TA_CENTER, leading=10)

    # ─────────────────────────────────────────────────────────────
    # DATOS BASE
    # ─────────────────────────────────────────────────────────────
    num_factura     = _v(factura, 'numero_factura')
    fecha_raw       = _v(factura, 'fecha_factura', None)
    if fecha_raw:
        fecha_str = fecha_raw[:10] if isinstance(fecha_raw, str) else fecha_raw.strftime('%d/%m/%Y')
    else:
        fecha_str = date.today().strftime('%d/%m/%Y')

    cliente_nombre  = _v(factura, 'cliente_nombre')
    cliente_email   = _v(factura, 'cliente_email')
    cliente_tel     = _v(factura, 'cliente_telefono')
    cliente_nit     = _v(factura, 'cliente_nit')
    cliente_dir     = _v(factura, 'cliente_direccion', '')
    colegio_nombre  = (
        getattr(getattr(factura, 'colegio', None), 'nombre', None)
        or _v(factura, 'colegio_nombre', None)
        or '—'
    )
    metodo_pago     = _v(factura, 'metodo_pago', 'MercadoPago')
    observaciones   = _v(factura, 'observaciones', '')

    # Página: 17.4 cm usable (A4 21cm - 2×1.8cm)
    PAGE_W = 17.4 * cm

    # ─────────────────────────────────────────────────────────────
    # A. CABECERA PRINCIPAL
    # ─────────────────────────────────────────────────────────────
    # Columna izquierda: logo + empresa
    logo_w, logo_h = 1.8 * cm, 1.8 * cm
    logo_cell_content = []
    try:
        if os.path.exists(_LOGO_PATH):
            logo_cell_content = RLImage(_LOGO_PATH, width=logo_w, height=logo_h)
        else:
            raise FileNotFoundError
    except Exception:
        logo_cell_content = Paragraph('<b>R</b>', st('r', fontSize=28, textColor=C_AMBER,
                                                      fontName='Helvetica-Bold'))

    empresa_info = [
        Paragraph('RALOZ COL SAS', s_company),
        Paragraph('Uniformes Escolares · Bogotá, Colombia', s_tagline),
        Paragraph('NIT: 901.XXX.XXX-X  ·  Tel: +57 321 341 2903', s_nit),
        Paragraph('ralozcol@outlook.com  ·  wa.me/573213412903', s_nit),
    ]

    # Columna derecha: FACTURA N°
    factura_info = [
        Paragraph('FACTURA', st('ftit', fontSize=9, textColor=colors.HexColor('#94A3B8'),
                                 fontName='Helvetica-Bold', alignment=TA_RIGHT, leading=11,
                                 letterSpacing=2)),
        Paragraph(f'N° {num_factura}', s_fac_num),
        Spacer(1, 0.15 * cm),
        Paragraph(f'Fecha: {fecha_str}', s_fac_sub),
        Paragraph(f'Método: {metodo_pago}', s_fac_sub),
    ]

    # Tabla de cabecera: 3 celdas [logo | empresa | factura]
    left_logo_table = Table([[logo_cell_content, empresa_info]],
                             colWidths=[2.2 * cm, 9.8 * cm])
    left_logo_table.setStyle(TableStyle([
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
    ]))

    header_table = Table(
        [[left_logo_table, factura_info]],
        colWidths=[12 * cm, 5.4 * cm],
    )
    header_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), C_HEADER_BG),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING',   (0, 0), (0, 0), 14),
        ('RIGHTPADDING',  (0, 0), (0, 0), 8),
        ('LEFTPADDING',   (1, 0), (1, 0), 8),
        ('RIGHTPADDING',  (1, 0), (1, 0), 14),
        ('LINEBELOW',     (0, 0), (-1, 0), 3, C_AMBER),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5 * cm))

    # ─────────────────────────────────────────────────────────────
    # B. DATOS DEL CLIENTE + RESUMEN DE PEDIDO
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph('▸  DATOS DEL CLIENTE', s_section))

    def _cliente_fila(label, valor):
        return [
            Paragraph(label, s_label),
            Paragraph(str(valor) if valor else '—', s_valor),
        ]

    col_izq = [
        _cliente_fila('Nombre completo', cliente_nombre),
        _cliente_fila('Correo electrónico', cliente_email),
        _cliente_fila('Teléfono', cliente_tel),
    ]
    if cliente_nit and cliente_nit != '—':
        col_izq.append(_cliente_fila('Cédula / NIT', cliente_nit))
    if cliente_dir and cliente_dir != '—':
        col_izq.append(_cliente_fila('Dirección de entrega', cliente_dir))

    col_der = [
        _cliente_fila('Colegio', colegio_nombre),
        _cliente_fila('Número de factura', num_factura),
        _cliente_fila('Fecha', fecha_str),
    ]

    # Rellenar para que ambas columnas tengan la misma altura
    max_rows = max(len(col_izq), len(col_der))
    while len(col_izq) < max_rows:
        col_izq.append([Paragraph('', s_label), Paragraph('', s_valor)])
    while len(col_der) < max_rows:
        col_der.append([Paragraph('', s_label), Paragraph('', s_valor)])

    # Combinar en tabla de 4 columnas [label | valor | label | valor]
    combined_rows = []
    for i in range(max_rows):
        combined_rows.append([
            col_izq[i][0], col_izq[i][1],
            col_der[i][0], col_der[i][1],
        ])

    cliente_table = Table(combined_rows, colWidths=[2.8*cm, 6.0*cm, 2.8*cm, 5.8*cm])
    cli_style = [
        ('BACKGROUND',    (0, 0), (-1, -1), C_AMBER_LIGHT),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('LINEBELOW',     (0, 0), (-1, -2), 0.3, C_AMBER_MID),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]
    for idx in range(0, max_rows, 2):
        cli_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.white))
    cliente_table.setStyle(TableStyle(cli_style))
    story.append(cliente_table)
    story.append(Spacer(1, 0.5 * cm))

    # ─────────────────────────────────────────────────────────────
    # C. TABLA DE PRODUCTOS
    # ─────────────────────────────────────────────────────────────
    story.append(Paragraph('▸  DETALLE DE PRODUCTOS', s_section))

    encabezado = [
        Paragraph('#',            s_th),
        Paragraph('Producto',     s_th_l),
        Paragraph('Talla',        s_th),
        Paragraph('Cant.',        s_th),
        Paragraph('Precio Unit.', s_th),
        Paragraph('Subtotal',     s_th),
    ]
    rows = [encabezado]

    total_calculado = 0
    for i, det in enumerate(detalles, start=1):
        if isinstance(det, dict):
            nombre_prod = det.get('producto_nombre') or det.get('nombre', '—')
        else:
            nombre_prod = (det.producto.nombre if det.producto else None) or '—'

        talla    = _v(det, 'talla_individual')
        cantidad = int(_v(det, 'cantidad', 0))
        precio   = float(_v(det, 'precio_unitario', 0))
        subtotal = float(_v(det, 'total_linea', precio * cantidad))
        total_calculado += subtotal

        rows.append([
            Paragraph(str(i),       st(f'n{i}a', parent=s_td)),
            Paragraph(nombre_prod,  st(f'n{i}b', parent=s_td_l)),
            Paragraph(talla,        st(f'n{i}c', parent=s_td)),
            Paragraph(str(cantidad),st(f'n{i}d', parent=s_td)),
            Paragraph(_f(precio),   st(f'n{i}e', parent=s_td_r)),
            Paragraph(_f(subtotal), st(f'n{i}f', parent=s_td_r)),
        ])

    prod_table = Table(rows, colWidths=[0.7*cm, 7.8*cm, 1.4*cm, 1.1*cm, 2.8*cm, 3.6*cm])
    prod_style = [
        # Encabezado
        ('BACKGROUND',    (0, 0), (-1, 0),  C_HEADER_BG),
        ('LINEBELOW',     (0, 0), (-1, 0),  2, C_AMBER),
        # Padding general
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        # Bordes sutiles entre filas
        ('LINEBELOW',     (0, 1), (-1, -1), 0.3, colors.HexColor('#E2E8F0')),
    ]
    for idx in range(1, len(rows)):
        bg = C_SLATE_100 if idx % 2 == 0 else colors.white
        prod_style.append(('BACKGROUND', (0, idx), (-1, idx), bg))

    prod_table.setStyle(TableStyle(prod_style))
    story.append(prod_table)
    story.append(Spacer(1, 0.4 * cm))

    # ─────────────────────────────────────────────────────────────
    # D. RESUMEN FINANCIERO
    # ─────────────────────────────────────────────────────────────
    total_final     = float(_v(factura, 'total', total_calculado))
    abono_pagado    = float(_v(factura, 'total_abonado', total_final) or total_final)
    saldo_pendiente = float(_v(factura, 'saldo_pendiente', 0) or 0)
    tiene_saldo     = saldo_pendiente > 0.01

    if tiene_saldo:
        # Pedido con abono: mostrar desglose
        fin_rows = [
            [
                Paragraph('Total del pedido:', s_tot_l),
                Paragraph(_f(total_final), s_tot_v),
            ],
            [
                Paragraph('Abono pagado hoy:', s_tot_l),
                Paragraph(_f(abono_pagado),
                          st('av', fontSize=11, textColor=C_GREEN,
                             fontName='Helvetica-Bold', alignment=TA_RIGHT, leading=14)),
            ],
            [
                Paragraph('Saldo pendiente al recoger:',
                          st('sl', fontSize=9, textColor=C_RED, fontName='Helvetica-Bold',
                             alignment=TA_RIGHT, leading=12)),
                Paragraph(_f(saldo_pendiente),
                          st('sv', fontSize=13, textColor=C_RED, fontName='Helvetica-Bold',
                             alignment=TA_RIGHT, leading=16)),
            ],
        ]
        fin_table = Table(fin_rows, colWidths=[13.4 * cm, 4 * cm])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 1), colors.white),
            ('BACKGROUND',    (0, 2), (-1, 2), colors.HexColor('#FEF2F2')),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 8),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
            ('LINEABOVE',     (0, 0), (-1, 0), 1.5, C_AMBER),
            ('LINEBELOW',     (0, 1), (-1, 1), 0.5, colors.HexColor('#E2E8F0')),
            ('LINEBELOW',     (0, 2), (-1, 2), 2, C_RED),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(fin_table)
    else:
        # Pago completo
        grand_data = [[
            Paragraph('TOTAL PAGADO:', s_grand_l),
            Paragraph(_f(total_final), s_grand_v),
        ]]
        grand_table = Table(grand_data, colWidths=[13.4 * cm, 4 * cm])
        grand_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), C_HEADER_BG),
            ('TOPPADDING',    (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING',   (0, 0), (-1, -1), 10),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
            ('LINEABOVE',     (0, 0), (-1, 0), 3, C_AMBER),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(grand_table)

    story.append(Spacer(1, 0.3 * cm))

    # ─────────────────────────────────────────────────────────────
    # E. NOTA DE PAGO Y REFERENCIA
    # ─────────────────────────────────────────────────────────────
    ref_limpia = observaciones.replace('Pedido web #', '').strip() if observaciones else ''
    nota_partes = [f'Método de pago: <b>{metodo_pago}</b>']
    if ref_limpia:
        nota_partes.append(f'Referencia: <b>{ref_limpia}</b>')
    nota_partes.append(f'Fecha de emisión: <b>{fecha_str}</b>')

    story.append(Paragraph(
        ' &nbsp;·&nbsp; '.join(nota_partes),
        st('nota', fontSize=7.5, textColor=C_SLATE_500, fontName='Helvetica',
           alignment=TA_CENTER, leading=11),
    ))
    story.append(Spacer(1, 0.5 * cm))

    # ─────────────────────────────────────────────────────────────
    # F. TÉRMINOS Y CONDICIONES
    # ─────────────────────────────────────────────────────────────
    # Caja con borde amber-200
    terminos_content = []

    terminos_content.append(Paragraph(
        '📋  TÉRMINOS, CONDICIONES Y POLÍTICA DE PRIVACIDAD', s_terms_h
    ))

    clausulas = [
        (
            '1. Protección de datos personales (Ley 1581 de 2012 — Habeas Data)',
            'Al realizar su pedido, el cliente autoriza expresamente a RALOZ COL SAS para recolectar '
            'y tratar sus datos personales (nombre, correo electrónico, teléfono, dirección) '
            'exclusivamente para la gestión, fabricación y entrega de su pedido. Los datos no serán '
            'compartidos con terceros sin consentimiento previo. Puede ejercer sus derechos de '
            'acceso, rectificación, supresión y revocación escribiendo a ralozcol@outlook.com.'
        ),
        (
            '2. Plazos de fabricación y entrega',
            'Los pedidos de prendas bajo fabricación especial (uniformes con logos bordados, '
            'prendas a medida) tienen un plazo estimado de producción de 15 a 45 días hábiles '
            'contados desde la confirmación del pago del abono. Las fechas estimadas son '
            'referenciales y pueden variar por causas de fuerza mayor. Le notificaremos por '
            'WhatsApp cuando su pedido esté listo para entrega.'
        ),
        (
            '3. Política de pagos y abono',
            'Para pedidos por fabricación se requiere un abono mínimo del 50% del valor total '
            'al momento del pedido. El saldo restante debe cancelarse antes de la entrega o al '
            'momento de recoger en el punto de venta. RALOZ COL SAS se reserva el derecho de '
            'retener el pedido hasta que se complete el pago total.'
        ),
        (
            '4. Cambios, devoluciones y garantía',
            'No se aceptan devoluciones en prendas de fabricación especial ni en productos '
            'personalizados con logos o bordados. Para prendas de stock, se aceptan cambios de '
            'talla dentro de los 5 días hábiles siguientes a la entrega, siempre que la prenda '
            'esté sin uso, con etiquetas y en su empaque original. Los defectos de fabricación '
            'están cubiertos por garantía de 30 días calendario desde la entrega.'
        ),
        (
            '5. Validez del documento',
            'Este comprobante fue generado automáticamente por el sistema de facturación de '
            'RALOZ COL SAS y tiene plena validez como soporte de compra. Consérvelo para '
            'cualquier reclamación, garantía o devolución. En caso de discrepancia entre el '
            'comprobante y la entrega recibida, contáctenos dentro de las 24 horas siguientes.'
        ),
        (
            '6. Jurisdicción y ley aplicable',
            'El presente documento y la relación comercial se rigen por las leyes de la '
            'República de Colombia. Cualquier controversia se resolverá de buena fe; de no '
            'lograrse acuerdo, las partes se someten a la jurisdicción de los tribunales '
            'ordinarios de la ciudad de Bogotá, D.C.'
        ),
    ]

    for titulo, texto in clausulas:
        terminos_content.append(Paragraph(
            f'<b>{titulo}</b>',
            st('clt', fontSize=6.5, textColor=C_AMBER_DARK, fontName='Helvetica-Bold',
               spaceAfter=1, leading=9),
        ))
        terminos_content.append(Paragraph(
            texto,
            st('clt2', fontSize=6.2, textColor=C_SLATE_500, fontName='Helvetica',
               spaceAfter=4, leading=8.5),
        ))

    terms_box = Table([[terminos_content]], colWidths=[PAGE_W])
    terms_box.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), C_AMBER_LIGHT),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('LINEABOVE',     (0, 0), (-1, 0),  1.5, C_AMBER),
        ('LINEBELOW',     (0, 0), (-1, 0),  0.5, C_AMBER_MID),
        ('LINEBEFORE',    (0, 0), (0, -1),  1.5, C_AMBER),
    ]))
    story.append(terms_box)
    story.append(Spacer(1, 0.4 * cm))

    # ─────────────────────────────────────────────────────────────
    # G. PIE DE PÁGINA
    # ─────────────────────────────────────────────────────────────
    HRFlowable(width='100%', thickness=0.5, color=C_AMBER_MID)

    footer_data = [[
        Paragraph(
            '📞 <b>+57 321 341 2903</b>',
            st('f1', fontSize=7.5, textColor=C_SLATE_500, fontName='Helvetica', alignment=TA_CENTER, leading=10),
        ),
        Paragraph(
            '✉️ <b>ralozcol@outlook.com</b>',
            st('f2', fontSize=7.5, textColor=C_SLATE_500, fontName='Helvetica', alignment=TA_CENTER, leading=10),
        ),
        Paragraph(
            '🌐 <b>ralozcolsas.com</b>',
            st('f3', fontSize=7.5, textColor=C_SLATE_500, fontName='Helvetica', alignment=TA_CENTER, leading=10),
        ),
    ]]
    footer_table = Table(footer_data, colWidths=[PAGE_W / 3] * 3)
    footer_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), C_HEADER_BG),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEABOVE',     (0, 0), (-1, 0),  2, C_AMBER),
    ]))
    story.append(footer_table)

    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        'RALOZ COL SAS · NIT: 901.XXX.XXX-X · Bogotá, Colombia '
        '— Este documento es generado automáticamente y tiene validez como comprobante de compra.',
        s_footer,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ══════════════════════════════════════════════════════════════════
# ENVÍO DE EMAIL
# ══════════════════════════════════════════════════════════════════

def enviar_email_factura(destinatario: str, factura, detalles) -> bool:
    """
    Genera el PDF y lo envía al cliente por email.
    Usa Brevo HTTP API en producción (sin SMTP bloqueado por Render).
    Fallback a SMTP en desarrollo local.
    """
    remitente  = os.getenv('EMAIL_REMITENTE', '').strip()
    password   = os.getenv('EMAIL_PASSWORD', '').strip()
    nombre_rem = os.getenv('EMAIL_NOMBRE', 'RALOZ COL SAS').strip()

    if not remitente or not password:
        logger.warning('[EMAIL] Credenciales no configuradas — EMAIL_REMITENTE o EMAIL_PASSWORD vacíos')
        return False

    # Sanitizar el destinatario (controlado por el cliente) para evitar
    # inyección de cabeceras de email (CR/LF) y validar formato básico.
    destinatario = (destinatario or '').replace('\r', '').replace('\n', '').strip()
    if '@' not in destinatario or ' ' in destinatario or len(destinatario) > 254:
        logger.warning('[EMAIL] Destinatario inválido, no se envía: %r', destinatario)
        return False

    def _v(obj, campo, default='—'):
        if isinstance(obj, dict):
            return obj.get(campo) or default
        return getattr(obj, campo, None) or default

    num_factura    = _v(factura, 'numero_factura')
    cliente_nombre = _v(factura, 'cliente_nombre')
    saldo          = float(_v(factura, 'saldo_pendiente', 0) or 0)

    # ── Generar PDF ────────────────────────────────────────────────
    try:
        pdf_buffer = generar_pdf_factura(factura, detalles)
    except Exception as e:
        logger.error('[EMAIL] Error generando PDF: %s', str(e), exc_info=True)
        return False

    # ── HTML del correo ───────────────────────────────────────────
    saldo_bloque = ''
    if saldo > 0.01:
        saldo_fmt = f"${saldo:,.0f}".replace(',', '.')
        saldo_bloque = f"""
        <div style="background:#FEF2F2;border-left:4px solid #DC2626;padding:14px 18px;
                    border-radius:4px;margin:16px 0;">
          <p style="margin:0;font-size:14px;color:#991B1B;">
            💰 <strong>Saldo pendiente: {saldo_fmt}</strong><br>
            <span style="font-size:13px;color:#7F1D1D;">
              Este monto debe cancelarse al momento de recoger tu pedido o antes del envío.
            </span>
          </p>
        </div>
        """

    cuerpo_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <body style="margin:0;padding:0;background:#F8FAFC;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#F8FAFC;padding:24px 0;">
      <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

        <!-- Cabecera -->
        <tr>
          <td style="background:#1E293B;padding:28px 32px;">
            <h1 style="color:#ffffff;margin:0;font-size:26px;letter-spacing:-0.5px;">RALOZ COL SAS</h1>
            <p style="color:#F59E0B;margin:4px 0 0;font-size:12px;letter-spacing:1px;">
              UNIFORMES ESCOLARES · BOGOTÁ, COLOMBIA
            </p>
          </td>
        </tr>

        <!-- Banda amber -->
        <tr><td style="background:#F59E0B;height:3px;"></td></tr>

        <!-- Cuerpo -->
        <tr>
          <td style="padding:32px;">
            <h2 style="color:#1E293B;margin:0 0 8px;font-size:20px;">
              ¡Gracias por tu compra, {cliente_nombre}! 🎒
            </h2>
            <p style="color:#64748B;font-size:15px;line-height:1.6;margin:0 0 20px;">
              Tu pago fue procesado exitosamente. Adjuntamos la factura
              <strong style="color:#1E293B;">{num_factura}</strong>
              como comprobante oficial de tu compra.
            </p>

            {saldo_bloque}

            <!-- Info de entrega -->
            <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
                        padding:16px 20px;margin-bottom:20px;">
              <p style="margin:0;font-size:14px;color:#92400E;font-weight:bold;">
                📦 Próximo paso: coordinación de entrega
              </p>
              <p style="margin:6px 0 0;font-size:13px;color:#78350F;line-height:1.5;">
                Nos contactaremos contigo por WhatsApp para coordinar la
                entrega de tu pedido en Bogotá. Por favor ten a mano tu
                número de factura: <strong>{num_factura}</strong>
              </p>
            </div>

            <!-- Contacto -->
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td width="50%" style="padding-right:8px;">
                  <a href="https://wa.me/573213412903" style="display:block;background:#25D366;
                     color:#fff;text-decoration:none;text-align:center;padding:12px;
                     border-radius:8px;font-size:14px;font-weight:bold;">
                    💬 WhatsApp
                  </a>
                </td>
                <td width="50%" style="padding-left:8px;">
                  <a href="mailto:ralozcol@outlook.com" style="display:block;background:#1E293B;
                     color:#fff;text-decoration:none;text-align:center;padding:12px;
                     border-radius:8px;font-size:14px;font-weight:bold;">
                    ✉️ Escribir por email
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#1E293B;padding:20px 32px;text-align:center;">
            <p style="color:#94A3B8;font-size:12px;margin:0;line-height:1.6;">
              RALOZ COL SAS · Bogotá, Colombia<br>
              +57 321 341 2903 · ralozcol@outlook.com
            </p>
            <p style="color:#475569;font-size:11px;margin:8px 0 0;">
              Este correo fue generado automáticamente. Si no realizaste esta compra,
              escríbenos de inmediato.
            </p>
          </td>
        </tr>

      </table>
      </td></tr>
    </table>
    </body>
    </html>
    """

    # ── Construir mensaje MIME (para fallback SMTP) ────────────────
    msg = MIMEMultipart('mixed')
    msg['From']     = f'{nombre_rem} <{remitente}>'
    msg['To']       = destinatario
    msg['Subject']  = f'Tu compra en RALOZ COL SAS — Factura {num_factura}'
    msg['Reply-To'] = remitente
    msg.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))

    part = MIMEBase('application', 'pdf')
    part.set_payload(pdf_buffer.read())
    encoders.encode_base64(part)
    nombre_archivo = f'Factura-{num_factura}.pdf'
    part.add_header('Content-Disposition', 'attachment', filename=nombre_archivo)
    part.add_header('Content-Type', 'application/pdf', name=nombre_archivo)
    msg.attach(part)

    # ── Enviar vía Brevo (producción) o SMTP (local) ──────────────
    brevo_key = os.getenv('BREVO_API_KEY', '').strip()

    if brevo_key:
        pdf_buffer.seek(0)
        pdf_b64 = base64.b64encode(pdf_buffer.read()).decode('utf-8')
        payload = {
            'sender':      {'name': nombre_rem, 'email': remitente},
            'to':          [{'email': destinatario}],
            'replyTo':     {'email': remitente},
            'subject':     f'Tu compra en RALOZ COL SAS — Factura {num_factura}',
            'htmlContent': cuerpo_html,
            'attachment':  [{'name': nombre_archivo, 'content': pdf_b64}],
        }
        try:
            resp = _requests.post(
                'https://api.brevo.com/v3/smtp/email',
                headers={'api-key': brevo_key, 'Content-Type': 'application/json'},
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info('[EMAIL-BREVO] Factura %s enviada a %s', num_factura, destinatario)
                return True
            else:
                logger.error('[EMAIL-BREVO] Error %s: %s', resp.status_code, resp.text[:300])
                return False
        except Exception as e:
            logger.error('[EMAIL-BREVO] Excepción: %s', str(e))
            return False
    else:
        smtp_host = os.getenv('EMAIL_SMTP_HOST', 'smtp-mail.outlook.com')
        smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(remitente, password)
                server.send_message(msg)
            logger.info('[EMAIL-SMTP] Factura %s enviada a %s', num_factura, destinatario)
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error('[EMAIL-SMTP] Error de autenticación SMTP')
            return False
        except Exception as e:
            logger.error('[EMAIL-SMTP] Error inesperado: %s', str(e))
            return False



# ══════════════════════════════════════════════════════════════════
# NOTIFICACIÓN DE LEAD AL ASESOR
# ══════════════════════════════════════════════════════════════════

def enviar_email_lead(lead_data: dict) -> bool:
    """
    Envía un email al asesor cuando llega un lead desde la tienda web.
    lead_data: dict con 'nombre', 'telefono', 'email', 'mensaje'
    """
    nombre  = lead_data.get('nombre', '—')
    telefono = lead_data.get('telefono', '—')
    email   = lead_data.get('email', '—')
    mensaje = lead_data.get('mensaje', '—')

    cuerpo_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <body style="margin:0;padding:0;background:#F8FAFC;font-family:Arial,Helvetica,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#F8FAFC;padding:24px 0;">
      <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">

        <tr>
          <td style="background:#1E293B;padding:28px 32px;">
            <h1 style="color:#ffffff;margin:0;font-size:26px;letter-spacing:-0.5px;">RALOZ COL SAS</h1>
            <p style="color:#F59E0B;margin:4px 0 0;font-size:12px;letter-spacing:1px;">
              UNIFORMES ESCOLARES · BOGOTÁ, COLOMBIA
            </p>
          </td>
        </tr>

        <tr><td style="background:#F59E0B;height:3px;"></td></tr>

        <tr>
          <td style="padding:32px;">
            <h2 style="color:#1E293B;margin:0 0 8px;font-size:20px;">
              📩 Nuevo lead desde la tienda web
            </h2>
            <p style="color:#64748B;font-size:15px;line-height:1.6;margin:0 0 24px;">
              Alguien填写的表格de cotización o asesoría. Contacta lo antes posible.
            </p>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
              <tr>
                <td width="120" style="padding:10px 0;color:#64748B;font-size:13px;">Nombre</td>
                <td style="padding:10px 0;color:#1E293B;font-size:14px;font-weight:bold;">{nombre}</td>
              </tr>
              <tr style="background:#F8FAFC;">
                <td style="padding:10px 0;color:#64748B;font-size:13px;">Teléfono</td>
                <td style="padding:10px 0;"><a href="https://wa.me/57{telefono}" style="color:#25D366;font-weight:bold;text-decoration:none;">{telefono}</a></td>
              </tr>
              <tr>
                <td style="padding:10px 0;color:#64748B;font-size:13px;">Email</td>
                <td style="padding:10px 0;"><a href="mailto:{email}" style="color:#1E293B;text-decoration:none;">{email}</a></td>
              </tr>
            </table>

            <div style="background:#F8FAFC;border-radius:8px;padding:16px 20px;">
              <p style="margin:0 0 6px;color:#64748B;font-size:13px;">Mensaje:</p>
              <p style="margin:0;color:#1E293B;font-size:14px;line-height:1.6;">{mensaje}</p>
            </div>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
              <tr>
                <td width="50%" style="padding-right:8px;">
                  <a href="https://wa.me/57{telefono}" style="display:block;background:#25D366;
                     color:#fff;text-decoration:none;text-align:center;padding:12px;
                     border-radius:8px;font-size:14px;font-weight:bold;">
                    💬 Contactar por WhatsApp
                  </a>
                </td>
                <td width="50%" style="padding-left:8px;">
                  <a href="mailto:{email}" style="display:block;background:#1E293B;
                     color:#fff;text-decoration:none;text-align:center;padding:12px;
                     border-radius:8px;font-size:14px;font-weight:bold;">
                    ✉️ Responder por email
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="background:#1E293B;padding:20px 32px;text-align:center;">
            <p style="color:#94A3B8;font-size:12px;margin:0;line-height:1.6;">
              RALOZ COL SAS · Bogotá, Colombia<br>
              +57 321 341 2903 · ralozcol@outlook.com
            </p>
            <p style="color:#475569;font-size:11px;margin:8px 0 0;">
              Este correo fue generado automáticamente desde la tienda web.
            </p>
          </td>
        </tr>

      </table>
      </td></tr>
    </table>
    </body>
    </html>
    """

    remitente = os.getenv('EMAIL_REMITENTE', 'ralozcol@outlook.com').strip()
    nombre_rem = os.getenv('EMAIL_NOMBRE', 'RALOZ COL SAS').strip()
    password   = os.getenv('EMAIL_PASSWORD', '').strip()
    destinatario = os.getenv('EMAIL_AVISO_TO', remitente).strip()

    brevo_key = os.getenv('BREVO_API_KEY', '').strip()

    if brevo_key:
        payload = {
            'sender':      {'name': nombre_rem, 'email': remitente},
            'to':          [{'email': destinatario}],
            'replyTo':     {'email': remitente},
            'subject':     f'📩 Nuevo lead: {nombre} — RALOZ COL SAS',
            'htmlContent': cuerpo_html,
        }
        try:
            resp = _requests.post(
                'https://api.brevo.com/v3/smtp/email',
                headers={'api-key': brevo_key, 'Content-Type': 'application/json'},
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                logger.info('[EMAIL-BREVO] Lead notificado: %s', nombre)
                return True
            else:
                logger.error('[EMAIL-BREVO] Error %s: %s', resp.status_code, resp.text[:300])
                return False
        except Exception as e:
            logger.error('[EMAIL-BREVO] Excepción: %s', str(e))
            return False
    else:
        msg = MIMEMultipart('mixed')
        msg['From']    = f'{nombre_rem} <{remitente}>'
        msg['To']      = destinatario
        msg['Subject'] = f'📩 Nuevo lead: {nombre} — RALOZ COL SAS'
        msg['Reply-To'] = email if email != '—' else remitente
        msg.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))
        smtp_host = os.getenv('EMAIL_SMTP_HOST', 'smtp-mail.outlook.com')
        smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(remitente, password)
                server.send_message(msg)
            logger.info('[EMAIL-SMTP] Lead notificado: %s', nombre)
            return True
        except Exception as e:
            logger.error('[EMAIL-SMTP] Error: %s', str(e))
            return False
