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
from datetime import date, datetime, timedelta

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
    Factura, FacturaDetalle, Pago, Gasto, PedidoFabricacion, PrendaPendiente, CajaDiaria,
    Stock, Producto, Colegio, PedidoWeb, PrecioColegio, Tarea, MovimientoInventario,
)
from app.utils.tallas import TALLA_INDIVIDUAL_A_GRUPO
from app.utils.inventario import registrar_movimiento, stock_descontado_neto

logger = logging.getLogger("raloz.asistente")

asistente_bp = Blueprint('asistente', __name__)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
# Modelo de la capa gratis; se puede cambiar por env si Google lo renombra.
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash').strip()
# Modelos que Google ya retiró (dan 404); si la env trae uno de estos, lo ignoramos.
_MODELOS_RETIRADOS = {'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro',
                      'gemini-1.0-pro', 'gemini-pro', 'gemini-2.0-flash-001'}
# Respaldo cuando Gemini falla/satura (routing invisible al Jefe). Opcional: DEEPSEEK_API_KEY en Render.
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '').strip()

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
    "- Recordatorios/Tareas: SÍ existen. Están en el menú 'Tareas' del panel; se "
    "puede crear una tarea con título y fecha. (No sugieras Google Calendar; el "
    "sistema tiene su propio módulo de Tareas.)\n"
    "- Reportes e histórico de ventas: menú 'Reportes' y 'Buscar facturas' (se puede "
    "filtrar por fechas de meses anteriores).\n"
    "- Horario del punto: lunes y sábado 10:00 a.m. – 5:00 p.m."
)


def _stock_resumen():
    """Unidades y valor de inventario por colegio (usa los precios reales del sistema)."""
    colegios = {c.id_colegio: c.nombre for c in Colegio.query.all()}
    precios = {(p.id_colegio, p.id_producto, p.talla_grupo): (p.precio_unitario or 0)
               for p in PrecioColegio.query.all()}
    agg, total_u, total_v = {}, 0, 0.0
    for s in Stock.query.all():
        a = agg.setdefault(s.id_colegio, {
            'colegio': colegios.get(s.id_colegio, f'Colegio {s.id_colegio}'),
            'unidades': 0, 'valor': 0.0})
        cant = s.cantidad or 0
        grupo = TALLA_INDIVIDUAL_A_GRUPO.get(s.talla_individual, s.talla_individual)
        val = cant * (precios.get((s.id_colegio, s.id_producto, grupo), 0) or 0)
        a['unidades'] += cant
        a['valor'] += val
        total_u += cant
        total_v += val
    return {
        'total_unidades': total_u,
        'valor_inventario_total': round(total_v),
        'por_colegio': [{'colegio': v['colegio'], 'unidades': v['unidades'],
                         'valor_inventario': round(v['valor'])} for v in agg.values()],
    }


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

    # Inventario completo: unidades + valor por colegio (y total)
    try:
        ctx['inventario'] = _stock_resumen()
    except Exception as e:
        logger.warning("asistente: fallo resumen de inventario: %s", e)

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
    if not isinstance(obj, dict):
        return texto, None
    tipo = obj.get('tipo')
    accion = None
    if tipo == 'cambiar_estado_pedido':
        estado = str(obj.get('estado', '')).upper().strip()
        factura = str(obj.get('factura', '')).strip()
        if estado in _ESTADOS_ENTREGA and factura:
            accion = {
                'tipo': tipo, 'factura': factura, 'estado': estado,
                'descripcion': f'Marcar la factura/pedido “{factura}” como: {_ESTADOS_ENTREGA[estado]}',
            }
    elif tipo == 'crear_tarea':
        titulo = str(obj.get('titulo', '')).strip()
        fecha = str(obj.get('fecha', '') or obj.get('fecha_vencimiento', '')).strip()[:10]
        if titulo:
            desc = f'Crear recordatorio: “{titulo}”' + (f' para el {fecha}' if fecha else '')
            accion = {
                'tipo': tipo, 'titulo': titulo[:200], 'fecha': fecha,
                'descripcion_tarea': str(obj.get('descripcion', '')).strip()[:500],
                'descripcion': desc,
            }
    elif tipo == 'ajustar_stock':
        colegio = str(obj.get('colegio', '')).strip()
        prenda = str(obj.get('prenda') or obj.get('texto', '')).strip()
        talla = str(obj.get('talla', '')).strip().upper()
        modo = str(obj.get('modo', '')).lower().strip()
        try:
            cantidad = int(obj.get('cantidad'))
        except Exception:
            cantidad = None
        if colegio and prenda and talla and modo in ('sumar', 'restar', 'fijar') \
                and cantidad is not None and cantidad >= 0:
            verbo = {'sumar': 'Sumar', 'restar': 'Restar', 'fijar': 'Fijar en'}[modo]
            accion = {
                'tipo': tipo, 'colegio': colegio, 'prenda': prenda[:100], 'talla': talla[:20],
                'modo': modo, 'cantidad': cantidad,
                'descripcion': f'{verbo} {cantidad} unidad(es) de “{prenda}” talla {talla} — {colegio}',
            }
    elif tipo == 'fijar_costo':
        colegio = str(obj.get('colegio', '')).strip()
        prenda = str(obj.get('prenda') or obj.get('texto', '')).strip()
        try:
            costo = float(obj.get('costo'))
        except Exception:
            costo = None
        if colegio and prenda and costo is not None and costo >= 0:
            accion = {
                'tipo': tipo, 'colegio': colegio, 'prenda': prenda[:100], 'costo': costo,
                'descripcion': f'Fijar el costo de “{prenda}” en ${int(costo):,} — {colegio}'.replace(',', '.'),
            }
    if not accion:
        return texto, None
    texto_limpio = texto[:m.start()].rstrip() or 'Te propongo esta acción:'
    return texto_limpio, accion


def _buscar_factura(ref):
    """Busca una factura por su número o por la referencia de un pedido web.
    Si piden 'la última / nueva / reciente' (o viene vacío), devuelve la más reciente."""
    r = str(ref or '').strip()
    if not r or any(p in r.lower() for p in ('ultim', 'última', 'ultima', 'nuev', 'recient')):
        return Factura.query.filter(Factura.estado != 'ANULADA') \
            .order_by(Factura.fecha_factura.desc(), Factura.id_factura.desc()).first()
    f = Factura.query.filter_by(numero_factura=r).first()
    if f:
        return f
    pedido = PedidoWeb.query.filter_by(referencia=r).first()
    if pedido and pedido.id_factura:
        return Factura.query.get(pedido.id_factura)
    return None


# ── Herramientas de BÚSQUEDA (solo lectura) que el asistente puede pedir ──
def _resolver_colegio_id(txt):
    t = (txt or '').strip().lower()
    if not t:
        return None
    for c in Colegio.query.all():
        n = (c.nombre or '').lower()
        if t in n or n in t or any(w and w in n for w in t.split()):
            return c.id_colegio
    return None


def _resolver_producto_id(texto):
    t = (texto or '').strip()
    if not t:
        return None, None
    exact = Producto.query.filter(Producto.nombre.ilike(t)).first()
    if exact:
        return exact.id_producto, exact.nombre
    p = Producto.query.filter(Producto.nombre.ilike(f'%{t}%')).order_by(Producto.id_producto).first()
    return (p.id_producto, p.nombre) if p else (None, None)


def _tool_buscar_prenda(colegio, texto):
    cid = _resolver_colegio_id(colegio)
    q = Producto.query
    if (texto or '').strip():
        q = q.filter(Producto.nombre.ilike(f'%{texto.strip()}%'))
    prods = q.limit(6).all()
    if not prods:
        return {'encontrado': False, 'mensaje': 'No hallé prendas con ese nombre.'}
    res = []
    for p in prods:
        item = {'prenda': p.nombre}
        if cid:
            _pcs = PrecioColegio.query.filter_by(id_colegio=cid, id_producto=p.id_producto).all()
            item['precios_por_grupo_talla'] = {pc.talla_grupo: pc.precio_unitario for pc in _pcs}
            # Costos: SOLO los que estén registrados (None = sin costo; el asistente no inventa)
            _costos = {pc.talla_grupo: pc.costo_unitario for pc in _pcs if pc.costo_unitario is not None}
            item['costos_por_grupo_talla'] = _costos or 'sin costo registrado'
            stock = {s.talla_individual: (s.cantidad or 0)
                     for s in Stock.query.filter_by(id_colegio=cid, id_producto=p.id_producto).all()}
            item['stock_por_talla'] = stock
            item['stock_total'] = sum(stock.values())
        res.append(item)
    return {'encontrado': True, 'colegio_id': cid, 'prendas': res}


def _tool_buscar_factura(ref):
    f = _buscar_factura(str(ref).strip())
    if not f:
        return {'encontrado': False}
    # Cuánto descontó ESTA factura del inventario (leído del kardex) → verdad absoluta
    try:
        netos = stock_descontado_neto(f.numero_factura, f.id_colegio)
    except Exception:
        netos = {}
    # Prendas del pedido + stock actual + cuánto salió del inventario por esta venta
    detalles, todo_disp, desconto_total = [], True, 0
    for d in f.detalles.all():
        st = Stock.query.filter_by(
            id_colegio=f.id_colegio, id_producto=d.id_producto,
            talla_individual=d.talla_individual).first()
        disp = int(st.cantidad or 0) if st else 0
        suf = disp >= (d.cantidad or 0)
        if not suf:
            todo_disp = False
        desc = int(netos.get((d.id_producto, d.talla_individual), 0))
        desconto_total += desc
        # Stock antes/después de ESTA venta, leído del kardex (SALIDA con su referencia)
        antes = despues = None
        movs_salida = MovimientoInventario.query.filter_by(
            referencia=f.numero_factura, id_producto=d.id_producto,
            talla_individual=d.talla_individual, tipo='SALIDA').all()
        if movs_salida:
            ult = max(movs_salida, key=lambda mv: mv.fecha or datetime.min)
            despues = ult.stock_resultante
            antes = (ult.stock_resultante or 0) + sum(mv.cantidad for mv in movs_salida)
        detalles.append({
            'prenda': d.producto.nombre if d.producto else '—',
            'talla': d.talla_individual, 'cantidad': d.cantidad,
            'stock_actual': disp, 'suficiente': suf,
            'descontado': desc,  # unidades que ESTA venta sacó del inventario
            'stock_antes': antes, 'stock_despues': despues,  # según el kardex
        })
    return {
        'encontrado': True,
        'numero_factura': f.numero_factura,
        'estado': f.estado,
        'estado_entrega': f.estado_entrega,
        'total': float(f.total or 0),
        'saldo_pendiente': float(f.saldo_pendiente or 0),
        'cliente': getattr(f, 'cliente_nombre', None),
        'telefono': getattr(f, 'cliente_telefono', None),
        'fecha': f.fecha_factura.isoformat() if f.fecha_factura else None,
        'detalles': detalles,
        'todo_disponible': todo_disp if detalles else None,
        'descontado_inventario': desconto_total,   # total de unidades que salieron del inventario
        'unidades_pedido': sum((d.get('cantidad') or 0) for d in detalles),
    }


def _tool_pedidos_telefono(tel):
    dig = re.sub(r'\D', '', str(tel or ''))
    if len(dig) < 7:
        return {'encontrado': False}
    ult = dig[-10:]
    cand = (PedidoWeb.query
            .filter(PedidoWeb.telefono_cliente.like(f'%{ult[-7:]}%'))
            .order_by(PedidoWeb.fecha_creacion.desc()).limit(10).all())
    pedidos = []
    for p in cand:
        if re.sub(r'\D', '', p.telefono_cliente or '')[-10:] != ult:
            continue
        pedidos.append({
            'referencia': p.referencia, 'estado': p.estado,
            'total': float(getattr(p, 'total', 0) or 0),
            'fecha': p.fecha_creacion.isoformat() if getattr(p, 'fecha_creacion', None) else None,
        })
    return {'encontrado': bool(pedidos), 'pedidos': pedidos}


def _tool_ventas_periodo(desde=None, hasta=None, mes=None, anio=None):
    """Ventas (facturas + total) en un mes/año o en un rango de fechas."""
    d = h = None
    if mes and anio:
        try:
            y, m = int(anio), int(mes)
            d = date(y, m, 1)
            h = date(y, 12, 31) if m == 12 else date(y, m + 1, 1) - timedelta(days=1)
        except Exception:
            pass
    for val, attr in ((desde, 'd'), (hasta, 'h')):
        if val:
            try:
                pd = datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
                if attr == 'd':
                    d = pd
                else:
                    h = pd
            except Exception:
                pass
    if not d or not h:
        return {'error': 'Especifica un mes y año, o un rango de fechas (YYYY-MM-DD).'}
    row = db.session.query(
        func.count(Factura.id_factura), func.coalesce(func.sum(Factura.total), 0)
    ).filter(and_(Factura.fecha_factura >= d, Factura.fecha_factura <= h,
                  Factura.estado != 'ANULADA')).first()
    return {'desde': d.isoformat(), 'hasta': h.isoformat(),
            'facturas': int(row[0] or 0), 'total': float(row[1] or 0)}


def _tool_top_productos(desde=None, hasta=None, mes=None, anio=None, limite=8):
    """Prendas más vendidas (unidades y $) en un periodo. Sin periodo = histórico."""
    d = h = None
    if mes and anio:
        try:
            y, m = int(anio), int(mes)
            d = date(y, m, 1)
            h = date(y, 12, 31) if m == 12 else date(y, m + 1, 1) - timedelta(days=1)
        except Exception:
            pass
    for val, attr in ((desde, 'd'), (hasta, 'h')):
        if val:
            try:
                pd = datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
                if attr == 'd':
                    d = pd
                else:
                    h = pd
            except Exception:
                pass
    try:
        limite = max(1, min(int(limite or 8), 20))
    except Exception:
        limite = 8
    q = (db.session.query(
            FacturaDetalle.id_producto,
            func.sum(FacturaDetalle.cantidad),
            func.sum(FacturaDetalle.total_linea))
         .join(Factura, Factura.id_factura == FacturaDetalle.id_factura)
         .filter(Factura.estado != 'ANULADA'))
    if d and h:
        q = q.filter(and_(Factura.fecha_factura >= d, Factura.fecha_factura <= h))
    q = q.group_by(FacturaDetalle.id_producto) \
         .order_by(func.sum(FacturaDetalle.cantidad).desc()).limit(limite)
    filas = q.all()
    if not filas:
        return {'encontrado': False, 'mensaje': 'No hay ventas registradas en ese periodo.'}
    pids = [f[0] for f in filas]
    nombres = {p.id_producto: p.nombre for p in Producto.query.filter(Producto.id_producto.in_(pids)).all()}
    productos = [{'prenda': nombres.get(f[0], f'Prod#{f[0]}'),
                  'unidades': int(f[1] or 0), 'total': float(f[2] or 0)} for f in filas]
    return {'encontrado': True,
            'periodo': (f'{d.isoformat()} → {h.isoformat()}' if d and h else 'histórico'),
            'productos': productos}


def _tool_movimientos_prenda(colegio, texto, talla=None):
    """Kardex de una prenda: entradas/salidas/ajustes recientes, con el stock
    antes y después de cada movimiento, su factura/motivo y quién lo hizo."""
    cid = _resolver_colegio_id(colegio)
    pid, pnombre = _resolver_producto_id(str(texto or ''))
    if not pid:
        return {'encontrado': False, 'mensaje': 'No hallé esa prenda.'}
    q = MovimientoInventario.query.filter_by(id_producto=pid)
    if cid:
        q = q.filter_by(id_colegio=cid)
    if talla:
        q = q.filter_by(talla_individual=str(talla).strip().upper())
    movs = q.order_by(MovimientoInventario.fecha.desc()).limit(10).all()
    if not movs:
        return {'encontrado': False, 'prenda': pnombre, 'mensaje': 'Sin movimientos registrados.'}
    out = []
    for m in movs:
        antes = None
        if m.tipo == 'ENTRADA':
            antes = (m.stock_resultante or 0) - (m.cantidad or 0)
        elif m.tipo == 'SALIDA':
            antes = (m.stock_resultante or 0) + (m.cantidad or 0)
        out.append({
            'fecha': m.fecha.isoformat() if m.fecha else None,
            'tipo': m.tipo, 'cantidad': m.cantidad,
            'stock_antes': antes, 'stock_despues': m.stock_resultante,
            'talla': m.talla_individual, 'motivo': m.motivo,
            'referencia': m.referencia, 'usuario': m.usuario,
        })
    return {'encontrado': True, 'prenda': pnombre, 'talla': talla, 'movimientos': out}


def _ejecutar_busqueda(obj):
    tipo = obj.get('tipo')
    if tipo == 'movimientos':
        return _tool_movimientos_prenda(obj.get('colegio', ''),
                                        obj.get('texto') or obj.get('prenda', ''), obj.get('talla'))
    if tipo == 'buscar_prenda':
        return _tool_buscar_prenda(obj.get('colegio', ''), obj.get('texto') or obj.get('prenda', ''))
    if tipo == 'buscar_factura':
        return _tool_buscar_factura(obj.get('referencia') or obj.get('factura', ''))
    if tipo == 'pedidos_cliente':
        return _tool_pedidos_telefono(obj.get('telefono', ''))
    if tipo == 'ventas_periodo':
        return _tool_ventas_periodo(obj.get('desde'), obj.get('hasta'),
                                    obj.get('mes'), obj.get('anio') or obj.get('año'))
    if tipo == 'top_productos':
        return _tool_top_productos(obj.get('desde'), obj.get('hasta'),
                                   obj.get('mes'), obj.get('anio') or obj.get('año'),
                                   obj.get('limite') or 8)
    return {'error': 'búsqueda no soportada'}


def _extraer_json_marcador(texto, marcador):
    """Extrae el objeto JSON que sigue a `marcador:` en el texto (o None)."""
    m = re.search(marcador + r':\s*(\{.*)', texto, re.DOTALL)
    if not m:
        return None
    crudo = m.group(1)
    for fin in range(len(crudo), 0, -1):
        if crudo[fin - 1] != '}':
            continue
        try:
            return json.loads(crudo[:fin])
        except Exception:
            continue
    return None


def _llamar_gemini(prompt_text):
    """Llama a Gemini probando modelos vigentes. Devuelve (texto|None, detalle)."""
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600},
    }
    candidatos = []
    if GEMINI_MODEL and GEMINI_MODEL not in _MODELOS_RETIRADOS:
        candidatos.append(GEMINI_MODEL)
    for m in ('gemini-3.6-flash', 'gemini-flash-latest', 'gemini-2.5-flash'):
        if m not in candidatos:
            candidatos.append(m)
    candidatos = candidatos[:3]

    ultimo_detalle = ''
    # Hasta 3 pasadas por la lista si todo dio 503 (alta demanda momentánea de Google).
    for intento in range(3):
        hubo_503 = False
        for modelo in candidatos:
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{modelo}:generateContent?key={GEMINI_API_KEY}")
            try:
                r = requests.post(url, json=payload, timeout=15)
            except Exception as e:
                ultimo_detalle = f'conexión: {e}'
                continue
            if r.status_code == 200:
                try:
                    return r.json()['candidates'][0]['content']['parts'][0]['text'].strip(), None
                except Exception:
                    return '', 'respuesta_vacia'
            ultimo_detalle = f'{r.status_code}: {r.text[:200]}'
            logger.warning("asistente: Gemini %s -> %s: %s", modelo, r.status_code, r.text[:200])
            if r.status_code in (503,) or 'UNAVAILABLE' in r.text.upper():
                hubo_503 = True
            # Si el problema es la LLAVE, no tiene sentido reintentar.
            if r.status_code in (400, 403) and 'API_KEY' in r.text.upper():
                return None, ultimo_detalle
        if not hubo_503:
            break
        time.sleep(1.5)  # espera y reintenta la lista completa
    # Respaldo: si Gemini no respondió, intenta DeepSeek (cambio de motor invisible al Jefe).
    ds, ds_det = _llamar_deepseek(prompt_text)
    if ds is not None:
        return ds, None
    return None, ds_det or ultimo_detalle


def _llamar_deepseek(prompt_text):
    """Respaldo cuando Gemini falla/satura. deepseek-chat (no 'pensante')."""
    if not DEEPSEEK_API_KEY:
        return None, 'sin_deepseek'
    try:
        r = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'deepseek-chat',
                  'messages': [{'role': 'user', 'content': prompt_text}],
                  'temperature': 0.2, 'max_tokens': 700, 'stream': False},
            timeout=20,
        )
    except Exception as e:
        return None, f'deepseek conexión: {e}'
    if r.status_code != 200:
        logger.warning('asistente: DeepSeek -> %s: %s', r.status_code, r.text[:200])
        return None, f'deepseek {r.status_code}'
    try:
        return (r.json()['choices'][0]['message']['content'] or '').strip(), None
    except Exception:
        return '', 'deepseek_vacio'


def _error_gemini(detalle):
    """Devuelve la respuesta de error adecuada (saturación vs. problema real)."""
    d = (detalle or '').upper()
    if 'UNAVAILABLE' in d or (detalle or '').startswith('503'):
        return jsonify({
            'error': '⏳ Los modelos de IA gratis de Google están saturados ahora mismo '
                     '(mucha demanda). Espera unos segundos y vuelve a intentar.',
            'detalle': detalle, 'code': 'ocupado',
        }), 503
    return jsonify({
        'error': 'El asistente no respondió. Revisa la GEMINI_API_KEY o el modelo.',
        'detalle': detalle, 'code': 'gemini_error',
    }), 502


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
        "Eres RALOZ, el copiloto inteligente del negocio de uniformes escolares (Bogotá). "
        "No eres un chatbot: eres el asistente estratégico del dueño (trátalo como *Jefe*, "
        "sin repetirlo en cada frase). Español, profesional pero cercano, con mentalidad "
        "empresarial; claro y directo, nunca robótico ni técnico.\n"
        "\n"
        "MISIÓN: convertir los datos en decisiones. Cuando aporte, sigue la cadena "
        "DATOS → ANÁLISIS → CONCLUSIÓN → ACCIÓN RECOMENDADA; no solo muestres números, "
        "explica qué significan. En consultas simples, responde breve.\n"
        "\n"
        "VERACIDAD (absoluta): usa SOLO los datos reales del sistema y las herramientas. "
        "NUNCA inventes stock, precios, ventas, facturas, clientes, costos, fechas ni "
        "movimientos. Si no hay dato, dilo con honestidad y di dónde mirarlo. Distingue "
        "'0 unidades' de 'sin información'. La base de datos es la fuente de verdad; ante "
        "una diferencia, avísala y sugiere revisar el kardex.\n"
        "\n"
        "REGLAS FINANCIERAS (innegociables): el *valor del inventario* NO es dinero ganado, "
        "ni ventas, ni utilidad. Ingresos ≠ utilidad. Utilidad = ingresos − costos (− gastos "
        "si hay). Margen = precio − costo. Si faltan costos o gastos, NO calcules utilidad sin "
        "advertirlo. Si el Jefe confunde conceptos (ej. 'esos $80M son ganancia'), corrígelo "
        "con respeto: esos $80M son el valor del inventario, no la utilidad.\n"
        "\n"
        "DISTINGUE SIEMPRE: DATO (del sistema) · CÁLCULO (matemático) · ESTIMACIÓN (con "
        "supuestos, dilo) · RECOMENDACIÓN (sugerencia tuya). Nunca presentes una estimación "
        "o recomendación como si fuera un dato oficial.\n"
        "\n"
        "PROACTIVIDAD: si al responder detectas algo importante (stock bajo, saldo por "
        "cobrar, una diferencia), menciónalo con un breve ⚠️ y una acción recomendada — solo "
        "si es relevante, no llenes cada respuesta de datos extra.\n"
        "\n"
        "ACCIONES: consultar y analizar es directo. MODIFICAR datos (ajustar stock, cambiar "
        "estado, crear recordatorio) SIEMPRE requiere confirmación (usa el formato ACCION_JSON "
        "de abajo; nunca afirmes que ya lo hiciste antes de confirmar). Nunca digas que una "
        "tarea quedó creada si la herramienta no lo confirmó.\n"
        "\n"
        "COSTOS Y RENTABILIDAD: NUNCA inventes un costo. Si una prenda NO tiene costo "
        "registrado, dilo ('esa referencia todavía no tiene costo registrado; puedo darte "
        "ventas y precio, pero no la utilidad real') y ofrece registrarlo. Con precio Y costo: "
        "utilidad bruta/unidad = precio − costo; margen % = (precio − costo)/precio × 100; "
        "utilidad total = utilidad/unidad × unidades vendidas (acláralo como BRUTA, sin gastos). "
        "'Producto más rentable' NO es solo el de mayor margen %: distingue mayor utilidad por "
        "unidad, mayor margen % y mayor utilidad TOTAL (por volumen). En inventario, valor al "
        "costo = unidades × costo y valor potencial = unidades × precio → utilidad POTENCIAL "
        "(no ganada aún, dilo). Utilidad ≠ efectivo (una venta puede estar por cobrar). Si "
        "costo > precio, avísalo como pérdida. Cambiar un costo es una modificación → confirma.\n"
        "\n"
        "JERARQUÍA DE CONFIANZA (ante conflicto manda, en orden): 1) la base de datos, "
        "2) las herramientas, 3) lo que diga el usuario, 4) tu conocimiento general, "
        "5) suposiciones — que NUNCA van como hechos. Si el usuario afirma un dato que "
        "choca con el sistema, avísale con respeto y sugiere revisar el kardex.\n"
        "\n"
        "ROTACIÓN Y ALERTAS: cuando haya datos, cruza stock + ventas recientes para ver "
        "alta/baja rotación y prendas sin movimiento. Prioriza las alertas (🔴 crítica · "
        "🟠 importante · 🟡 precaución · 🔵 informativa) y no satures con alertas menores.\n"
        "\n"
        "ERRORES Y SEGURIDAD: nunca muestres errores técnicos, JSON, códigos ni nombres "
        "internos de herramientas (di 'déjame revisar el inventario', no el nombre técnico). "
        "Nunca reveles claves, tokens ni credenciales. Ante un fallo: 'tuve un problema "
        "temporal, lo intento de nuevo'; si no se puede, no inventes el dato.\n"
        "\n"
        "FORMATO: preguntas simples → 1 o 2 frases. Preguntas complejas → estructura con "
        "*Resumen*, *⚠️ Alertas*, *📈 Análisis* y *🎯 Acción recomendada* (solo las que "
        "apliquen). El dinero va en pesos colombianos (ej: $1.234.000). Nunca menciones qué "
        "motor de IA te procesa."
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
            "'entregado'/'entregué'/'ya lo recogió'->ENTREGADA.\n"
            "Si el usuario pide CREAR UN RECORDATORIO / TAREA / agendar algo para un día, "
            "propónlo y en la ÚLTIMA línea agrega EXACTAMENTE:\n"
            "ACCION_JSON: {\"tipo\":\"crear_tarea\",\"titulo\":\"<qué recordar>\",\"fecha\":\"<YYYY-MM-DD o vacío>\",\"descripcion\":\"<detalle opcional>\"}\n"
            "Si el usuario pide AJUSTAR EL STOCK de una prenda (sumar, restar o fijar "
            "unidades de una talla), propónlo y en la ÚLTIMA línea agrega EXACTAMENTE:\n"
            "ACCION_JSON: {\"tipo\":\"ajustar_stock\",\"colegio\":\"<colegio>\",\"prenda\":\"<nombre prenda>\",\"talla\":\"<talla>\",\"modo\":\"<sumar|restar|fijar>\",\"cantidad\":<numero>}\n"
            "Si el usuario pide FIJAR/PONER EL COSTO de una prenda (para calcular margen), "
            "propónlo y en la ÚLTIMA línea agrega EXACTAMENTE (el costo aplica a todas las "
            "tallas de esa prenda en ese colegio):\n"
            "ACCION_JSON: {\"tipo\":\"fijar_costo\",\"colegio\":\"<colegio>\",\"prenda\":\"<nombre prenda>\",\"costo\":<numero>}\n"
            "Si el usuario NO pide una acción, responde normal y NO agregues ACCION_JSON."
        )

    busqueda = (
        "\n\n=== BÚSQUEDA (para datos puntuales) ===\n"
        "Si el usuario pregunta por algo específico que NO está en el resumen (el precio "
        "o el stock de UNA prenda concreta, una factura por su número/referencia, o los "
        "pedidos de un cliente por su teléfono), responde ÚNICAMENTE con una línea así y "
        "nada más:\n"
        "BUSCAR: {\"tipo\":\"buscar_prenda\",\"colegio\":\"<colegio>\",\"texto\":\"<nombre prenda>\"}\n"
        "BUSCAR: {\"tipo\":\"movimientos\",\"colegio\":\"<colegio>\",\"texto\":\"<prenda>\",\"talla\":\"<talla o vacío>\"}  → kardex de la prenda: entradas/salidas/ajustes con el stock antes y después, la factura y quién lo movió (úsalo para '¿cuánto había antes?', '¿quién ajustó el stock?', '¿qué movimientos tuvo?')\n"
        "BUSCAR: {\"tipo\":\"buscar_factura\",\"referencia\":\"<numero, RALOZ-..., o 'ultima' para la más reciente>\"}  → devuelve la factura con sus prendas, cuánto descontó del inventario (antes→después) y si descontó todo bien\n"
        "BUSCAR: {\"tipo\":\"pedidos_cliente\",\"telefono\":\"<numero>\"}\n"
        "BUSCAR: {\"tipo\":\"ventas_periodo\",\"mes\":<1-12>,\"anio\":<año>}  (o usa \"desde\"/\"hasta\" en formato YYYY-MM-DD para ventas de un mes/rango anterior)\n"
        "BUSCAR: {\"tipo\":\"top_productos\",\"limite\":<n>}  → prendas más vendidas (unidades y $); sin mes/rango = histórico, o agrega \"mes\"/\"anio\" o \"desde\"/\"hasta\". Úsalo para 'qué es lo que más se vende' / 'la mejor prenda'\n"
        "Solo UNA búsqueda por vez. Si la respuesta ya está en el resumen, NO uses BUSCAR."
    )

    base = (
        f"{sistema}{busqueda}{acciones}\n\n=== DATOS REALES DEL SISTEMA (hoy {datos.get('fecha_hoy')}) ===\n"
        f"{json.dumps(datos, ensure_ascii=False, default=str)}\n\n"
        f"=== MANUAL DEL SISTEMA ===\n{MANUAL}\n\n"
        f"=== PREGUNTA DEL USUARIO ===\n{pregunta}"
    )

    texto, detalle = _llamar_gemini(base)
    if texto is None:
        return _error_gemini(detalle)

    # Bucle de búsqueda: si la IA pide un dato con BUSCAR, lo consultamos y se lo damos.
    ultima_busqueda = None   # para devolver datos estructurados a la UI (tarjetas)
    for _ in range(2):
        consulta = _extraer_json_marcador(texto, 'BUSCAR')
        if not consulta:
            break
        try:
            resultado = _ejecutar_busqueda(consulta)
        except Exception as e:
            logger.warning("asistente: búsqueda falló: %s", e)
            resultado = {'error': 'la búsqueda falló'}
        ultima_busqueda = {'tipo': consulta.get('tipo'), 'resultado': resultado}
        seguimiento = (
            f"{base}\n\n=== RESULTADO DE LA BÚSQUEDA ({consulta.get('tipo')}) ===\n"
            f"{json.dumps(resultado, ensure_ascii=False, default=str)}\n\n"
            "Con ese resultado responde al usuario en español, claro y breve. No inventes; "
            "si no se encontró, dilo. No vuelvas a escribir BUSCAR salvo que necesites otro dato distinto."
        )
        texto, detalle = _llamar_gemini(seguimiento)
        if texto is None:
            return _error_gemini(detalle)

    if not texto:
        texto = 'No obtuve una respuesta. Intenta reformular la pregunta.'

    respuesta = {'respuesta': texto}
    # Datos estructurados de la última búsqueda → la UI los pinta como tarjetas.
    if ultima_busqueda and isinstance(ultima_busqueda.get('resultado'), dict) \
            and not ultima_busqueda['resultado'].get('error'):
        respuesta['datos'] = ultima_busqueda
    if puede_accionar:
        texto_limpio, accion = _extraer_accion(texto)
        if accion:
            respuesta['respuesta'] = texto_limpio
            respuesta['accion'] = accion
    return jsonify(respuesta), 200


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
    tipo = data.get('tipo')

    # ── Crear recordatorio / tarea ──
    if tipo == 'crear_tarea':
        titulo = str(data.get('titulo', '')).strip()[:200]
        if not titulo:
            return jsonify({'error': 'Falta el título del recordatorio.'}), 400
        fecha = None
        if data.get('fecha'):
            try:
                fecha = datetime.strptime(str(data['fecha'])[:10], '%Y-%m-%d').date()
            except Exception:
                fecha = None
        ident = get_current_identity()
        t = Tarea(titulo=titulo,
                  descripcion=(str(data.get('descripcion_tarea', '')).strip() or None),
                  fecha_vencimiento=fecha,
                  creada_por=ident['id_usuario'])
        db.session.add(t)
        db.session.commit()
        try:
            registrar_auditoria('tareas', t.id_tarea, 'CREADA',
                                f'[Asistente] Recordatorio creado por {ident.get("usuario")}')
        except Exception as e:
            logger.warning("asistente: no se pudo auditar tarea: %s", e)
        return jsonify({
            'ok': True,
            'mensaje': f'✅ Recordatorio creado: “{titulo}”'
                       + (f' para el {fecha.isoformat()}' if fecha else '')
                       + '. Lo ves en el menú *Tareas*.',
        }), 200

    # ── Ajustar stock (sumar / restar / fijar) ──
    if tipo == 'ajustar_stock':
        cid = _resolver_colegio_id(str(data.get('colegio', '')))
        pid, pnombre = _resolver_producto_id(str(data.get('prenda', '')))
        talla = str(data.get('talla', '')).strip().upper()
        modo = str(data.get('modo', '')).lower().strip()
        try:
            cantidad = int(data.get('cantidad'))
        except Exception:
            cantidad = None
        if not cid:
            return jsonify({'error': 'No identifiqué el colegio.'}), 400
        if not pid:
            return jsonify({'error': 'No identifiqué la prenda.'}), 404
        if not talla or modo not in ('sumar', 'restar', 'fijar') or cantidad is None or cantidad < 0:
            return jsonify({'error': 'Datos del ajuste inválidos.'}), 400
        ident = get_current_identity()
        tipo_mov = {'sumar': 'ENTRADA', 'restar': 'SALIDA', 'fijar': 'AJUSTE'}[modo]
        try:
            stock, _mov = registrar_movimiento(cid, pid, talla, tipo_mov, cantidad,
                                               usuario=ident['usuario'], motivo='[Asistente]')
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning("asistente: ajustar_stock falló: %s", e)
            return jsonify({'error': 'No pude aplicar el ajuste de stock.'}), 500
        try:
            registrar_auditoria('stock', stock.id_stock, tipo_mov,
                                f'[Asistente] {pnombre} T{talla}: {modo} {cantidad} '
                                f'-> {stock.cantidad} por {ident.get("usuario")}')
        except Exception:
            pass
        return jsonify({
            'ok': True,
            'mensaje': f'✅ Stock actualizado: {pnombre} talla {talla} → '
                       f'{stock.cantidad} unidades.',
        }), 200

    # ── Fijar el costo de una prenda (para margen/rentabilidad) ──
    if tipo == 'fijar_costo':
        cid = _resolver_colegio_id(str(data.get('colegio', '')))
        pid, pnombre = _resolver_producto_id(str(data.get('prenda', '')))
        try:
            costo = float(data.get('costo'))
        except Exception:
            costo = None
        if not cid:
            return jsonify({'error': 'No identifiqué el colegio.'}), 400
        if not pid:
            return jsonify({'error': 'No identifiqué la prenda.'}), 404
        if costo is None or costo < 0:
            return jsonify({'error': 'Costo inválido.'}), 400
        rows = PrecioColegio.query.filter_by(id_colegio=cid, id_producto=pid).all()
        if not rows:
            return jsonify({'error': f'“{pnombre}” no tiene precios en ese colegio; '
                                     'primero configura el precio.'}), 404
        ident = get_current_identity()
        for r in rows:
            r.costo_unitario = costo
        db.session.commit()
        try:
            registrar_auditoria('precios_colegio', rows[0].id_precio, 'ACTUALIZAR',
                                f'[Asistente] costo de {pnombre} = ${costo} '
                                f'({len(rows)} talla/s) por {ident.get("usuario")}')
        except Exception:
            pass
        costo_fmt = f'${int(costo):,}'.replace(',', '.')
        return jsonify({
            'ok': True,
            'mensaje': f'✅ Costo de {pnombre} fijado en {costo_fmt} '
                       f'(aplica a {len(rows)} talla/s). Ya puedo calcular su margen.',
        }), 200

    if tipo != 'cambiar_estado_pedido':
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
