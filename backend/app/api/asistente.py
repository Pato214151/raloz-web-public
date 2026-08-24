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
import json
import logging
from datetime import date

import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func, and_

from app import db, limiter
from app.utils.decorators import rol_requerido
from app.models import (
    Factura, Pago, Gasto, PedidoFabricacion, PrendaPendiente, CajaDiaria,
    Stock, Producto, Colegio,
)

logger = logging.getLogger("raloz.asistente")

asistente_bp = Blueprint('asistente', __name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
# Modelo de la capa gratis; se puede cambiar por env si Google lo renombra.
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash').strip()

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
    """Reúne un resumen de datos REALES (solo lectura) para dárselo al asistente."""
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

    return ctx


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

    datos = _contexto_datos()

    sistema = (
        "Eres el asistente interno del sistema POS de RALOZ (uniformes escolares en "
        "Bogotá). Hablas en español, claro y breve. Usa SOLO los datos reales y el "
        "manual que te doy abajo. Si algo no está en los datos, dilo con honestidad y "
        "sugiere en qué parte del sistema mirarlo. NUNCA inventes cifras, precios ni "
        "stock. El dinero va en pesos colombianos (ej: $1.234.000)."
    )
    prompt = (
        f"{sistema}\n\n=== DATOS REALES DEL SISTEMA (hoy {datos.get('fecha_hoy')}) ===\n"
        f"{json.dumps(datos, ensure_ascii=False, default=str)}\n\n"
        f"=== MANUAL DEL SISTEMA ===\n{MANUAL}\n\n"
        f"=== PREGUNTA DEL USUARIO ===\n{pregunta}"
    )

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}")
    try:
        r = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700},
        }, timeout=30)
    except Exception as e:
        logger.warning("asistente: fallo conectando a Gemini: %s", e)
        return jsonify({'error': 'No pude conectar con el asistente ahora. Intenta de nuevo.'}), 502

    if r.status_code != 200:
        logger.warning("asistente: Gemini respondió %s: %s", r.status_code, r.text[:300])
        return jsonify({'error': 'El asistente no respondió. Revisa la GEMINI_API_KEY o el modelo.',
                        'code': 'gemini_error'}), 502

    try:
        texto = r.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception:
        texto = 'No obtuve una respuesta. Intenta reformular la pregunta.'

    return jsonify({'respuesta': texto}), 200
