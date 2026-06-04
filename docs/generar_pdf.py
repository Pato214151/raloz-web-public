"""
Genera el documento PDF de arquitectura (descargable) a partir de los
diagramas Mermaid del proyecto. Crea dos PDFs: español e inglés.

Uso:
    cd "sofware raloz/raloz-web/docs"
    python generar_pdf.py

Requiere: reportlab (ya viene con el backend) e internet (renderiza los
diagramas con mermaid.ink). No necesita pg_dump ni navegador.
Salida: RALOZ_Arquitectura_ES.pdf  y  RALOZ_Architecture_EN.pdf
"""

import re
import base64
import tempfile
import urllib.request
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
)
from reportlab.lib.utils import ImageReader

AQUI = Path(__file__).parent
NAVY = colors.HexColor("#1d3a8a")
GOLD = colors.HexColor("#f6c23d")
GRIS = colors.HexColor("#555555")


def render_diagramas(md_file: Path, tmp: Path):
    """Renderiza cada bloque ```mermaid a PNG con mermaid.ink. Devuelve rutas."""
    texto = md_file.read_text(encoding="utf-8")
    bloques = re.findall(r"```mermaid\n(.*?)```", texto, re.DOTALL)
    rutas = []
    for i, b in enumerate(bloques):
        data = base64.urlsafe_b64encode(b.strip().encode("utf-8")).decode("ascii")
        url = "https://mermaid.ink/img/" + data + "?type=png&bgColor=ffffff"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        out = tmp / f"diag_{i}.png"
        with urllib.request.urlopen(req, timeout=40) as r:
            out.write_bytes(r.read())
        rutas.append(out)
    return rutas


def img_ajustada(ruta: Path, max_w: float):
    """Imagen escalada al ancho disponible, conservando proporción."""
    iw, ih = ImageReader(str(ruta)).getSize()
    w = min(max_w, iw)
    h = w * ih / iw
    max_h = 16 * cm
    if h > max_h:
        h = max_h
        w = h * iw / ih
    return Image(str(ruta), width=w, height=h)


def construir(md_file: Path, salida: Path, T: dict):
    tmp = Path(tempfile.mkdtemp())
    diagramas = render_diagramas(md_file, tmp)

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=NAVY, fontSize=18, spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=NAVY, fontSize=13, spaceBefore=14, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10, leading=15, textColor=colors.HexColor("#222222"))
    cap = ParagraphStyle("cap", parent=body, fontSize=9, textColor=GRIS, alignment=TA_CENTER, spaceBefore=4)
    title = ParagraphStyle("title", parent=styles["Title"], textColor=NAVY, fontSize=26)
    sub = ParagraphStyle("sub", parent=body, fontSize=11, textColor=GRIS, alignment=TA_CENTER)

    doc = SimpleDocTemplate(
        str(salida), pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title=T["doc_title"], author="RALOZ COL S.A.S",
    )
    avail = doc.width
    E = []

    # ── Portada ──
    E += [Spacer(1, 3 * cm)]
    E += [Paragraph("RALOZ COL S.A.S", title)]
    E += [Spacer(1, 0.3 * cm), Paragraph(T["doc_title"], sub)]
    E += [Spacer(1, 0.2 * cm), Paragraph(T["tagline"], sub)]
    E += [Spacer(1, 1.2 * cm)]

    metr = [[T["metric"], T["value"]]] + T["metrics"]
    t = Table(metr, colWidths=[avail * 0.55, avail * 0.45])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f3ec")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    E += [t, PageBreak()]

    # ── Resumen ──
    E += [Paragraph(T["overview_h"], h1), Paragraph(T["overview_p"], body)]

    # ── Secciones con diagramas ──
    secciones = [
        ("arch_h", "arch_p", 0),
        ("data_h", "data_p", 1),
        ("flow_h", "flow_p", 2),
        ("bot_h", "bot_p", 3),
        ("deploy_h", "deploy_p", 4),
    ]
    for hk, pk, idx in secciones:
        E += [Spacer(1, 0.4 * cm), Paragraph(T[hk], h2), Paragraph(T[pk], body), Spacer(1, 0.2 * cm)]
        if idx < len(diagramas):
            E += [img_ajustada(diagramas[idx], avail), Paragraph(T[hk], cap)]

    # ── Stack ──
    E += [PageBreak(), Paragraph(T["stack_h"], h1)]
    st = [[T["layer"], T["tech"]]] + T["stack"]
    ts = Table(st, colWidths=[avail * 0.32, avail * 0.68])
    ts.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f3ec")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    E += [ts]

    # ── Seguridad ──
    E += [Spacer(1, 0.5 * cm), Paragraph(T["sec_h"], h1)]
    for item in T["sec"]:
        E += [Paragraph("&bull; " + item, body)]

    doc.build(E)
    print(f"  PDF generado: {salida.name}")


# ─────────────────────────────────────────────────────────────────
ES = {
    "doc_title": "Arquitectura del Sistema",
    "tagline": "Plataforma full-stack de comercio electronico para uniformes escolares",
    "metric": "Metrica", "value": "Valor",
    "metrics": [
        ["Lineas de codigo", "~23.000"],
        ["Backend (Flask)", "8.000 LOC - 20 modulos - 25 modelos"],
        ["Panel admin (React)", "9.200 LOC - 19 dominios de UI"],
        ["Tienda publica (JS)", "6.000 LOC - PWA offline"],
        ["Integraciones", "MercadoPago - Brevo - Google OAuth - WhatsApp"],
        ["Despliegue", "Render - Cloudflare Pages - Supabase"],
    ],
    "overview_h": "Que es",
    "overview_p": "Sistema integral para un negocio real de confeccion y venta de uniformes "
        "escolares en Bogota. Cubre todo el ciclo: catalogo, compra online, pago, facturacion, "
        "inventario, fabricacion bajo pedido, entrega y soporte. Se compone de tres aplicaciones "
        "que comparten un unico backend: la tienda publica (sitio estatico), el panel admin/POS "
        "(SPA en React) y el backend (API REST en Flask).",
    "arch_h": "Arquitectura general",
    "arch_p": "Tres frontends y un backend central. La tienda publica consume endpoints sin "
        "autenticacion; el panel admin usa JWT. El backend integra base de datos, pagos, correo y "
        "el bot de WhatsApp.",
    "data_h": "Modelo de datos",
    "data_p": "Entidades principales y sus relaciones. Los precios se guardan por grupo de talla y "
        "el stock por talla individual; un pedido web genera factura al pagarse y, si requiere "
        "confeccion, un pedido de fabricacion.",
    "flow_h": "Flujo estrella: compra online",
    "flow_p": "El precio se calcula en el servidor (no se confia en el cliente). Tras el pago, el "
        "webhook de MercadoPago (con firma HMAC) crea la factura, descuenta stock, envia el PDF por "
        "correo y notifica al cliente por WhatsApp.",
    "bot_h": "Bot de WhatsApp",
    "bot_p": "Contestador con estado por usuario (menu, soporte, garantia) y avisos automaticos del "
        "estado del pedido. Reutiliza la tienda web para la compra en lugar de duplicarla.",
    "deploy_h": "Despliegue",
    "deploy_p": "Despliegue continuo desde GitHub: el backend y el panel a Render, la tienda a "
        "Cloudflare Pages, y la base de datos en Supabase.",
    "stack_h": "Stack tecnologico",
    "layer": "Capa", "tech": "Tecnologia",
    "stack": [
        ["Tienda publica", "HTML5, CSS3, JavaScript (ES Modules), Service Worker (PWA offline)"],
        ["Panel admin", "React 18, Vite, React Router, Axios (rutas protegidas por rol)"],
        ["Backend", "Python, Flask, SQLAlchemy (API REST, 1 blueprint por dominio)"],
        ["Auth", "Flask-JWT-Extended, bcrypt, Google OAuth, lista negra de tokens"],
        ["Base de datos", "PostgreSQL (Supabase), SSL"],
        ["Pagos", "MercadoPago (preferencias + webhooks con firma HMAC)"],
        ["Email", "Brevo API + ReportLab (PDF en memoria)"],
        ["Infra", "Render, Cloudflare Pages, Docker Compose"],
    ],
    "sec_h": "Seguridad (auditoria realizada y corregida)",
    "sec": [
        "Autenticacion JWT con bloqueo de cuenta y logout real (lista negra de tokens).",
        "Autorizacion por rol; los datos financieros solo para administrador.",
        "Precio calculado en el servidor y webhook de pago con firma HMAC e idempotencia.",
        "Rate limiting, CORS restringido, headers de seguridad (HSTS, CSP) y SRI en CDNs.",
        "Anti-XSS (sanitizacion) y anti-inyeccion SQL (consultas parametrizadas).",
        "Secretos solo en variables de entorno y respaldos automaticos de la base de datos.",
    ],
}

EN = {
    "doc_title": "System Architecture",
    "tagline": "Full-stack e-commerce platform for school uniforms",
    "metric": "Metric", "value": "Value",
    "metrics": [
        ["Lines of code", "~23,000"],
        ["Backend (Flask)", "8,000 LOC - 20 modules - 25 models"],
        ["Admin panel (React)", "9,200 LOC - 19 UI domains"],
        ["Public store (JS)", "6,000 LOC - offline PWA"],
        ["Integrations", "MercadoPago - Brevo - Google OAuth - WhatsApp"],
        ["Deployment", "Render - Cloudflare Pages - Supabase"],
    ],
    "overview_h": "What it is",
    "overview_p": "An end-to-end system for a real school-uniform manufacturing and retail business "
        "in Bogota, Colombia. It covers the full lifecycle: catalog, online purchase, payment, "
        "invoicing, inventory, made-to-order production, delivery and support. It is made of three "
        "applications sharing a single backend: the public store (static site), the admin/POS panel "
        "(React SPA) and the backend (Flask REST API).",
    "arch_h": "High-level architecture",
    "arch_p": "Three frontends and one central backend. The public store calls unauthenticated "
        "endpoints; the admin panel uses JWT. The backend integrates the database, payments, email "
        "and the WhatsApp bot.",
    "data_h": "Data model",
    "data_p": "Core entities and their relationships. Prices are stored per size group and stock per "
        "individual size; a web order creates an invoice on payment and, if it needs production, a "
        "manufacturing order.",
    "flow_h": "Core flow: online purchase",
    "flow_p": "Price is computed server-side (the client price is never trusted). After payment, the "
        "MercadoPago webhook (HMAC-signed) creates the invoice, decrements stock, emails the PDF and "
        "notifies the customer over WhatsApp.",
    "bot_h": "WhatsApp bot",
    "bot_p": "Per-user stateful auto-responder (menu, support, warranty) plus automatic order-status "
        "updates. It reuses the web store for checkout instead of duplicating it.",
    "deploy_h": "Deployment",
    "deploy_p": "Continuous deployment from GitHub: backend and panel to Render, the store to "
        "Cloudflare Pages, and the database on Supabase.",
    "stack_h": "Tech stack",
    "layer": "Layer", "tech": "Technology",
    "stack": [
        ["Public store", "HTML5, CSS3, JavaScript (ES Modules), Service Worker (offline PWA)"],
        ["Admin panel", "React 18, Vite, React Router, Axios (role-based protected routes)"],
        ["Backend", "Python, Flask, SQLAlchemy (REST API, one blueprint per domain)"],
        ["Auth", "Flask-JWT-Extended, bcrypt, Google OAuth, token blocklist"],
        ["Database", "PostgreSQL (Supabase), SSL"],
        ["Payments", "MercadoPago (preferences + HMAC-signed webhooks)"],
        ["Email", "Brevo API + ReportLab (in-memory PDF)"],
        ["Infra", "Render, Cloudflare Pages, Docker Compose"],
    ],
    "sec_h": "Security (audited and remediated)",
    "sec": [
        "JWT authentication with account lockout and real logout (token blocklist).",
        "Role-based authorization; financial data is admin-only.",
        "Server-side price computation and HMAC-signed, idempotent payment webhook.",
        "Rate limiting, restricted CORS, security headers (HSTS, CSP) and SRI on CDNs.",
        "Anti-XSS (sanitization) and anti-SQL-injection (parameterized queries).",
        "Secrets only in environment variables and automated database backups.",
    ],
}


if __name__ == "__main__":
    print("Generando PDFs (renderizando diagramas con mermaid.ink)...")
    construir(AQUI / "ARQUITECTURA.md", AQUI / "RALOZ_Arquitectura_ES.pdf", ES)
    construir(AQUI / "ARCHITECTURE.md", AQUI / "RALOZ_Architecture_EN.pdf", EN)
    print("Listo.")
