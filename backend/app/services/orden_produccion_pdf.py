"""
Genera el PDF de una Orden de Producción (confección) en memoria (BytesIO),
listo para imprimir y mandar al taller. Reusa la estética del PDF de facturas.

El logo del colegio se busca en app/static/logos/ por el nombre del colegio
(slug en minúsculas, sin tildes/espacios). Si no hay logo, se omite sin fallar.
"""

import os
import re
import unicodedata
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

_LOGOS_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'logos')

C_HEADER_BG  = colors.HexColor('#1E293B')   # slate-800
C_AMBER      = colors.HexColor('#F59E0B')   # amber-500
C_AMBER_DARK = colors.HexColor('#92400E')   # amber-800
C_AMBER_LIGHT = colors.HexColor('#FFFBEB')  # amber-50
C_SLATE_100  = colors.HexColor('#F1F5F9')
C_SLATE_500  = colors.HexColor('#64748B')
C_TEXT       = colors.HexColor('#0F172A')
C_WHITE      = colors.white


def _slug(texto):
    t = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]', '', t.lower())


def _logo_colegio(nombre_colegio):
    """Devuelve la ruta del logo del colegio, o None si no existe."""
    try:
        if not os.path.isdir(_LOGOS_DIR):
            return None
        slug = _slug(nombre_colegio)
        if not slug:
            return None
        for f in os.listdir(_LOGOS_DIR):
            if not f.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
            stem = _slug(os.path.splitext(f)[0])
            if stem and (stem in slug or slug in stem):
                return os.path.join(_LOGOS_DIR, f)
    except Exception:
        return None
    return None


def _money(v):
    try:
        return f"${float(v):,.0f}".replace(',', '.')
    except Exception:
        return '—'


def generar_pdf_orden(orden) -> BytesIO:
    """orden: objeto OrdenProduccion o su dict (to_dict())."""
    d = orden if isinstance(orden, dict) else orden.to_dict()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.6 * cm, rightMargin=1.6 * cm,
        topMargin=1.4 * cm, bottomMargin=1.4 * cm,
    )
    styles = getSampleStyleSheet()
    h_title = ParagraphStyle('t', parent=styles['Normal'], fontSize=18, leading=20,
                             textColor=C_WHITE, fontName='Helvetica-Bold')
    h_sub = ParagraphStyle('s', parent=styles['Normal'], fontSize=10, leading=12,
                           textColor=C_AMBER, fontName='Helvetica-Bold')
    sec = ParagraphStyle('sec', parent=styles['Normal'], fontSize=11, leading=13,
                         textColor=C_WHITE, fontName='Helvetica-Bold')
    normal = ParagraphStyle('n', parent=styles['Normal'], fontSize=9.5, leading=13, textColor=C_TEXT)
    small = ParagraphStyle('sm', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=C_SLATE_500)

    story = []
    ancho = doc.width

    # ── Cabecera: logo RALOZ-texto + datos + logo colegio ──
    izq = [
        Paragraph('RALOZ COL S.A.S', h_title),
        Paragraph('ORDEN DE PRODUCCIÓN', h_sub),
        Paragraph(f"{d['numero_fmt']} &nbsp;·&nbsp; {d.get('estado','').upper()}",
                  ParagraphStyle('x', parent=normal, textColor=C_WHITE, fontSize=9)),
    ]
    logo_path = _logo_colegio(d.get('nombre_colegio'))
    if logo_path:
        try:
            der = RLImage(logo_path, width=2.4 * cm, height=2.4 * cm, kind='proportional')
        except Exception:
            der = Paragraph('', normal)
    else:
        der = Paragraph('', normal)

    cab = Table([[izq, der]], colWidths=[ancho - 3 * cm, 3 * cm])
    cab.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_HEADER_BG),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (0, 0), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (1, 0), (1, 0), 10),
    ]))
    story.append(cab)
    story.append(Spacer(1, 10))

    # ── Datos generales ──
    def kv(k, v):
        return [Paragraph(f"<b>{k}</b>", normal), Paragraph(str(v or '—'), normal)]
    datos = Table([
        kv('Prenda', d.get('prenda')) + kv('Fecha', (d.get('fecha') or '')[:10]),
        kv('Colegio', d.get('nombre_colegio')) + kv('Entrega', (d.get('fecha_entrega') or '—')),
        kv('Taller', d.get('taller')) + kv('Total prendas', d.get('total_prendas')),
    ], colWidths=[ancho * 0.16, ancho * 0.34, ancho * 0.16, ancho * 0.34])
    datos.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, C_SLATE_100),
    ]))
    story.append(datos)
    story.append(Spacer(1, 10))

    def seccion(titulo):
        t = Table([[Paragraph(titulo, sec)]], colWidths=[ancho])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), C_AMBER_DARK),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        return t

    # ── Insumos ──
    story.append(seccion('MATERIALES / INSUMOS'))
    story.append(Spacer(1, 4))
    ins = [[Paragraph('<b>Insumo</b>', normal), Paragraph('<b>Especificación</b>', normal),
            Paragraph('<b>Cantidad</b>', normal), Paragraph('<b>Unidad</b>', normal),
            Paragraph('<b>Observación</b>', normal)]]
    for it in (d.get('insumos') or []):
        ins.append([
            Paragraph(str(it.get('insumo') or ''), normal),
            Paragraph(str(it.get('especificacion') or ''), normal),
            Paragraph(str(it.get('cantidad') or ''), normal),
            Paragraph(str(it.get('unidad') or ''), normal),
            Paragraph(str(it.get('observacion') or ''), normal),
        ])
    if len(ins) == 1:
        ins.append([Paragraph('—', small)] + [Paragraph('', small)] * 4)
    t_ins = Table(ins, colWidths=[ancho * 0.22, ancho * 0.30, ancho * 0.14, ancho * 0.12, ancho * 0.22])
    t_ins.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), C_SLATE_100),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_ins)
    story.append(Spacer(1, 10))

    # ── Tallas ──
    story.append(seccion('TALLAS Y CANTIDADES'))
    story.append(Spacer(1, 4))
    tallas = d.get('tallas') or []
    fila_t = [Paragraph('<b>Talla</b>', normal)] + [Paragraph(f"<b>{t.get('talla','')}</b>", normal) for t in tallas] + [Paragraph('<b>TOTAL</b>', normal)]
    fila_c = [Paragraph('Cant.', normal)] + [Paragraph(str(t.get('cantidad', '')), normal) for t in tallas] + [Paragraph(f"<b>{d.get('total_prendas',0)}</b>", normal)]
    if not tallas:
        fila_t = [Paragraph('<b>Talla</b>', normal), Paragraph('<b>TOTAL</b>', normal)]
        fila_c = [Paragraph('Cant.', normal), Paragraph('0', normal)]
    t_tallas = Table([fila_t, fila_c])
    t_tallas.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 0), (-1, 0), C_SLATE_100),
        ('BACKGROUND', (-1, 0), (-1, -1), C_AMBER_LIGHT),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_tallas)
    story.append(Spacer(1, 10))

    # ── Logo ──
    story.append(seccion('LOGO / MARCA'))
    story.append(Spacer(1, 4))
    logo_tbl = Table([
        kv('Descripción', d.get('logo_descripcion')) + kv('Técnica', d.get('logo_tecnica')),
        kv('Ubicación', d.get('logo_ubicacion')) + kv('Tamaño', d.get('logo_tamano')),
    ], colWidths=[ancho * 0.16, ancho * 0.34, ancho * 0.16, ancho * 0.34])
    logo_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(logo_tbl)
    story.append(Spacer(1, 10))

    # ── Observaciones ──
    if d.get('observaciones'):
        story.append(seccion('OBSERVACIONES'))
        story.append(Spacer(1, 4))
        story.append(Paragraph(str(d['observaciones']).replace('\n', '<br/>'), normal))
        story.append(Spacer(1, 10))

    # ── Costos ──
    if d.get('costo_total'):
        story.append(seccion('COSTOS'))
        story.append(Spacer(1, 4))
        c = Table([
            [Paragraph('Tela', normal), Paragraph(_money(d.get('costo_tela')), normal)],
            [Paragraph('Insumos', normal), Paragraph(_money(d.get('costo_insumos')), normal)],
            [Paragraph('Mano de obra', normal), Paragraph(_money(d.get('costo_mano_obra')), normal)],
            [Paragraph('<b>TOTAL</b>', normal), Paragraph(f"<b>{_money(d.get('costo_total'))}</b>", normal)],
        ], colWidths=[ancho * 0.5, ancho * 0.5])
        c.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
            ('BACKGROUND', (0, -1), (-1, -1), C_AMBER_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(c)
        story.append(Spacer(1, 16))

    # ── Firmas ──
    firmas = Table([
        [Paragraph('_______________________<br/>Pedido por', small),
         Paragraph('_______________________<br/>Recibido (taller)', small)],
    ], colWidths=[ancho * 0.5, ancho * 0.5])
    firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('TOPPADDING', (0, 0), (-1, -1), 18),
    ]))
    story.append(firmas)

    doc.build(story)
    buffer.seek(0)
    return buffer
