"""
Textos y lógica del bot RALOZ.

👉 Para cambiar lo que responde el bot, edita los textos de abajo.
   (Las *negritas* de WhatsApp se escriben con *asteriscos*.)

construir_respuesta() devuelve un objeto Respuesta(texto, aviso_admin):
  - texto       = lo que se le responde al cliente
  - aviso_admin = mensaje opcional para el asesor/admin (o None)
"""

import logging
import os
import re
import unicodedata
from collections import namedtuple

import requests

from app.bot.state import get_estado, set_estado, reset_estado, set_dato, get_dato

logger = logging.getLogger("raloz-bot.responses")


# ─── Helpers: guardar lead cuando el cliente pide un asesor ────────────

def _guardar_lead(chat_id: str, texto: str):
    """Registra al cliente como lead en el backend cuando pide un asesor.
    No bloquea la respuesta al cliente; si falla, solo se loguea."""
    if not WA_LOG_TOKEN:
        return
    try:
        requests.post(
            f"{BACKEND_URL}/api/tienda/lead",
            headers={"X-Bot-Token": WA_LOG_TOKEN},
            json={
                "nombre":   "",
                "telefono": chat_id,
                "email":    "",
                "mensaje":  f"[WhatsApp] Cliente pidió hablar con un asesor: {texto[:500]}",
                "origen":   "whatsapp",
            },
            timeout=10,
        )
    except Exception as e:
        logger.warning("No se pudo guardar lead para %s: %s", chat_id, e)

# URL del backend (para pedir el link de pago del saldo)
BACKEND_URL = os.getenv("BACKEND_URL", "https://raloz-web.onrender.com").rstrip("/")
# Secreto compartido con el backend (para guardar citas). El mismo del bot.
WA_LOG_TOKEN = os.getenv("WA_LOG_TOKEN", "").strip()


# ─── Llamadas al backend (helpers comunes: un solo try/except y con log) ───

def _get_backend_json(path: str, timeout: int, headers: dict = None):
    """GET al backend. Devuelve el dict del JSON, o None si falló (y lo loguea)."""
    url = f"{BACKEND_URL}{path}"
    try:
        r = requests.get(url, headers=headers or {}, timeout=timeout)
    except Exception as e:
        logger.warning("Backend GET %s falló: %s", path, e)
        return None
    if r.status_code != 200:
        logger.warning("Backend GET %s respondió %s", path, r.status_code)
        return None
    try:
        return r.json()
    except Exception:
        logger.warning("Backend GET %s devolvió un cuerpo no-JSON", path)
        return None


def _post_backend(path: str, payload: dict, timeout: int, headers: dict = None):
    """POST al backend. Devuelve (status_code, data). Si no hubo conexión,
    devuelve (None, {}) — los callers distinguen 'sin conexión' de 'respuesta
    con error' porque los textos al cliente son distintos."""
    url = f"{BACKEND_URL}{path}"
    try:
        r = requests.post(url, json=payload, headers=headers or {}, timeout=timeout)
    except Exception as e:
        logger.warning("Backend POST %s falló: %s", path, e)
        return None, {}
    try:
        data = r.json() if "application/json" in r.headers.get("content-type", "") else {}
    except Exception:
        data = {}
    if r.status_code >= 300:
        logger.info("Backend POST %s respondió %s (code=%s)", path, r.status_code, data.get("code"))
    return r.status_code, data


def _solicitar_link_saldo(referencia: str) -> str:
    """Llama al backend para generar el link de pago del saldo y arma el mensaje."""
    status, data = _post_backend("/api/tienda/pagar-saldo",
                                 {"referencia": referencia}, timeout=20)
    if status is None:
        return "😕 No pude conectar para generar tu link ahora. Intenta de nuevo en un momento."

    if status == 200 and data.get("pago_url"):
        monto = data.get("monto")
        monto_txt = (f"${int(monto):,}".replace(",", ".")) if monto else ""
        return (
            f"💰 Aquí está tu link para pagar el saldo{(' de ' + monto_txt) if monto_txt else ''}:\n"
            f"👉 {data['pago_url']}\n\n"
            "_Guárdalo; puedes usarlo cuando quieras. Cuando pagues, te confirmo por aquí._"
        )

    code = (data or {}).get("code")
    if code == "no_encontrado":
        return (
            "🤔 No encontré un pedido en línea con esa referencia.\n"
            "Verifícala (ej: *RALOZ-ABC123*) e intenta de nuevo.\n\n"
            "Si compraste en el *punto físico*, esa factura no tiene link de pago en línea. "
            "Escribe *asesor* y una persona te ayuda. 🙌"
        )
    if code == "sin_saldo":
        return "✅ ¡Buenas noticias! Ese pedido ya está pagado completamente. 🎓"
    if code == "en_produccion":
        return "🧵 Tu pedido aún se está fabricando. Te avisaré por aquí cuando esté listo para pagar el saldo."
    return "😕 No pude generar el link ahora. Intenta más tarde o escríbenos a un asesor."

# aviso_admin opcional · handoff=True pide pasar el chat a un asesor humano
Respuesta = namedtuple("Respuesta", ["texto", "aviso_admin", "handoff"],
                       defaults=(None, False))


# ─── CONSULTA DE PRECIOS Y STOCK (llama al catálogo del backend) ────
# id de cada colegio en la base (ver /api/tienda/colegios)
COLEGIOS = {"marillac": (1, "Marillac"), "marilac": (1, "Marillac"),
            "marrilla": (1, "Marillac"), "marilla": (1, "Marillac"), "marillac": (1, "Marillac"),
            "adventista": (2, "Adventista"), "adbentista": (2, "Adventista"),
            "manyanet": (3, "Manyanet"), "manyannet": (3, "Manyanet"), "manyanette": (3, "Manyanet")}


def _detectar_colegio(t: str):
    for clave, (idc, nombre) in COLEGIOS.items():
        if clave in t:
            return idc, nombre
    return None, None


def _detectar_talla(t: str):
    m = re.search(r"\b(\d{1,2}|xl|xs|s|m|l)\b", t)
    return m.group(1).upper() if m else None


_PALABRAS_DIA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado",
                 "hoy", "manana", "pasado", "proxim", "entrante", "fin de semana",
                 "esta semana", "este ", "el finde", "festivo"]


def _parece_dia(t: str) -> bool:
    """True si el texto parece indicar un día (para no guardar una frase suelta
    como si fuera la fecha de la cita)."""
    if any(w in t for w in _PALABRAS_DIA):
        return True
    # una fecha con número: "8 de julio", "el 15", "15/7"
    if re.search(r"\b\d{1,2}\b", t):
        return True
    return False


def _coincide_genero(nombre_prenda: str, genero: str) -> bool:
    """¿La prenda corresponde al género pedido? 'ambos' muestra todo; las prendas
    sin marca de género (Blazer, Chaleco...) se muestran para niño y para niña."""
    if genero == "ambos":
        return True
    n = _norm(nombre_prenda)
    es_nino = "nino" in n
    es_nina = "nina" in n
    if not es_nino and not es_nina:
        return True  # prenda unisex
    return es_nino if genero == "nino" else es_nina


def _consultar_precios(id_colegio: int, nombre_colegio: str, talla: str,
                       genero: str = "ambos", producto: str = None) -> str:
    """Pide el catálogo del colegio al backend y arma la respuesta para una talla,
    un género ('nino' | 'nina' | 'ambos') y, opcionalmente, una prenda puntual."""
    data = _get_backend_json(f"/api/tienda/catalogo/{id_colegio}", timeout=90)
    if not data:
        return ("😕 No pude consultar los precios en este momento. "
                "Intenta de nuevo en un momento o míralos en la tienda 👉 " + TIENDA_URL)

    talla = talla.upper()
    prod = _norm(producto) if producto else None
    encontrados = []  # (nombre, precio, stock)
    for p in data.get("productos", []):
        if not _coincide_genero(p["nombre"], genero):
            continue
        for tt in p.get("tallas", []):
            if str(tt["talla"]).upper() == talla:
                encontrados.append((p["nombre"], tt["precio"], tt["stock"]))
                break

    etiqueta_gen = {"nino": " · niño", "nina": " · niña"}.get(genero, "")
    nota = ""
    if prod:
        terminos = _terminos_producto(prod)
        filtrados = [e for e in encontrados if any(term in _norm(e[0]) for term in terminos)]
        if filtrados:
            encontrados = filtrados
        else:
            nota = f"🤔 No encontré *{producto}* en talla *{talla}*. Te muestro lo demás:\n\n"

    if not encontrados:
        return (f"🤔 No encontré prendas en talla *{talla}*{etiqueta_gen} para *{nombre_colegio}*.\n"
                "¿Seguro es esa talla? También puedes ver todo en la tienda 👉 " + TIENDA_URL)

    def _linea(n, pr):
        return f"• {n} — " + f"${int(pr):,}".replace(",", ".")
    disp = [_linea(n, pr) for (n, pr, st) in encontrados if st > 0]
    encargo = [_linea(n, pr) for (n, pr, st) in encontrados if st <= 0]

    partes = [nota + f"🏷️ *Precios {nombre_colegio} · talla {talla}{etiqueta_gen}*\n"]
    if disp:
        partes.append("✅ *Disponible ahora:*\n" + "\n".join(disp))
    if encargo:
        partes.append("\n🧵 *Por encargo* (demora aprox. 1 a 2 meses):\n" + "\n".join(encargo))
    _slug = {1: "marillac", 2: "adventista", 3: "manyanet"}.get(id_colegio, "")
    _prenda_q = ("&prenda=" + prod.split()[0]) if (_slug and prod) else ""
    _link = TIENDA_URL + ("/?colegio=" + _slug + _prenda_q if _slug else "")
    partes.append("\n🛒 *Cómpralo en línea* 👉 " + _link +
                  "\nPagas por *link seguro* (MercadoPago), te *reservamos la talla* "
                  "y te llega la *factura* al correo. 🧾"
                  "\n_O acércate al punto para medir la talla._")
    return "\n".join(partes)


PEDIR_COLEGIO_PRECIO = (
    "🏷️ *Precios y disponibilidad*\n\n"
    "¿De cuál colegio es el uniforme? Escribe *Marillac*, *Adventista* o *Manyanet*."
)
PEDIR_TALLA_PRECIO = "👍 Perfecto. ¿Qué *talla* necesitas? (ej: *16*, *10*, *S*, *M*...)"
PEDIR_GENERO_PRECIO = (
    "👦👧 ¿El uniforme es para *niño*, *niña* o *ambos*?\n"
    "Escribe *niño*, *niña* o *ambos*."
)


def _detectar_genero(t: str):
    """Devuelve 'nino' | 'nina' | 'ambos' | None a partir del texto (ya normalizado)."""
    if "ambos" in t or "los dos" in t or "todo" in t:
        return "ambos"
    if "nina" in t or "niña" in t or "mujer" in t or "hembra" in t:
        return "nina"
    if "nino" in t or "niño" in t or "hombre" in t or "varon" in t:
        return "nino"
    return None


# Prendas que el cliente puede nombrar. El orden importa: los más específicos
# van primero (pantaloneta antes que pantalon, uniforme completo antes que uniforme).
_PRODUCTOS = ["pantaloneta", "uniforme completo", "jardinera", "blusa", "camiseta",
              "camisa", "blazer", "chaleco", "chaqueta", "sudadera", "medias",
              "pantalon", "buzo", "falda", "saco", "corbata", "uniforme"]


def _detectar_producto(t: str):
    """Devuelve la prenda mencionada (ej: 'jardinera') o None."""
    for p in _PRODUCTOS:
        if p in t:
            return p
    return None


# Sinónimos coloquiales → términos que SÍ aparecen en los nombres reales.
# Ej: la gente dice "sudadera" y se refiere al uniforme de Educación Física.
_SINONIMOS = {
    "sudadera": ["fisica", "pantaloneta"],
    "buzo": ["camiseta ed", "chaqueta ed", "fisica"],
    "saco": ["chaqueta", "chaleco"],
    "camibuso": ["camiseta"],
    "camisilla": ["camiseta"],
    "falda": ["jardinera"],
    "sueter": ["chaqueta", "chaleco"],
}


def _terminos_producto(prod):
    """Términos de búsqueda para un producto detectado (aplica sinónimos)."""
    return _SINONIMOS.get(prod, [prod]) if prod else None


# Frases que indican que el cliente NO está seguro de la talla
_DUDA_TALLA = ["no se si", "no estoy segur", "no se que talla", "no se cual talla",
               "no se la talla", "no se mi talla", "cual talla", "que talla es",
               "6 o 8", "6 u 8", "8 o 10", "no se cual", "duda", "no estoy segura"]


# ─── DATOS DEL NEGOCIO (edita aquí) ────────────────────────────────
TIENDA_URL      = "https://ralozcolsas.com"
WHATSAPP_HUMANO = "+57 321 341 2903"   # ✏️ confirma el número real del asesor
EMAIL           = "ralozcol@outlook.com"
DIRECCION       = "Centro Comercial San Andresito de la 68 · Local M14, Bogotá"
HORARIO         = "Lunes y sábado de 10:00 a.m. a 6:00 p.m."
MAPS_URL        = "https://maps.app.goo.gl/NPvai43RV9VGNpqj8"   # ubicación del local

# Páginas legales de la tienda (deben coincidir con lo publicado en la web)
TERMINOS_URL   = TIENDA_URL + "/terminos.html"
PRIVACIDAD_URL = TIENDA_URL + "/politicas.html"
COOKIES_URL    = TIENDA_URL + "/cookies.html"

# Nota que aplica en varias respuestas (política del negocio)
NOTA_ATENCION = (
    "📲 Por favor *solo escribir* (las llamadas se nos dificultan).\n"
    "👦 Trae al niñ@ para tomar bien la talla.\n"
    "🚚 También hacemos *domicilios*: escríbenos para cotizar el envío."
)

VOLVER = "\n\n_Escribe *menú* para volver al inicio._"

# Se agrega al final de los precios para invitar a consultar otra talla sin repetir todo
OTRA_TALLA = ("\n\n🔁 ¿Ver *otra talla*? Escríbela (ej: *10*). "
              "También puedes cambiar de *niño/niña* u *otro colegio*, o escribir *menú*.")

# ─── ENTREGA (cuando el pedido está listo) ─────────────────────────
ENTREGA_PREGUNTA = (
    "\n\n📦 *¡Tu paquete ya está listo!* ¿Cómo deseas recibirlo?\n"
    "🚚 Escribe *envío* (a domicilio, con costo)\n"
    "🏪 o *recoger* (en el almacén)"
)
ENTREGA_RECOGER = (
    "🏪 *Recoger en el almacén*\n\n"
    "¡Te esperamos! Puedes recogerlo en:\n"
    f"📍 {DIRECCION}\n"
    f"🕘 {HORARIO}\n\n"
    "Lleva tu número de pedido. 🙌"
)
ENTREGA_PEDIR_DIR = (
    "🚚 *Envío a domicilio*\n\n"
    "Con gusto te lo llevamos. Escríbeme tu *dirección* y *barrio* "
    "para cotizarte el costo del envío del local a tu casa."
)

RESP_DUDA_TALLA = (
    "📏 *¿No estás seguro de la talla?*\n\n"
    "¡Tranquilo/a! Lo mejor es acercarte al punto y *traer al niñ@* para medir "
    "bien la talla, sin compromiso:\n"
    f"📍 {DIRECCION}\n"
    f"🕘 {HORARIO}\n\n"
    "📅 O *agenda una cita* y te atendemos rápido: escribe *cita*."
)


# ─── AGENDAR CITA ──────────────────────────────────────────────────
_CITA = ["cita", "agendar", "agenda", "reservar", "reserva", "separar hora", "turno",
         "vernos", "visitar", "pasar el", "puedo ir", "puedo pasar", "ir el",
         "medir", "tomar medida", "probar", "probarme", "entre semana", "cita previa"]

CITA_PEDIR_NOMBRE = (
    "📅 *Agendar cita*\n\n"
    "Los *lunes y sábados* atendemos sin cita (10 a.m.–6 p.m.). Para *otro día* "
    "te agendamos con gusto — ideal si quieres venir a *medir tallas*. 👕\n\n"
    "¿A nombre de quién? Escríbeme tu *nombre completo*."
)
CITA_PEDIR_DIA = (
    "📆 ¿Qué *día* te gustaría venir? (ej: *martes 8 de julio*)\n"
    "Atendemos con cita cualquier día *excepto domingos y festivos*."
)
CITA_PEDIR_HORA = (
    "🕘 ¿A qué *hora*? Entre las *10:00 a.m. y 6:00 p.m.*\n"
    "(ej: *11 am*, *2 pm*)"
)
CITA_PEDIR_COLEGIO = "🏫 Por último, ¿de qué *colegio* es el uniforme? (Marillac, Adventista o Manyanet)"


def _parse_hora(t: str):
    """Devuelve la hora (10-18) si es válida dentro del horario, o None."""
    m = re.search(r"(\d{1,2})", t)
    if not m:
        return None
    h = int(m.group(1))
    if "pm" in t and h < 12:
        h += 12
    if "am" in t and h == 12:
        h = 0
    return h if 10 <= h <= 18 else None


def _crear_cita(chat_id: str, nombre: str, dia: str, hora: str, colegio: str) -> bool:
    """Guarda la cita en el backend. Devuelve True si quedó registrada."""
    if not WA_LOG_TOKEN:
        logger.warning("WA_LOG_TOKEN no configurado: la cita no se guardará en el panel")
        return False
    status, _ = _post_backend(
        "/api/citas/nueva",
        {"chat_id": chat_id, "nombre": nombre, "dia": dia,
         "hora": hora, "colegio": colegio},
        timeout=10,
        headers={"X-Bot-Token": WA_LOG_TOKEN},
    )
    return status is not None and status < 300


def _consultar_estado_pedidos(telefono: str):
    """Pide al backend los pedidos de un teléfono. Devuelve el texto listo, o None
    si no hay pedidos con ese número."""
    tel = "".join(ch for ch in (telefono or "") if ch.isdigit())
    if len(tel) < 7:
        # Mismo contrato que "sin pedidos": (texto, hay_listo). Antes devolvía
        # None a secas y el caller crasheaba al desempacar (cliente sin respuesta).
        return None, False
    data = _get_backend_json(f"/api/tienda/pedidos-por-telefono/{tel}",
                             timeout=90, headers={"X-Bot-Token": WA_LOG_TOKEN})
    pedidos = (data or {}).get("pedidos", [])
    if not pedidos:
        return None, False
    lineas = ["📦 *Estado de tus pedidos*\n"]
    hay_listo = False
    for p in pedidos:
        if p.get("listo"):
            hay_listo = True
        total = f"${int(p['total']):,}".replace(",", ".") if p.get("total") else ""
        linea = f"• *{p['referencia']}* ({p.get('fecha', '')})\n  {p['estado_texto']}"
        if p.get("resumen"):
            linea += f"\n  🧺 {p['resumen']}"
        if total:
            linea += f"\n  💵 {total}"
        lineas.append(linea)
    return "\n".join(lineas), hay_listo


def _responder_estado(chat_id: str, texto: str, hay_listo: bool) -> Respuesta:
    """Arma la respuesta del estado; si hay un pedido listo, ofrece envío o recoger."""
    if hay_listo:
        set_estado(chat_id, "entrega_opcion")
        return Respuesta(texto + ENTREGA_PREGUNTA)
    return Respuesta(texto + VOLVER)


# ─── MENÚ PRINCIPAL ────────────────────────────────────────────────
MENU_PRINCIPAL = (
    "👋 ¡Hola! Bienvenido/a a *RALOZ COL S.A.S* 🎓\n"
    "🤖 Soy el *asistente virtual* (un bot). Respondo al instante; si necesitas una "
    "persona, escribe *asesor*.\n\n"
    "¿En qué te puedo ayudar? Responde con el *número* de la opción:\n\n"
    "1️⃣  Quiénes somos\n"
    "2️⃣  Métodos de pago\n"
    "3️⃣  Horarios y ubicación\n"
    "4️⃣  Precios y disponibilidad 🏷️\n"
    "5️⃣  Soporte (garantía, entregas, etc.)\n"
    "6️⃣  Pagar saldo pendiente 💰\n"
    "7️⃣  Hablar con un asesor 🙋\n"
    "8️⃣  Estado de mi pedido 📦\n\n"
    "_Escribe *menú* en cualquier momento para volver aquí._"
)

PEDIR_REF_SALDO = (
    "💰 *Pagar saldo pendiente*\n\n"
    "Escríbeme el *número de tu pedido* (lo recibiste al comprar, ej: *RALOZ-ABC123*) "
    "y te genero el link de pago."
)

RESP_QUIENES = (
    "🏫 *Quiénes somos*\n\n"
    "En *RALOZ COL S.A.S* nacimos del sueño de vestir a los estudiantes "
    "colombianos con uniformes que inspiren orgullo y confianza.\n\n"
    "✂️ Confección propia con control de calidad\n"
    "📏 Todas las tallas, con ajustes a medida\n"
    "🤝 Trabajamos con los colegios *Marillac*, *Adventista* y *Manyanet*\n"
    "⭐ Más de 5 años de experiencia"
)

RESP_PAGOS = (
    "💳 *Métodos de pago*\n\n"
    "Pagas 100% seguro en línea con *MercadoPago*:\n"
    "• Tarjetas de crédito y débito\n"
    "• PSE (transferencia bancaria)\n"
    "• Efecty y otros medios disponibles en el checkout\n\n"
    "Todos los precios ya *incluyen IVA*. 🧾\n"
    "Para prendas que se fabrican bajo pedido puedes pagar un *abono del 50%* "
    "y el resto al recibir. 🧵"
)

RESP_HORARIOS = (
    "🕘 *Horarios y ubicación*\n\n"
    f"📍 {DIRECCION}\n"
    f"🗺️ Cómo llegar: {MAPS_URL}\n"
    f"🕘 *Sin cita:* {HORARIO}\n"
    "📅 *Otros días:* solo con *cita previa* (excepto domingos y festivos).\n"
    f"📧 {EMAIL}\n\n"
    f"{NOTA_ATENCION}\n\n"
    "📅 ¿Quieres *agendar una cita*? Escribe *cita* y te reservamos un espacio.\n\n"
    "¡Te esperamos! 😊"
)

RESP_COMPRAR = (
    "🛒 *Comprar uniformes en línea*\n\n"
    "Es rápido y seguro:\n"
    "1. Entra 👉 " + TIENDA_URL + "\n"
    "2. Elige tu *colegio*, *prenda* y *talla*\n"
    "3. Paga con *MercadoPago* (link seguro)\n\n"
    "✅ Te *reservamos la talla*, te llega la *factura* al correo y "
    "te aviso por aquí el estado de tu pedido. 📦"
)

# ─── SOPORTE ───────────────────────────────────────────────────────
SOPORTE_MENU = (
    "🛠️ *Soporte RALOZ*\n\n"
    "¿Con qué te ayudo? Responde con el número:\n\n"
    "1️⃣  Garantía / arreglo de prenda\n"
    "2️⃣  Mi pedido no ha llegado\n"
    "3️⃣  Otro tema (hablar con un asesor)\n"
    "4️⃣  Cambios, devoluciones y retracto" + VOLVER
)

DEVOLUCIONES_INFO = (
    "🔄 *Cambios, devoluciones y retracto*\n\n"
    "La prenda debe estar *sin uso, limpia, seca, con etiquetas y en su empaque "
    "original*.\n\n"
    "• 📏 *Talla incorrecta:* cambio dentro de *5 días hábiles* de recibida.\n"
    "• 🧵 *Defecto de fabricación* (costuras/hilo): garantía de *6 meses* (cambio o arreglo).\n"
    "• ✍️ *Uniformes personalizados* (bordados o a la medida): no tienen cambio "
    "ni devolución, salvo defecto comprobado.\n"
    "• ↩️ *Derecho de retracto* (compras en línea, Ley 1480): puedes retractarte "
    "dentro de *5 días hábiles* de la entrega. El transporte de la devolución lo "
    "asume el cliente.\n"
    "• 🚫 *Cancelación:* dentro de las *24 horas* del pedido (si ya empezó la "
    "fabricación no se garantiza).\n"
    "• 💵 Los reembolsos van por el mismo medio de pago; el *costo de envío no es "
    "reembolsable*.\n"
    "• 💳 *Reversión del pago* (compras en línea, Ley 1480): si hay fraude, no "
    "recibes el producto o llega defectuoso, puedes pedir la reversión del pago "
    "dentro de *5 días hábiles*.\n\n"
    f"📄 Términos completos: {TERMINOS_URL}\n"
    "Para gestionar un caso escribe *asesor* con tu número de pedido y fotos. 🙌"
)

RESP_POLITICAS = (
    "📄 *Políticas y condiciones*\n\n"
    "Consúltalas completas aquí:\n"
    f"• Términos y condiciones (ventas): {TERMINOS_URL}\n"
    f"• Política de privacidad (datos): {PRIVACIDAD_URL}\n"
    f"• Política de cookies: {COOKIES_URL}\n\n"
    "Tratamos tus datos conforme a la *Ley 1581 de 2012*. Los pagos los procesa "
    "*MercadoPago*: no guardamos los datos de tu tarjeta."
)

GARANTIA_INFO = (
    "🧵 *Garantía / arreglo de prenda*\n\n"
    "Nuestra garantía cubre fallas de confección (costuras/hilo) por *6 meses*:\n"
    "• Costura en mala postura o descosida\n"
    "• Bordado dañado o despegado\n\n"
    "Para ayudarte, por favor:\n"
    "1️⃣ Cuéntame en pocas palabras qué le pasó a la prenda\n"
    "2️⃣ Envíame *fotos* del daño 📷\n\n"
    "⚠️ *Ten en cuenta:*\n"
    "• La prenda debe estar *limpia* (sucia no se arregla)\n"
    "• *No* se recibe mojada\n"
    "• El arreglo tarda *máximo de 1 a 2 semanas*\n"
    "• Si no se puede arreglar, hablamos contigo"
)

GARANTIA_RECORDAR_FOTO = (
    "📝 ¡Anotado! Ahora por favor *envíame las fotos* del daño 📷 para continuar.\n\n"
    "_Recuerda: la prenda se recibe *limpia y seca*._"
)

GARANTIA_POST_FOTO = (
    "¡Gracias! 🙏 Ya recibí tus fotos.\n\n"
    "Por favor acércate a nuestro *punto físico* para dejar la prenda:\n"
    f"📍 {DIRECCION}\n"
    f"🕘 {HORARIO}\n\n"
    "Recuerda llevarla *limpia y seca*. El arreglo tarda de *1 a 2 semanas*.\n"
    "Si la prenda no se puede arreglar, un asesor te contactará. 🙌"
)

RESP_PEDIDO = (
    "📦 *Seguimiento de pedido*\n\n"
    "Lamento la demora. Ten a la mano tu *número de pedido* o el nombre con el "
    "que compraste.\n\n"
    "En un momento un asesor te responde *por aquí mismo* con el estado exacto. 🙌"
)

RESP_ASESOR = (
    "🙋 *Te comunico con un asesor*\n\n"
    "¡Con gusto! En un momento una persona de nuestro equipo te responde "
    "*por aquí mismo*. 🙌\n"
    "Cuéntanos mientras tanto en qué te podemos ayudar."
)

RESP_LLAMAR = (
    "📞 *Llámanos o escríbenos por WhatsApp:*\n"
    f"{WHATSAPP_HUMANO}\n\n"
    f"🕘 {HORARIO}\n"
    "O escribe *asesor* y una persona te atiende por aquí mismo. 🙌"
)

RESP_AGRADECIMIENTO = "¡Con gusto! 😊 Si necesitas algo más, escribe *menú*."

# Confirmación de comprobante de pago (el archivo queda en la bandeja del asesor)
RESP_COMPROBANTE = (
    "🧾 *¡Gracias!* Recibimos tu *comprobante de pago*.\n\n"
    "Un asesor lo *verifica* y te confirma por aquí en cuanto quede validado. 🙌\n"
    "_Si aún no lo enviaste, adjunta la *foto* o el *PDF* del soporte._"
)

# Llegó una imagen/archivo sin contexto → preguntamos para qué es
RESP_FOTO_SIN_CONTEXTO = (
    "📎 ¡Recibí tu archivo! ¿Para qué es? Escribe:\n\n"
    "🧾 *pago* — si es un comprobante de pago (un asesor lo verifica).\n"
    "📦 *pedido* — si es sobre tu pedido/compra (estado, ¿ya está listo?).\n"
    "🧵 *garantía* — si es por una prenda con falla.\n\n"
    "O escribe *menú* para ver todas las opciones."
)

RESP_SOLO_TEXTO = (
    "🙂 Por ahora solo puedo leer *mensajes de texto* y *fotos*.\n\n"
    "Escribe *menú* para ver las opciones."
)

RESP_NO_ENTIENDO = "🤔 No estoy seguro de haber entendido.\n\n" + MENU_PRINCIPAL


# ─── Utilidades de texto ───────────────────────────────────────────
def _norm(s: str) -> str:
    """minúsculas + sin tildes, para comparar fácil."""
    s = (s or "").lower().strip()
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _tiene(t: str, palabras) -> bool:
    return any(p in t for p in palabras)


# Diccionarios de intención (palabras que el cliente podría escribir)
_SALUDOS   = {"menu", "menu principal", "hola", "inicio", "buenas", "buenos dias",
             "buenas tardes", "buenas noches", "ola", "hi", "start", "0"}
_GRACIAS   = {"gracias", "muchas gracias", "ok", "okay", "listo", "vale",
             "perfecto", "de acuerdo", "dale", "graciass"}
_ASESOR    = ["asesor", "humano", "persona", "agente", "hablar con", "alguien", "vendedor"]
# Piden un número / quieren llamar (frases específicas para no chocar con "número de pedido")
_LLAMAR    = ["numero para llamar", "numero donde llamar", "donde puedo llamar", "numero donde",
             "un numero donde", "me pasas el numero", "me das el numero", "me das un numero",
             "pasame el numero", "numero de contacto", "numero telefonico", "numero de telefono",
             "puedo llamar", "quiero llamar", "para llamar", "los llamo", "telefono de contacto",
             "linea de atencion", "numero de la tienda", "numero del local"]
# Horarios / ubicación (reusable dentro y fuera del flujo de precios)
_HORARIOS  = ["horario", "atendiendo", "atienden", "atiende", "atencion",
             "abierto", "abiertos", "estan abiert", "estan atend", "que dias", "que dia",
             "como llego", "como llegar", "mapa", "ubicado", "ubicacion",
             "direccion", "donde quedan", "donde estan", "donde queda", "abren",
             "cierran", "cierre", "hasta que hora", "hasta que horas",
             "que hora", "que horas", "a que hora", "a que horas", "de que hora",
             "cuando abren", "cuando atienden", "cuando se puede pasar",
             "cuando puedo pasar", "cuando puedo ir", "puedo pasar hoy",
             "atienden hoy", "atendiendo hoy", "estan atendiendo",
             "ir al local", "se puede ir", "puedo ir al local", "estan en el local",
             "estan hoy", "el local", "al local hoy"]
_GARANTIA  = ["garantia", "descosi", "descoc", "costura", "bordado", "daño", "dano",
             "roto", "rota", "rasg", "falla", "fallo", "mala postura", "deshil",
             "arreglo", "arreglar", "se daño", "defect"]
_PEDIDO    = ["no ha llegado", "no me ha llegado", "no llego", "no me llego",
             "donde esta mi pedido", "mi pedido", "mi orden", "demora", "envio",
             "despacho", "rastre", "seguimiento", "cuando llega"]
_COMPRAR   = ["comprar", "compra", "tienda", "uniforme", "precio", "precios",
             "cuanto vale", "cuanto cuesta", "cuanto es", "valor", "cotiz",
             "tienen", "tiene", "disponib", "disponen", "hay ", "consigo",
             "necesito", "busco", "quiero", "me venden", "venden"]
_DEVOLUCIONES = ["devolucion", "devoluciones", "devolver", "retracto", "reembolso",
             "me arrepenti", "quiero cancelar", "cancelar el pedido",
             "cancelar mi pedido", "cambio de talla", "cambiar de talla",
             "cambiar la talla", "me queda grande", "me queda pequeñ",
             "me quedo grande", "me quedo pequeñ"]
_POLITICAS = ["politica", "politicas", "privacidad", "terminos", "condiciones",
             "datos personales", "habeas data", "tratamiento de datos", "cookies"]
_COMPROBANTE = ["comprobante", "ya pague", "ya pagué", "ya realice el pago",
             "ya hice el pago", "hice el pago", "hice la transferencia", "ya transferi",
             "ya consigne", "le consigne", "soporte de pago", "soporte del pago",
             "adjunto el pago", "adjunto comprobante", "envio el comprobante",
             "aqui esta el pago", "aqui el comprobante", "pago realizado",
             "pantallazo del pago", "pantallazo de pago", "mando el pago", "ya deposite",
             # confirmaciones de transferencia ("ya se te hizo/iso la transferencia")
             "se te iso", "se te hizo la transfer", "se hizo la transfer", "hice la transfer",
             "te transferi", "te hice la transfer", "te consigne", "te deposite",
             "te mande el pago", "mande el pago", "te paso el soporte", "paso el soporte",
             "mando el soporte", "envio el soporte", "te envio el soporte"]
_ENVIOS    = ["domicilio", "envios", "hacen envio", "mandan", "a otra ciudad",
             "fuera de bogota", "contraentrega"]

# Palabras que forman un saludo. Si TODO el mensaje son estas palabras
# (ej: "hola buenos dias", "buenas tardes como estas"), lo tratamos como saludo.
_PALABRAS_SALUDO = {"hola", "holaa", "holaaa", "holi", "holis", "ola", "hey", "hi",
                    "hello", "buenas", "buenos", "buena", "bueno", "buen", "dia",
                    "dias", "tarde", "tardes", "noche", "noches", "como", "estas",
                    "esta", "va", "tal", "saludos", "cordial", "cordiales",
                    "senores", "señores", "y", "el", "bendiciones", "bendicion",
                    "feliz", "santo", "santos", "santas", "santa", "estan",
                    "excelente", "linda", "lindo", "bonito", "bonita"}


def _es_saludo(t: str) -> bool:
    """True si el mensaje es SOLO un saludo (sin otra intención)."""
    palabras = [w for w in re.split(r"[^0-9a-zñ]+", t) if w]
    if not palabras or len(palabras) > 6:
        return False
    return all(w in _PALABRAS_SALUDO for w in palabras)


def _guardar_colegio_y_pedir_siguiente(chat_id: str, idc: int, nombre: str, talla) -> Respuesta:
    """Guarda el colegio elegido y pide lo que falte: el género si ya hay
    talla, o la talla. (Mismo paso desde el menú y desde precio_colegio.)"""
    set_dato(chat_id, "precio_col_id", str(idc))
    set_dato(chat_id, "precio_col_nom", nombre)
    if talla:
        set_dato(chat_id, "precio_talla", talla)
        set_estado(chat_id, "precio_genero")
        return Respuesta(PEDIR_GENERO_PRECIO)
    set_estado(chat_id, "precio_talla")
    return Respuesta(PEDIR_TALLA_PRECIO)


def _mostrar_precios(chat_id: str, idc: int, nombre: str, talla: str, genero: str) -> Respuesta:
    """Muestra los precios y deja la conversación lista para consultar otra talla."""
    producto = get_dato(chat_id, "precio_producto", "") or None
    set_dato(chat_id, "precio_col_id", str(idc))
    set_dato(chat_id, "precio_col_nom", nombre)
    set_dato(chat_id, "precio_talla_val", talla)
    set_dato(chat_id, "precio_genero_val", genero)
    set_estado(chat_id, "precio_otra")
    return Respuesta(_consultar_precios(idc, nombre, talla, genero, producto) + OTRA_TALLA)


def _resp_comprobante(chat_id: str, via: str = "archivo") -> Respuesta:
    """Confirma la recepción de un comprobante de pago y pasa el chat a un asesor.
    El archivo en sí ya quedó guardado en la bandeja por la capa del webhook."""
    _guardar_lead(chat_id, f"Envió comprobante de pago ({via})")
    reset_estado(chat_id)
    aviso = ("🧾 *COMPROBANTE DE PAGO*\n"
             f"Cliente: {chat_id}\n"
             f"Envió un comprobante ({via}). Verifícalo en la bandeja y confírmale al cliente.")
    return Respuesta(RESP_COMPROBANTE, aviso, True)


def construir_respuesta(chat_id: str, texto: str, contenido: str = "texto") -> Respuesta:
    """
    Decide la respuesta según el mensaje y el estado de la conversación.
    contenido: "texto" | "foto" | "otro"  (tipo de mensaje recibido)
    """
    estado = get_estado(chat_id)
    t = _norm(texto)

    # ── 1) El cliente envió una FOTO o ARCHIVO ────────────────────
    if contenido in ("foto", "otro"):
        # Audio, sticker o video (media "otro" sin texto): no la podemos leer
        if contenido == "otro" and not t:
            return Respuesta(RESP_SOLO_TEXTO)
        # Dentro del flujo de garantía, la foto es la evidencia del daño
        if contenido == "foto" and estado == "garantia_fotos":
            desc = get_dato(chat_id, "garantia_desc", "(sin descripción)")
            reset_estado(chat_id)
            aviso = (
                "🧵 *NUEVA GARANTÍA*\n"
                f"Cliente: {chat_id}\n"
                f"Descripción: {desc}\n"
                "El cliente recibió fotos OK y se le indicó pasar al punto físico."
            )
            return Respuesta(GARANTIA_POST_FOTO, aviso)
        # El caption/nombre del archivo menciona un pago → comprobante directo
        if _tiene(t, _COMPROBANTE):
            return _resp_comprobante(chat_id, "imagen" if contenido == "foto" else "documento")
        # Archivo sin contexto → preguntamos si es pago o garantía
        set_estado(chat_id, "media_contexto")
        return Respuesta(RESP_FOTO_SIN_CONTEXTO)

    # ── 3) Comandos globales (funcionan en cualquier estado) ──────
    if t in _SALUDOS or _es_saludo(t):
        reset_estado(chat_id)
        return Respuesta(MENU_PRINCIPAL)
    # Agradecimiento: un "gracias" exacto siempre se contesta cortés (sin tocar
    # el estado). La versión "de pasada" ("me llegó roto, gracias") solo aplica
    # fuera de un flujo activo, para no interrumpir una garantía/cita/etc.
    # "gracias" cuenta como agradecimiento puro solo si el mensaje es CORTO y no
    # trae una intención de compra. Si es un pedido largo (ej. "necesito comprar
    # ... muchas gracias") NO debe tragarse la intención real: se deja pasar.
    if t in _GRACIAS or ("gracias" in t and estado == "menu"
                         and len(t.split()) <= 6 and not _tiene(t, _COMPRAR)):
        return Respuesta(RESP_AGRADECIMIENTO)
    # Piden un número para llamar → damos el teléfono (funciona en cualquier estado)
    if _tiene(t, _LLAMAR):
        return Respuesta(RESP_LLAMAR)
    if _tiene(t, _ASESOR):
        _guardar_lead(chat_id, texto)
        return Respuesta(RESP_ASESOR, handoff=True)

    # ── 4) Estás dentro del flujo de GARANTÍA (esperando fotos) ───
    if estado == "garantia_fotos":
        # El cliente escribió una descripción en vez de mandar foto:
        set_dato(chat_id, "garantia_desc", texto)
        return Respuesta(GARANTIA_RECORDAR_FOTO)

    # ── Contexto de un archivo recibido: ¿es pago o garantía? ─────
    if estado == "media_contexto":
        if t in ("1",) or _tiene(t, ["pago", "comprobante", "deposit", "transfer",
                                     "consign", "abono", "soporte"]):
            return _resp_comprobante(chat_id, "archivo")
        if _tiene(t, ["pedido", "orden", "compra", "listo", "entrega", "estado"]):
            # Sobre su pedido → intenta el estado con el mismo número del chat
            texto_resp, hay_listo = _consultar_estado_pedidos(chat_id)
            if texto_resp:
                return _responder_estado(chat_id, texto_resp, hay_listo)
            set_estado(chat_id, "estado_pedido_tel")
            return Respuesta("📦 *Estado de tu pedido*\n\nEscríbeme el *número de teléfono* "
                             "con el que hiciste el pedido (con o sin +57).")
        if t in ("2",) or _tiene(t, _GARANTIA):
            set_estado(chat_id, "garantia_fotos")
            return Respuesta(GARANTIA_INFO)
        # No aclaró → volvemos al menú principal
        reset_estado(chat_id)
        return Respuesta(RESP_NO_ENTIENDO)

    # ── Flujo PAGAR SALDO: esperando el número de pedido ──────────
    if estado == "saldo_ref":
        reset_estado(chat_id)
        return Respuesta(_solicitar_link_saldo(texto.strip().upper()))

    # ── Flujo PRECIOS: esperando el colegio ───────────────────────
    if estado == "precio_colegio":
        idc, nombre = _detectar_colegio(t)
        if not idc:
            return Respuesta("¿De cuál colegio? Escribe *Marillac*, *Adventista* o *Manyanet*.")
        return _guardar_colegio_y_pedir_siguiente(chat_id, idc, nombre, _detectar_talla(t))

    # ── Flujo PRECIOS: esperando la talla ─────────────────────────
    if estado == "precio_talla":
        # ¿El cliente no está seguro de la talla? → invitarlo al local / cita
        if _tiene(t, _DUDA_TALLA):
            reset_estado(chat_id)
            return Respuesta(RESP_DUDA_TALLA + VOLVER)
        talla_det = _detectar_talla(t)
        # Si no escribió una talla sino otra pregunta (horarios/cita), no la
        # tomamos como talla: la respondemos para no quedar pegados.
        if not talla_det:
            if _tiene(t, _HORARIOS):
                return Respuesta(RESP_HORARIOS + VOLVER)
            if _tiene(t, _CITA):
                set_estado(chat_id, "cita_nombre")
                return Respuesta(CITA_PEDIR_NOMBRE)
        talla = talla_det or texto.strip().upper()
        set_dato(chat_id, "precio_talla", talla)
        set_estado(chat_id, "precio_genero")
        return Respuesta(PEDIR_GENERO_PRECIO)

    # ── Flujo PRECIOS: esperando niño / niña / ambos ──────────────
    if estado == "precio_genero":
        genero = _detectar_genero(t)
        if not genero:
            if _tiene(t, _HORARIOS):
                return Respuesta(RESP_HORARIOS + VOLVER)
            if _tiene(t, _CITA):
                set_estado(chat_id, "cita_nombre")
                return Respuesta(CITA_PEDIR_NOMBRE)
            return Respuesta("¿Para *niño*, *niña* o *ambos*?")
        idc = int(get_dato(chat_id, "precio_col_id", "0"))
        nombre = get_dato(chat_id, "precio_col_nom", "")
        talla = get_dato(chat_id, "precio_talla", "")
        return _mostrar_precios(chat_id, idc, nombre, talla, genero)

    # ── Flujo PRECIOS: ya mostró precios, permite ver otra talla ──
    if estado == "precio_otra":
        idc2, nombre2 = _detectar_colegio(t)
        if idc2:  # cambió de colegio → pedir talla de nuevo
            set_dato(chat_id, "precio_col_id", str(idc2))
            set_dato(chat_id, "precio_col_nom", nombre2)
            set_estado(chat_id, "precio_talla")
            return Respuesta(PEDIR_TALLA_PRECIO)
        if _tiene(t, _DUDA_TALLA):
            reset_estado(chat_id)
            return Respuesta(RESP_DUDA_TALLA + VOLVER)
        genero_nuevo = _detectar_genero(t)
        if genero_nuevo:
            set_dato(chat_id, "precio_genero_val", genero_nuevo)
        prod_nuevo = _detectar_producto(t)
        if prod_nuevo:
            set_dato(chat_id, "precio_producto", prod_nuevo)
        idc = int(get_dato(chat_id, "precio_col_id", "0"))
        nombre = get_dato(chat_id, "precio_col_nom", "")
        gen = get_dato(chat_id, "precio_genero_val", "ambos")
        talla = _detectar_talla(t)
        if talla:
            return _mostrar_precios(chat_id, idc, nombre, talla, gen)
        if genero_nuevo or prod_nuevo:  # cambió género/prenda → re-mostrar última talla
            talla_prev = get_dato(chat_id, "precio_talla_val", "")
            if talla_prev:
                return _mostrar_precios(chat_id, idc, nombre, talla_prev, gen)
        # No es talla ni cambio de prenda: ¿pregunta por horarios o quiere cita?
        if _tiene(t, _HORARIOS):
            return Respuesta(RESP_HORARIOS + VOLVER)
        if _tiene(t, _CITA):
            set_estado(chat_id, "cita_nombre")
            return Respuesta(CITA_PEDIR_NOMBRE)
        return Respuesta("🔁 Escríbeme la *talla* que quieres ver (ej: *10*, *S*, *M*), "
                         "o *menú* para volver al inicio.")

    # ── Flujo AGENDAR CITA ────────────────────────────────────────
    if estado == "cita_nombre":
        set_dato(chat_id, "cita_nombre", texto.strip())
        set_estado(chat_id, "cita_dia")
        return Respuesta(CITA_PEDIR_DIA)

    if estado == "cita_dia":
        if "domingo" in t:
            return Respuesta("😕 Los domingos no atendemos. Dime otro día (lunes a sábado).")
        # Si escribió una frase suelta o una pregunta en vez de un día, re-preguntamos
        # (así no queda "hasta qué hora podría confirmarle..." guardado como el día).
        if not _parece_dia(t):
            return Respuesta("📆 Escríbeme *solo el día*, por ejemplo: *mañana*, *el jueves* "
                             "o *18 de julio*. 🙂")
        set_dato(chat_id, "cita_dia", texto.strip()[:60])
        set_estado(chat_id, "cita_hora")
        return Respuesta(CITA_PEDIR_HORA)

    if estado == "cita_hora":
        if _parse_hora(t) is None:
            return Respuesta("🕘 Dame una hora entre las *10 a.m. y 6 p.m.* (ej: *11 am*, *2 pm*).")
        set_dato(chat_id, "cita_hora", texto.strip())
        set_estado(chat_id, "cita_colegio")
        return Respuesta(CITA_PEDIR_COLEGIO)

    if estado == "cita_colegio":
        _idc, nombre_col = _detectar_colegio(t)
        colegio = nombre_col or texto.strip()
        nombre = get_dato(chat_id, "cita_nombre", "")
        dia = get_dato(chat_id, "cita_dia", "")
        hora = get_dato(chat_id, "cita_hora", "")
        guardada = _crear_cita(chat_id, nombre, dia, hora, colegio)
        reset_estado(chat_id)
        resumen = (
            "✅ *¡Cita solicitada!*\n\n"
            f"👤 {nombre}\n📆 {dia}\n🕘 {hora}\n🏫 {colegio}\n\n"
            "En un momento un asesor te *confirma el cupo* por aquí mismo. 🙌"
        )
        aviso = ("📅 *NUEVA CITA — confirmar cupo*\n"
                 f"Cliente: {chat_id}\n👤 {nombre}\n📆 {dia}\n🕘 {hora}\n🏫 {colegio}")
        if not guardada:
            # El cliente ve lo mismo; el asesor sabe que el panel quedó ciego.
            aviso += ("\n\n⚠️ OJO: esta cita NO quedó guardada en el panel "
                      "(el backend no respondió). Anótala a mano.")
        # handoff: el asesor confirma la fecha (la disponibilidad real varía).
        # La regla 'volver_a_bot' devuelve el chat al bot pasadas unas horas.
        return Respuesta(resumen, aviso, handoff=True)

    # ── Flujo ESTADO DE PEDIDO: esperando el teléfono ─────────────
    if estado == "estado_pedido_tel":
        texto_resp, hay_listo = _consultar_estado_pedidos(texto)
        if texto_resp:
            return _responder_estado(chat_id, texto_resp, hay_listo)
        reset_estado(chat_id)
        return Respuesta(
            "🤔 No encontré pedidos en línea con ese número.\n"
            "Si compraste en el *punto físico* o con otro número, escribe *asesor* y te ayudamos. 🙌"
        )

    # ── Flujo ENTREGA: pedido listo, elige envío o recoger ────────
    if estado == "entrega_opcion":
        if _tiene(t, ["envio", "domicilio", "casa", "a mi casa", "envienlo", "manden", "que lo manden"]):
            set_estado(chat_id, "entrega_direccion")
            return Respuesta(ENTREGA_PEDIR_DIR)
        if _tiene(t, ["recoger", "almacen", "local", "tienda", "paso yo", "recojo", "punto"]):
            reset_estado(chat_id)
            return Respuesta(ENTREGA_RECOGER + VOLVER)
        return Respuesta("¿Prefieres *envío* a domicilio o *recoger* en el almacén?")

    if estado == "entrega_direccion":
        direccion = texto.strip()
        _guardar_lead(chat_id, f"Solicitó envío a: {direccion}")
        reset_estado(chat_id)
        aviso = ("🚚 *SOLICITUD DE ENVÍO*\n"
                 f"Cliente: {chat_id}\nDirección: {direccion}")
        return Respuesta(
            "¡Gracias! 🙌 Un asesor te confirma el *costo del envío* y coordinamos la entrega. "
            "En un momento te escribimos por aquí.",
            aviso, True)

    # ── 5) Estás dentro del submenú de SOPORTE ────────────────────
    if estado == "soporte":
        if t in ("1",) or _tiene(t, _GARANTIA):
            set_estado(chat_id, "garantia_fotos")
            return Respuesta(GARANTIA_INFO)
        if t in ("2",) or _tiene(t, _PEDIDO):
            _guardar_lead(chat_id, texto)
            reset_estado(chat_id)
            return Respuesta(RESP_PEDIDO, handoff=True)
        if t in ("4",) or _tiene(t, _DEVOLUCIONES):
            reset_estado(chat_id)
            return Respuesta(DEVOLUCIONES_INFO + VOLVER)
        if t in ("3",):
            reset_estado(chat_id)
            return Respuesta(RESP_ASESOR, handoff=True)
        # algo no claro dentro de soporte → repetir submenú
        return Respuesta("No entendí. " + SOPORTE_MENU)

    # ── 6) Menú principal / detección por palabras clave ──────────
    # Comprobante de pago escrito ("ya pagué", "envío soporte", etc.)
    if _tiene(t, _COMPROBANTE):
        return _resp_comprobante(chat_id, "mensaje")
    # Pagar saldo (va primero para que no choque con "métodos de pago")
    if t == "6" or _tiene(t, ["pagar saldo", "saldo pendiente", "pagar el saldo",
                              "pagar mi saldo", "abono restante", "saldo"]):
        set_estado(chat_id, "saldo_ref")
        return Respuesta(PEDIR_REF_SALDO)
    if t == "1" or _tiene(t, ["quien", "quienes somos", "nosotros", "empresa"]):
        return Respuesta(RESP_QUIENES + VOLVER)
    if t == "2" or _tiene(t, ["pago", "pagos", "tarjeta", "pse", "efecty", "abono"]):
        return Respuesta(RESP_PAGOS + VOLVER)
    if t == "3" or _tiene(t, _HORARIOS):
        return Respuesta(RESP_HORARIOS + VOLVER)
    # Agendar cita (después de horarios, que es de donde se ofrece)
    if _tiene(t, _CITA):
        set_estado(chat_id, "cita_nombre")
        return Respuesta(CITA_PEDIR_NOMBRE)
    if t == "5" or _tiene(t, ["soporte", "ayuda", "reclamo", "queja", "problema"]):
        set_estado(chat_id, "soporte")
        return Respuesta(SOPORTE_MENU)
    if t == "7":
        _guardar_lead(chat_id, texto)
        reset_estado(chat_id)
        return Respuesta(RESP_ASESOR, handoff=True)
    if t == "8" or _tiene(t, ["estado de mi pedido", "estado del pedido", "estado pedido",
                              "rastrear", "seguir mi pedido", "donde va mi pedido"]):
        # Primero pruebo con el mismo número de WhatsApp del cliente
        texto_resp, hay_listo = _consultar_estado_pedidos(chat_id)
        if texto_resp:
            return _responder_estado(chat_id, texto_resp, hay_listo)
        set_estado(chat_id, "estado_pedido_tel")
        return Respuesta("📦 *Estado de tu pedido*\n\nEscríbeme el *número de teléfono* "
                         "con el que hiciste el pedido (con o sin +57).")

    # Políticas / privacidad / términos → enlaces a las páginas legales
    if _tiene(t, _POLITICAS):
        return Respuesta(RESP_POLITICAS + VOLVER)

    # Cambios, devoluciones, retracto, cancelación (antes que garantía/compra)
    if _tiene(t, _DEVOLUCIONES):
        return Respuesta(DEVOLUCIONES_INFO + VOLVER)

    # Garantía escrita directamente desde el menú (sin pasar por soporte)
    if _tiene(t, _GARANTIA):
        set_estado(chat_id, "garantia_fotos")
        return Respuesta(GARANTIA_INFO)

    # Envíos / domicilios (pregunta de venta) — ANTES que "pedido no llegado",
    # porque ambos mencionan la palabra "envío".
    if _tiene(t, _ENVIOS):
        return Respuesta(RESP_COMPRAR + VOLVER)

    # Pedido no llegado escrito directamente
    if _tiene(t, _PEDIDO):
        _guardar_lead(chat_id, texto)
        return Respuesta(RESP_PEDIDO, handoff=True)

    # Precios / comprar → flujo interactivo (colegio → talla → género → stock)
    prod_detectado = _detectar_producto(t)
    if t == "4" or _tiene(t, _COMPRAR) or prod_detectado:
        if _tiene(t, _DUDA_TALLA):
            return Respuesta(RESP_DUDA_TALLA + VOLVER)
        if prod_detectado:
            set_dato(chat_id, "precio_producto", prod_detectado)
        idc, nombre = _detectar_colegio(t)
        if idc:
            return _guardar_colegio_y_pedir_siguiente(chat_id, idc, nombre, _detectar_talla(t))
        set_estado(chat_id, "precio_colegio")
        return Respuesta(PEDIR_COLEGIO_PRECIO)

    # Duda de talla escrita libremente (ej: "no sé si es 6 u 8")
    if _tiene(t, _DUDA_TALLA):
        return Respuesta(RESP_DUDA_TALLA + VOLVER)

    # ── 7) No reconocido → menú ───────────────────────────────────
    return Respuesta(RESP_NO_ENTIENDO)
