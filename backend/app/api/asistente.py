"""
API del Asistente RALOZ (Fase 1 — SOLO LECTURA).

Un asistente interno para el POS/panel: responde preguntas del equipo
(admin/vendedor/cajero) usando *datos reales* del sistema y un pequeño
manual de uso. NO ejecuta acciones (no crea ni modifica nada).

- Usa Google Gemini (capa gratis). La llave va en la variable de entorno
  GEMINI_API_KEY (nunca en el código). Si no está, el endpoint responde 503.
- Regla de oro del prompt: responder SOLO con los datos entregados; nunca
  inventar cifras, precios ni stock.
"""

import os
import re
import json
import time
import logging
from datetime import date

# Caché corta del contexto (evita reconsultar la BD en cada pregunta seguida).
_CTX_CACHE = {'t': 0.0, 'data': None}
_CTX_TTL = 45  # segundos

import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func, and_

from app import db, limiter
from app.utils.decorators import rol_requerido, get_current_identity, registrar_auditoria
from app.models import (
    Factura, Pago, Gasto, PedidoFabricacion, PrendaPendiente, CajaDiaria,
    Stock, Producto, Colegio, PedidoWeb,
)

logger = logging.getLogger("raloz.asistente")

asistente_bp = Blueprint('asistente', __name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
# Modelo de la capa gratis; se puede cambiar por env si Google lo renombra.
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash').strip()
# Modelos que Google ya retiró (dan 404); si la env trae uno de estos, lo ignoramos.
_MODELOS_RETIRADOS = {'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro',
                      'gemini-1.0-pro', 'gemini-pro', 'gemini-2.0-flash-001'}

# ── Fase 2 (acciones) — APAGADO por defecto. Enciéndelo con ASISTENTE_ACCIONES=1.
#    Aun encendido, NADA se ejecuta sin confirmación explícita del admin en la UI.
ACCIONES_ON = os.getenv('ASISTENTE_ACCIONES', '') == '1'
# Estados de entrega que el asistente puede PROPONER (2a). Con confirmación.
_ESTADOS_ENTREGA = {
    'EMPACADO':     'Empacado (listo para entregar)',
    'LISTO_LLAMAR': 'Listo — llamar al cliente',
    'ENTREGADA':    'Entregado al cliente',
}

# Manual corto del sistema (para responder "¿cómo hago X?"). Basado en la
# operación real de RALOZ. Ajusta este texto cuando cambie un flujo.
MANUAL = (
    "CÓMO USAR EL SISTEMA RALOZ:\n"
    "- Nueva venta: menú 'Nueva Venta' (/vender), eliges colegio, prenda y talla, "
    "agregas al carrito y cobras. Se puede pagar total o con abono.\n"
    "- Ticket: tras la venta, 'Imprimir recibo' saca el ticket de 76mm en la "
    "impresora de taquilla (Epson TM-U220PD, por cable al computador, no al celular). "
    "También se reimprime desde 'Buscar facturas' → 'Imprimir ticket'.\n"
    "- Abono 50%: en pedidos por fabricación el cliente paga la mitad y el saldo al entregar.\n"
    "- Garantía: 6 meses por defecto de confección (costuras/hilo); cambio por talla "
    "incorrecta dentro de 5 días hábiles.\n"
    "- Pedidos web: flujo POR_ENTREGAR → EMPACADO → ENTREGADO; fabricación: "
    "EN_PRODUCCION → LISTO → ENTREGADO.\n"
    "- Horario del punto: lunes y sábado 10:00 a.m. – 5:00 p.m."
)


def _contexto_datos():
    """Reúne un resumen de datos REALES (solo lectura) para dárselo al asistente.
    Cachea el resultado unos segundos para no golpear la BD en cada pregunta."""
    ahora = time.time()
    if _CTX_CACHE['data'] is not None and (ahora - _CTX_CACHE['t']) < _CTX_TTL:
        return _CTX_CACHE['data']
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)
    ctx = {'fecha_hoy': hoy.isoformat()}

    try:
        vh = db.session.query(
            func.count(Factura.id_factura), func.coalesce(func.sum(Factura.total), 0)
        ).filter(and_(Factura.fecha_factura == hoy, Factura.estado != 'ANULADA')).first()
        ctx['ventas_hoy'] = {'facturas': int(vh[0] or 0), 'total': float(vh[1] or 0)}

        vm = db.session.query(
            func.count(Factura.id_factura), func.coalesce(func.sum(Factura.total), 0)
        ).filter(and_(Factura.fecha_factura >= inicio_mes, Factura.fecha_factura <= hoy,
                      Factura.estado != 'ANULADA')).first()
        ctx['ventas_mes'] = {'facturas': int(vm[0] or 0), 'total': float(vm[1] or 0)}

        ch = db.session.query(func.coalesce(func.sum(Pago.valor), 0)).join(
            Factura, Pago.id_factura == Factura.id_factura
        ).filter(and_(Pago.fecha_pago == hoy, Factura.estado != 'ANULADA')).first()
        ctx['cobros_hoy'] = float(ch[0] or 0)

        gm = db.session.query(func.coalesce(func.sum(Gasto.valor), 0)).filter(and_(
            Gasto.fecha >= inicio_mes, Gasto.fecha <= hoy,
            func.coalesce(Gasto.estado_pago, 'PAGADO') != 'PENDIENTE')).first()
        ctx['gastos_mes'] = float(gm[0] or 0)

        ctx['total_por_cobrar'] = float(db.session.query(
            func.coalesce(func.sum(Factura.saldo_pendiente), 0)
        ).filter(Factura.estado.in_(['PENDIENTE', 'ABONO'])).scalar() or 0)

        ctx['pedidos_web_por_entregar'] = Factura.query.filter(
            Factura.canal == 'WEB',
            Factura.estado_entrega.in_(['POR_ENTREGAR', 'EMPACADO']),
            Factura.estado != 'ANULADA').count()
        ctx['fabricacion_en_curso'] = PedidoFabricacion.query.filter(
            PedidoFabricacion.estado.in_(['en_produccion', 'listo_para_entrega'])).count()
        ctx['prendas_pendientes_entrega'] = PrendaPendiente.query.filter_by(estado='PENDIENTE').count()

        caja = CajaDiaria.query.filter_by(estado='ABIERTA').first()
        ctx['caja'] = {'abierta': bool(caja),
                       'total_ventas': float(caja.total_ventas or 0) if caja else 0}
    except Exception as e:
        logger.warning("asistente: fallo armando métricas: %s", e)

    # Stock bajo (<=3 unidades): top 20, con nombre de prenda, colegio y talla
    try:
        filas = (db.session.query(
                    Colegio.nombre, Producto.nombre, Stock.talla_individual, Stock.cantidad)
                 .join(Producto, Stock.id_producto == Producto.id_producto)
                 .join(Colegio, Stock.id_colegio == Colegio.id_colegio)
                 .filter(Stock.cantidad <= 3)
                 .order_by(Stock.cantidad.asc())
                 .limit(20).all())
        ctx['stock_bajo'] = [
            {'colegio': c, 'prenda': p, 'talla': t, 'cantidad': int(q or 0)}
            for (c, p, t, q) in filas
        ]
    except Exception as e:
        logger.warning("asistente: fallo armando stock bajo: %s", e)

    _CTX_CACHE['t'] = ahora
    _CTX_CACHE['data'] = ctx
    return ctx


def _extraer_accion(texto):
    """Busca 'ACCION_JSON: {...}' en la respuesta de la IA. Devuelve
    (texto_sin_esa_linea, accion_validada | None). Solo valida acciones de la
    lista blanca; cualquier otra cosa se ignora."""
    m = re.search(r'ACCION_JSON:\s*(\{.*)', texto, re.DOTALL)
    if not m:
        return texto, None
    crudo = m.group(1)
    obj = None
    for fin in range(len(crudo), 0, -1):  # recorta hasta un JSON válido
        if crudo[fin - 1] != '}':
            continue
        try:
            obj = json.loads(crudo[:fin])
            break
        except Exception:
            continue
    if not isinstance(obj, dict) or obj.get('tipo') != 'cambiar_estado_pedido':
        return texto, None
    estado = str(obj.get('estado', '')).upper().strip()
    factura = str(obj.get('factura', '')).strip()
    if estado not in _ESTADOS_ENTREGA or not factura:
        return texto, None
    accion = {
        'tipo': 'cambiar_estado_pedido',
        'factura': factura,
        'estado': estado,
        'descripcion': f'Marcar la factura/pedido “{factura}” como: {_ESTADOS_ENTREGA[estado]}',
    }
    texto_limpio = texto[:m.start()].rstrip() or 'Te propongo esta acción:'
    return texto_limpio, accion


def _buscar_factura(ref):
    """Busca una factura por su número, o por la referencia de un pedido web."""
    f = Factura.query.filter_by(numero_factura=ref).first()
    if f:
        return f
    pedido = PedidoWeb.query.filter_by(referencia=ref).first()
    if pedido and pedido.id_factura:
        return Factura.query.get(pedido.id_factura)
    return None


@asistente_bp.route('/preguntar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor', 'cajero')
@limiter.limit("20 per minute")
def preguntar():
    """Recibe {pregunta} y responde con datos reales vía Gemini (solo lectura)."""
    if not GEMINI_API_KEY:
        return jsonify({
            'error': 'El asistente aún no está configurado. Falta la variable '
                     'GEMINI_API_KEY en el servidor.',
            'code': 'sin_config',
        }), 503

    pregunta = ((request.get_json(silent=True) or {}).get('pregunta') or '').strip()
    if not pregunta:
        return jsonify({'error': 'Escribe una pregunta.'}), 400
    if len(pregunta) > 800:
        pregunta = pregunta[:800]

    identity = get_current_identity()
    puede_accionar = ACCIONES_ON and identity.get('rol') == 'administrador'

    datos = _contexto_datos()

    sistema = (
        "Eres el asistente interno del sistema POS de RALOZ (uniformes escolares en "
        "Bogotá). Hablas en español, claro y breve. Usa SOLO los datos reales y el "
        "manual que te doy abajo. Si algo no está en los datos, dilo con honestidad y "
        "sugiere en qué parte del sistema mirarlo. NUNCA inventes cifras, precios ni "
        "stock. El dinero va en pesos colombianos (ej: $1.234.000)."
    )
    acciones = ""
    if puede_accionar:
        acciones = (
            "\n\n=== ACCIONES (con confirmación) ===\n"
            "Si el usuario pide CAMBIAR EL ESTADO DE ENTREGA de un pedido o factura, "
            "NO afirmes que ya lo hiciste. Escribe una frase proponiéndolo y, en la "
            "ÚLTIMA línea, agrega EXACTAMENTE:\n"
            "ACCION_JSON: {\"tipo\":\"cambiar_estado_pedido\",\"factura\":\"<numero de factura o referencia RALOZ-...>\",\"estado\":\"<EMPACADO|LISTO_LLAMAR|ENTREGADA>\"}\n"
            "Mapea: 'empacado'->EMPACADO; 'listo'/'llamar'->LISTO_LLAMAR; "
            "'entregado'/'entregué'/'ya lo recogió'->ENTREGADA. "
            "Si el usuario NO pide una acción, responde normal y NO agregues ACCION_JSON."
        )
    prompt = (
        f"{sistema}{acciones}\n\n=== DATOS REALES DEL SISTEMA (hoy {datos.get('fecha_hoy')}) ===\n"
        f"{json.dumps(datos, ensure_ascii=False, default=str)}\n\n"
        f"=== MANUAL DEL SISTEMA ===\n{MANUAL}\n\n"
        f"=== PREGUNTA DEL USUARIO ===\n{pregunta}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500},
    }

    # Prueba varios modelos (el de la env primero, luego respaldos conocidos),
    # así un nombre de modelo mal escrito no rompe el asistente.
    candidatos = []
    if GEMINI_MODEL and GEMINI_MODEL not in _MODELOS_RETIRADOS:
        candidatos.append(GEMINI_MODEL)
    for m in ('gemini-3.6-flash', 'gemini-flash-latest', 'gemini-2.5-flash'):
        if m not in candidatos:
            candidatos.append(m)
    candidatos = candidatos[:3]  # acota el peor caso de latencia

    ultimo_detalle = ''
    for modelo in candidatos:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{modelo}:generateContent?key={GEMINI_API_KEY}")
        try:
            r = requests.post(url, json=payload, timeout=15)
        except Exception as e:
            ultimo_detalle = f'conexión: {e}'
            logger.warning("asistente: fallo conectando a Gemini (%s): %s", modelo, e)
            continue

        if r.status_code == 200:
            try:
                texto = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            except Exception:
                texto = 'No obtuve una respuesta. Intenta reformular la pregunta.'
            respuesta = {'respuesta': texto}
            if puede_accionar:
                texto_limpio, accion = _extraer_accion(texto)
                if accion:
                    respuesta['respuesta'] = texto_limpio
                    respuesta['accion'] = accion
            return jsonify(respuesta), 200

        ultimo_detalle = f'{r.status_code}: {r.text[:200]}'
        logger.warning("asistente: Gemini %s respondió %s: %s", modelo, r.status_code, r.text[:300])
        # Si el problema es la LLAVE, no tiene sentido probar otros modelos.
        if r.status_code in (400, 403) and 'API_KEY' in r.text.upper():
            break

    return jsonify({
        'error': 'El asistente no respondió. Revisa la GEMINI_API_KEY o el modelo.',
        'detalle': ultimo_detalle,
        'code': 'gemini_error',
    }), 502


@asistente_bp.route('/ejecutar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
@limiter.limit("20 per minute")
def ejecutar():
    """Ejecuta una acción YA confirmada por el admin en la UI. Apagada por
    defecto (requiere ASISTENTE_ACCIONES=1). Reusa el mismo flujo probado."""
    if not ACCIONES_ON:
        return jsonify({
            'error': 'Las acciones del asistente están desactivadas. '
                     'Actívalas con ASISTENTE_ACCIONES=1 en el servidor.',
            'code': 'acciones_off',
        }), 403

    data = request.get_json(silent=True) or {}
    if data.get('tipo') != 'cambiar_estado_pedido':
        return jsonify({'error': 'Acción no soportada.'}), 400

    factura_ref = str(data.get('factura', '')).strip()
    estado = str(data.get('estado', '')).upper().strip()
    if estado not in _ESTADOS_ENTREGA or not factura_ref:
        return jsonify({'error': 'Datos de la acción inválidos.'}), 400

    factura = _buscar_factura(factura_ref)
    if not factura:
        return jsonify({'error': f'No encontré la factura/pedido "{factura_ref}".',
                        'code': 'no_encontrado'}), 404
    if factura.estado == 'ANULADA':
        return jsonify({'error': 'Esa factura está anulada; no se puede cambiar.'}), 400

    anterior = factura.estado_entrega
    factura.estado_entrega = estado
    db.session.commit()

    identity = get_current_identity()
    try:
        registrar_auditoria('facturas', factura.id_factura, estado,
                            f'[Asistente] Estado de entrega {anterior} -> {estado} '
                            f'por {identity.get("usuario")}')
    except Exception as e:
        logger.warning("asistente: no se pudo auditar: %s", e)

    return jsonify({
        'ok': True,
        'mensaje': f'✅ Factura {factura.numero_factura} marcada como '
                   f'"{_ESTADOS_ENTREGA[estado]}".',
    }), 200
