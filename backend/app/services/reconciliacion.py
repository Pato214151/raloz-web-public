"""
Reconciliación de pagos con MercadoPago.

Red de seguridad: si un webhook de pago se pierde (servidor dormido, timeout,
etc.), este chequeo consulta a MercadoPago los pagos aprobados recientes y
registra los pedidos que quedaron sin facturar. Así ninguna venta se pierde.
"""

import os
from datetime import datetime, timedelta

import requests

from app import db
from app.models import PedidoWeb
from app.services.facturacion_web import (
    _crear_factura_desde_pedido,
    _crear_pedido_fabricacion_si_aplica,
)

MP_API = 'https://api.mercadopago.com'


def reconciliar_pagos(dias: int = 2, logger=None) -> int:
    """Busca pagos aprobados en MercadoPago de los últimos `dias` y factura los
    pedidos que el webhook no alcanzó a procesar. Devuelve cuántos se recuperaron."""
    token = os.getenv('MP_ACCESS_TOKEN', '')
    if not token:
        return 0

    fmt = '%Y-%m-%dT%H:%M:%S.000-00:00'
    params = {
        'sort': 'date_created', 'criteria': 'desc',
        'range': 'date_created',
        'begin_date': (datetime.utcnow() - timedelta(days=dias)).strftime(fmt),
        'end_date': datetime.utcnow().strftime(fmt),
        'status': 'approved', 'limit': 50,
    }
    try:
        r = requests.get(
            f'{MP_API}/v1/payments/search',
            headers={'Authorization': f'Bearer {token}'},
            params=params, timeout=15,
        )
        if r.status_code >= 300:
            if logger:
                logger.warning('[RECON] MP status %s: %s', r.status_code, r.text[:200])
            return 0
        resultados = (r.json() or {}).get('results', [])
    except Exception as e:
        if logger:
            logger.warning('[RECON] error consultando MP: %s', e)
        return 0

    recuperados = 0
    for pago in resultados:
        ref = pago.get('external_reference') or ''
        if not ref.startswith('RALOZ-') or ref.endswith('-SALDO'):
            continue
        pedido = PedidoWeb.query.filter_by(referencia=ref).first()
        if not pedido or pedido.id_factura:
            continue  # no existe, o ya está facturado (nada que recuperar)
        try:
            pedido.estado = 'pagado'
            pedido.fecha_pago = pedido.fecha_pago or datetime.utcnow()
            pedido.metodo_pago = pago.get('payment_type_id', 'MP')
            db.session.commit()

            factura = _crear_factura_desde_pedido(pedido)
            pedido.id_factura = factura.id_factura
            db.session.commit()

            try:
                _crear_pedido_fabricacion_si_aplica(pedido)
                db.session.commit()
            except Exception:
                db.session.rollback()

            recuperados += 1
            if logger:
                logger.warning('[RECON] Recuperado pago perdido %s → factura %s',
                               ref, factura.numero_factura)
        except Exception as e:
            db.session.rollback()
            if logger:
                logger.error('[RECON] Error recuperando %s: %s', ref, e)

    return recuperados
