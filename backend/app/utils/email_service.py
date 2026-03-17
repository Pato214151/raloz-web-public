"""
RALOZ COL SAS — Servicio de Email + Generación de Factura PDF
─────────────────────────────────────────────────────────────
Genera el PDF en memoria (BytesIO) y lo envía como adjunto.
No guarda nada en disco (compatible con filesystems efímeros como Render).

Variables de entorno requeridas:
  EMAIL_REMITENTE   → tu_cuenta@gmail.com
  EMAIL_PASSWORD    → contraseña de aplicación de Gmail (16 chars)
  EMAIL_NOMBRE      → Nombre que aparece como remitente (ej. "RALOZ COL SAS")
"""

import os
import logging
import smtplib
from io import BytesIO
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

logger = logging.getLogger(__name__)

# ─── Colores de marca RALOZ ───────────────────────────────────────
COLOR_PRIMARIO   = colors.HexColor('#E65100')   # naranja oscuro
COLOR_SECUNDARIO = colors.HexColor('#FF6D00')   # naranja brillante
COLOR_ACENTO     = colors.HexColor('#FFF3E0')   # naranja muy claro (fondo)
COLOR_GRIS       = colors.HexColor('#546E7A')   # gris azulado
COLOR_GRIS_CLARO = colors.HexColor('#ECEFF1')
COLOR_TEXTO      = colors.HexColor('#212121')


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
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    estilos = getSampleStyleSheet()
    story   = []

    # ── Helpers ──────────────────────────────────────────────────
    def _v(obj, campo, default='—'):
        """Accede a atributo o clave de dict."""
        if isinstance(obj, dict):
            return obj.get(campo) or default
        return getattr(obj, campo, None) or default

    def _f(valor):
        """Formatea número como COP."""
        try:
            return f"${float(valor):,.0f}".replace(',', '.')
        except Exception:
            return '—'

    # ── Estilos personalizados ────────────────────────────────────
    st_empresa = ParagraphStyle('empresa', fontSize=20, textColor=COLOR_PRIMARIO,
                                fontName='Helvetica-Bold', spaceAfter=2)
    st_slogan  = ParagraphStyle('slogan',  fontSize=9,  textColor=COLOR_GRIS,
                                fontName='Helvetica', spaceAfter=6)
    st_titulo  = ParagraphStyle('titulo',  fontSize=14, textColor=colors.white,
                                fontName='Helvetica-Bold', alignment=TA_RIGHT)
    st_label   = ParagraphStyle('label',   fontSize=8,  textColor=COLOR_GRIS,
                                fontName='Helvetica')
    st_valor   = ParagraphStyle('valor',   fontSize=9,  textColor=COLOR_TEXTO,
                                fontName='Helvetica-Bold')
    st_th      = ParagraphStyle('th',      fontSize=8,  textColor=colors.white,
                                fontName='Helvetica-Bold', alignment=TA_CENTER)
    st_td      = ParagraphStyle('td',      fontSize=8,  textColor=COLOR_TEXTO,
                                fontName='Helvetica', alignment=TA_CENTER)
    st_td_l    = ParagraphStyle('td_l',    fontSize=8,  textColor=COLOR_TEXTO,
                                fontName='Helvetica', alignment=TA_LEFT)
    st_total_l = ParagraphStyle('tot_l',   fontSize=10, textColor=COLOR_TEXTO,
                                fontName='Helvetica-Bold', alignment=TA_RIGHT)
    st_total_v = ParagraphStyle('tot_v',   fontSize=12, textColor=COLOR_PRIMARIO,
                                fontName='Helvetica-Bold', alignment=TA_RIGHT)
    st_footer  = ParagraphStyle('footer',  fontSize=7,  textColor=COLOR_GRIS,
                                fontName='Helvetica', alignment=TA_CENTER)

    # ── CABECERA: empresa + número de factura ─────────────────────
    num_factura = _v(factura, 'numero_factura')
    fecha_str   = ''
    fecha_raw   = _v(factura, 'fecha_factura', None)
    if fecha_raw:
        if isinstance(fecha_raw, str):
            fecha_str = fecha_raw[:10]
        else:
            fecha_str = fecha_raw.strftime('%d/%m/%Y')
    else:
        fecha_str = date.today().strftime('%d/%m/%Y')

    header_data = [[
        # Columna izquierda — nombre empresa
        [Paragraph('RALOZ COL SAS', st_empresa),
         Paragraph('Uniformes Escolares — Medellín, Colombia', st_slogan)],
        # Columna derecha — número y fecha
        [Paragraph(f'FACTURA N° {num_factura}', st_titulo),
         Paragraph(f'<font color="#FFF3E0">Fecha: {fecha_str}</font>',
                   ParagraphStyle('sub', fontSize=9, textColor=colors.white,
                                  fontName='Helvetica', alignment=TA_RIGHT))],
    ]]
    header_table = Table(header_data, colWidths=[10 * cm, 7 * cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND',   (1, 0), (1, 0), COLOR_PRIMARIO),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',   (1, 0), (1, 0), 10),
        ('BOTTOMPADDING',(1, 0), (1, 0), 10),
        ('LEFTPADDING',  (1, 0), (1, 0), 12),
        ('RIGHTPADDING', (1, 0), (1, 0), 12),
        ('ROUNDEDCORNERS', (1, 0), (1, 0), [4, 4, 4, 4]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width='100%', thickness=1.5, color=COLOR_SECUNDARIO))
    story.append(Spacer(1, 0.4 * cm))

    # ── DATOS DEL CLIENTE ─────────────────────────────────────────
    story.append(Paragraph('DATOS DEL CLIENTE', ParagraphStyle(
        'sec', fontSize=9, textColor=COLOR_PRIMARIO, fontName='Helvetica-Bold',
        spaceAfter=4,
    )))

    cliente_nombre = _v(factura, 'cliente_nombre')
    cliente_email  = _v(factura, 'cliente_email')
    cliente_tel    = _v(factura, 'cliente_telefono')
    cliente_nit    = _v(factura, 'cliente_nit')
    colegio_nombre = _v(factura, 'colegio_nombre', None) or ''

    cliente_data = [
        [Paragraph('Nombre:', st_label),     Paragraph(cliente_nombre, st_valor),
         Paragraph('Colegio:', st_label),    Paragraph(colegio_nombre, st_valor)],
        [Paragraph('Email:', st_label),      Paragraph(cliente_email, st_valor),
         Paragraph('Teléfono:', st_label),   Paragraph(cliente_tel, st_valor)],
    ]
    if cliente_nit and cliente_nit != '—':
        cliente_data.append([
            Paragraph('Documento:', st_label), Paragraph(cliente_nit, st_valor),
            Paragraph('', st_label),           Paragraph('', st_valor),
        ])

    cliente_table = Table(cliente_data, colWidths=[2.5 * cm, 6.5 * cm, 2.5 * cm, 5.5 * cm])
    cliente_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), COLOR_ACENTO),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS',(0, 0), (-1, -1), [COLOR_ACENTO, colors.white]),
    ]))
    story.append(cliente_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── TABLA DE PRODUCTOS ────────────────────────────────────────
    story.append(Paragraph('DETALLE DE PRODUCTOS', ParagraphStyle(
        'sec2', fontSize=9, textColor=COLOR_PRIMARIO, fontName='Helvetica-Bold',
        spaceAfter=4,
    )))

    tabla_encabezado = [
        Paragraph('#',               st_th),
        Paragraph('Producto',        st_th),
        Paragraph('Talla',           st_th),
        Paragraph('Cant.',           st_th),
        Paragraph('Precio Unit.',    st_th),
        Paragraph('Subtotal',        st_th),
    ]
    rows = [tabla_encabezado]

    total_calculado = 0
    for i, det in enumerate(detalles, start=1):
        nombre_prod = '—'
        if isinstance(det, dict):
            nombre_prod = det.get('producto_nombre') or det.get('nombre', '—')
        else:
            nombre_prod = (det.producto.nombre if det.producto else None) or '—'

        talla    = _v(det, 'talla_individual')
        cantidad = int(_v(det, 'cantidad', 0))
        precio   = float(_v(det, 'precio_unitario', 0))
        subtotal = float(_v(det, 'total_linea', precio * cantidad))
        total_calculado += subtotal

        bg = COLOR_GRIS_CLARO if i % 2 == 0 else colors.white
        rows.append([
            Paragraph(str(i),          ParagraphStyle('n', **{**st_td.__dict__,
                                        'parent': st_td.parent})),
            Paragraph(nombre_prod,     st_td_l),
            Paragraph(talla,           st_td),
            Paragraph(str(cantidad),   st_td),
            Paragraph(_f(precio),      st_td),
            Paragraph(_f(subtotal),    st_td),
        ])

    productos_table = Table(rows, colWidths=[0.8*cm, 7.5*cm, 1.5*cm, 1.2*cm, 2.5*cm, 3.5*cm])
    table_style = [
        # Encabezado
        ('BACKGROUND',    (0, 0), (-1, 0), COLOR_PRIMARIO),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',          (0, 0), (-1, -1), 0.3, colors.HexColor('#CFD8DC')),
    ]
    # Filas alternadas
    for idx in range(1, len(rows)):
        bg = COLOR_GRIS_CLARO if idx % 2 == 0 else colors.white
        table_style.append(('BACKGROUND', (0, idx), (-1, idx), bg))

    productos_table.setStyle(TableStyle(table_style))
    story.append(productos_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── TOTAL ─────────────────────────────────────────────────────
    total_final = float(_v(factura, 'total', total_calculado))
    total_data = [[
        Paragraph('TOTAL A PAGAR:', st_total_l),
        Paragraph(_f(total_final),  st_total_v),
    ]]
    total_table = Table(total_data, colWidths=[13 * cm, 4 * cm])
    total_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), COLOR_ACENTO),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
        ('LINEABOVE',     (0, 0), (-1, 0), 2, COLOR_PRIMARIO),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── INFO DE PAGO ──────────────────────────────────────────────
    metodo = _v(factura, 'metodo_pago', 'MercadoPago')
    referencia = _v(factura, 'observaciones', '').replace('Pedido web #', '')
    story.append(Paragraph(
        f'Método de pago: <b>{metodo}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Referencia: <b>{referencia}</b>',
        ParagraphStyle('pago', fontSize=8, textColor=COLOR_GRIS, fontName='Helvetica',
                       alignment=TA_CENTER),
    ))
    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=COLOR_GRIS_CLARO))
    story.append(Spacer(1, 0.3 * cm))

    # ── PIE DE PÁGINA ─────────────────────────────────────────────
    story.append(Paragraph(
        '¡Gracias por tu compra en RALOZ COL SAS! · Medellín, Colombia · '
        'WhatsApp: <a href="https://wa.me/573213412903">+57 321 341 2903</a>',
        st_footer,
    ))
    story.append(Paragraph(
        'Este documento es generado automáticamente y tiene validez como comprobante de compra.',
        st_footer,
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
    Devuelve True si el envío fue exitoso, False si falló.

    Requiere en .env:
      EMAIL_REMITENTE  → tu_cuenta@gmail.com
      EMAIL_PASSWORD   → contraseña de aplicación de Gmail
      EMAIL_NOMBRE     → "RALOZ COL SAS" (nombre visible del remitente)
    """
    remitente  = os.getenv('EMAIL_REMITENTE', '').strip()
    password   = os.getenv('EMAIL_PASSWORD', '').strip()
    nombre_rem = os.getenv('EMAIL_NOMBRE', 'RALOZ COL SAS').strip()

    if not remitente or not password:
        logger.warning('[EMAIL] Credenciales no configuradas — EMAIL_REMITENTE o EMAIL_PASSWORD vacíos')
        return False

    def _v(obj, campo, default='—'):
        if isinstance(obj, dict):
            return obj.get(campo) or default
        return getattr(obj, campo, None) or default

    num_factura    = _v(factura, 'numero_factura')
    cliente_nombre = _v(factura, 'cliente_nombre')

    # ── Generar PDF ────────────────────────────────────────────────
    try:
        pdf_buffer = generar_pdf_factura(factura, detalles)
    except Exception as e:
        logger.error('[EMAIL] Error generando PDF: %s', str(e))
        return False

    # ── Construir mensaje ─────────────────────────────────────────
    msg = MIMEMultipart('mixed')
    msg['From']    = f'{nombre_rem} <{remitente}>'
    msg['To']      = destinatario
    msg['Subject'] = f'Tu compra en RALOZ COL SAS — Factura {num_factura}'
    msg['Reply-To'] = remitente

    cuerpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #212121; max-width: 600px; margin: 0 auto;">

      <div style="background: #E65100; padding: 24px 32px; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 24px;">RALOZ COL SAS</h1>
        <p style="color: #FFE0B2; margin: 4px 0 0 0; font-size: 13px;">Uniformes Escolares — Medellín</p>
      </div>

      <div style="background: #FFF3E0; padding: 24px 32px;">
        <h2 style="color: #E65100; margin-top: 0;">¡Gracias por tu compra, {cliente_nombre}!</h2>
        <p style="font-size: 15px; line-height: 1.6;">
          Tu pago fue procesado exitosamente. Adjuntamos la factura <strong>{num_factura}</strong>
          como comprobante de tu compra.
        </p>

        <div style="background: white; border-left: 4px solid #E65100; padding: 16px 20px;
                    border-radius: 4px; margin: 20px 0;">
          <p style="margin: 0; font-size: 14px; color: #546E7A;">
            📦 <strong>Próximo paso:</strong> Nos contactaremos contigo para coordinar la
            <strong>entrega del pedido</strong> en Medellín.
          </p>
        </div>

        <p style="font-size: 14px; color: #546E7A;">
          Si tienes alguna pregunta, escríbenos por WhatsApp:
          <a href="https://wa.me/573213412903" style="color: #E65100; font-weight: bold;">
            +57 321 341 2903
          </a>
        </p>
      </div>

      <div style="background: #ECEFF1; padding: 16px 32px; border-radius: 0 0 8px 8px;
                  text-align: center;">
        <p style="color: #90A4AE; font-size: 12px; margin: 0;">
          RALOZ COL SAS · Medellín, Colombia · uniformes escolares de calidad
        </p>
      </div>

    </body>
    </html>
    """

    msg.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))

    # ── Adjuntar PDF ──────────────────────────────────────────────
    part = MIMEBase('application', 'pdf')
    part.set_payload(pdf_buffer.read())
    encoders.encode_base64(part)
    nombre_archivo = f'Factura-{num_factura}.pdf'
    part.add_header('Content-Disposition', 'attachment', filename=nombre_archivo)
    part.add_header('Content-Type', 'application/pdf', name=nombre_archivo)
    msg.attach(part)

    # ── Enviar via SMTP Gmail ─────────────────────────────────────
    try:
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.login(remitente, password)
            server.send_message(msg)
        logger.info('[EMAIL] Factura %s enviada a %s', num_factura, destinatario)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error('[EMAIL] Error de autenticación — verifica EMAIL_REMITENTE y EMAIL_PASSWORD')
        return False
    except smtplib.SMTPException as e:
        logger.error('[EMAIL] Error SMTP: %s', str(e))
        return False
    except Exception as e:
        logger.error('[EMAIL] Error inesperado: %s', str(e))
        return False
