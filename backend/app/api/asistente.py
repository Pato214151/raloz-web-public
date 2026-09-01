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
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import func, and_

from app import db, limiter
from app.utils.decorators import rol_requerido, get_current_identity, registrar_auditoria
from app.models import (
    Factura, FacturaDetalle, Pago, Gasto, PedidoFabricacion, PrendaPendiente, CajaDiaria,
    Stock, Producto, Colegio, PedidoWeb, PrecioColegio, Tarea, MovimientoInventario,
    AccionAsistente, Evento,
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
# Grok (xAI), API compatible con OpenAI. Si está configurada, es el motor PRINCIPAL.
GROK_API_KEY = os.getenv('GROK_API_KEY', '').strip()
GROK_MODEL = os.getenv('GROK_MODEL', 'grok-3').strip()

# ¿Hay AL MENOS un motor de IA configurado?
def _hay_ia():
    return bool(GROK_API_KEY or GEMINI_API_KEY or DEEPSEEK_API_KEY)

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
    elif tipo == 'revertir':
        try:
            id_accion = int(obj.get('id_accion'))
        except Exception:
            id_accion = None
        if id_accion:
            acc = AccionAsistente.query.get(id_accion)
            if acc and acc.reversible and acc.resultado != 'REVERTIDA':
                accion = {
                    'tipo': tipo, 'id_accion': id_accion,
                    'descripcion': f'Deshacer: {acc.descripcion or ("acción #" + str(id_accion))}',
                }
    elif tipo == 'crear_regla':
        texto_regla = str(obj.get('texto', '')).strip()
        categoria = str(obj.get('categoria', 'OTRA')).upper().strip()[:20] or 'OTRA'
        if texto_regla:
            params = obj.get('parametros') if isinstance(obj.get('parametros'), dict) else None
            accion = {
                'tipo': tipo, 'categoria': categoria, 'texto': texto_regla[:400],
                'parametros': params,
                'descripcion': f'Guardar regla [{categoria}]: “{texto_regla[:120]}”',
            }
    elif tipo == 'crear_objetivo':
        try:
            meta = float(obj.get('meta'))
            anio = int(obj.get('anio'))
        except Exception:
            meta = anio = None
        mes = obj.get('mes')
        mes = int(mes) if mes not in (None, '', 0) else None
        if meta and meta > 0 and anio:
            desc = str(obj.get('descripcion', '')).strip()[:200] or f'Meta {anio}'
            accion = {
                'tipo': tipo, 'meta': meta, 'anio': anio, 'mes': mes,
                'descripcion_obj': desc,
                'descripcion': f'Guardar meta: {desc} = ${int(meta):,}'.replace(',', '.'),
            }
    elif tipo == 'estimar_costos':
        try:
            factor = float(obj.get('factor', 0.6))
        except Exception:
            factor = 0.6
        factor = min(max(factor, 0.05), 1.0)
        accion = {
            'tipo': tipo, 'factor': factor,
            'solo_faltantes': bool(obj.get('solo_faltantes', True)),
            'descripcion': f'Poner costos ESTIMADOS (precio × {factor:.0%}, '
                           f'margen ~{round((1-factor)*100)}%) en las prendas sin costo',
        }
    elif tipo == 'crear_memoria':
        texto_mem = str(obj.get('texto', '')).strip()
        tipo_mem = str(obj.get('tipo_memoria', 'NOTA')).upper().strip()[:20] or 'NOTA'
        if texto_mem:
            accion = {
                'tipo': tipo, 'tipo_memoria': tipo_mem, 'texto': texto_mem[:500],
                'descripcion': f'Recordar [{tipo_mem}]: “{texto_mem[:120]}”',
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


def _tool_simular_precio(colegio, prenda, porcentaje):
    """SIMULACIÓN (no toca la BD): compara margen actual vs con un % de cambio de
    precio, usando precios y costos REALES. Solo simula lo que tiene costo."""
    try:
        pct = float(porcentaje)
    except Exception:
        return {'error': 'Indica el porcentaje de cambio (ej: 5 o -10).'}
    cid = _resolver_colegio_id(colegio) if colegio else None
    pid, _pn = _resolver_producto_id(prenda) if prenda else (None, None)
    q = PrecioColegio.query
    if cid:
        q = q.filter_by(id_colegio=cid)
    if pid:
        q = q.filter_by(id_producto=pid)
    rows = q.limit(300).all()
    if not rows:
        return {'encontrado': False, 'mensaje': 'No hay precios para simular con esos filtros.'}
    nombres = {p.id_producto: p.nombre for p in
               Producto.query.filter(Producto.id_producto.in_({r.id_producto for r in rows})).all()}
    items, sin_costo = [], 0
    for r in rows:
        if r.costo_unitario is None:
            sin_costo += 1
            continue
        pa, co = r.precio_unitario, r.costo_unitario
        pn = round(pa * (1 + pct / 100))
        items.append({
            'prenda': nombres.get(r.id_producto, f'Prod#{r.id_producto}'),
            'talla_grupo': r.talla_grupo,
            'precio_actual': pa, 'costo': co,
            'margen_actual': round((pa - co) / pa * 100) if pa else 0,
            'precio_nuevo': pn,
            'margen_nuevo': round((pn - co) / pn * 100) if pn else 0,
            'utilidad_actual': round(pa - co), 'utilidad_nueva': round(pn - co),
        })
    return {
        'encontrado': bool(items) or sin_costo > 0,
        'tipo_sim': 'simular_precio', 'porcentaje': pct,
        'items': items[:12], 'con_costo': len(items), 'sin_costo': sin_costo,
        'nota': 'Escenario matemático: asume las mismas ventas; la demanda real puede cambiar.',
    }


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


# Campos con datos personales que NO deben salir del backend hacia el modelo de
# IA externo ni pintarse en tarjetas (minimización de PII — Ley 1581).
_PII_KEYS = {'telefono', 'cliente_telefono', 'telefono_cliente', 'email',
             'cliente_email', 'correo', 'direccion', 'cliente_direccion',
             'nit', 'cliente_nit'}


def _sin_pii(obj):
    """Devuelve una copia del resultado sin campos personales (teléfono, correo,
    dirección, NIT). Recursivo sobre dicts y listas."""
    if isinstance(obj, dict):
        return {k: _sin_pii(v) for k, v in obj.items() if k not in _PII_KEYS}
    if isinstance(obj, list):
        return [_sin_pii(x) for x in obj]
    return obj


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
    if tipo == 'simular_precio':
        return _tool_simular_precio(obj.get('colegio'), obj.get('prenda') or obj.get('texto'),
                                    obj.get('porcentaje'))
    if tipo == 'bitacora':
        return _tool_bitacora(obj.get('limite') or 10)
    if tipo == 'observar':
        return _tool_observar()
    if tipo == 'home':
        return _tool_home()
    if tipo == 'calendario':
        return _tool_calendario(obj.get('desde'), obj.get('hasta'), obj.get('dias'))
    if tipo == 'ventas_por_dia':
        return _tool_ventas_por_dia(obj.get('desde'), obj.get('hasta'), obj.get('dias'))
    return {'error': 'búsqueda no soportada'}


def _tool_ventas_por_dia(desde, hasta, dias):
    """Ventas agrupadas por DÍA DE LA SEMANA en un rango (por defecto, últimos
    90 días). Para decisiones tipo '¿me conviene contratar para lunes/sábado?':
    dice cuánto se factura en promedio cada uno de esos días."""
    hoy = date.today()

    def _parse(s, default):
        try:
            return datetime.strptime(str(s)[:10], '%Y-%m-%d').date()
        except Exception:
            return default

    d1 = _parse(hasta, hoy)
    d0 = _parse(desde, hoy - timedelta(days=90))
    if d1 < d0:
        d0, d1 = d1, d0
    filtro = set()
    for nom in (dias or []):
        k = _DIAS_SEMANA.get(str(nom).strip().lower())
        if k is not None:
            filtro.add(k)

    # Cuántas veces cae cada día de la semana en el rango (para el promedio/día)
    ocur = {i: 0 for i in range(7)}
    total_dias = min((d1 - d0).days + 1, 800)
    cur = d0
    for _ in range(total_dias):
        ocur[cur.weekday()] += 1
        cur += timedelta(days=1)

    agg = {i: {'total': 0.0, 'facturas': 0} for i in range(7)}
    rows = (Factura.query
            .filter(Factura.estado != 'ANULADA',
                    Factura.fecha_factura >= d0, Factura.fecha_factura <= d1)
            .all())
    for f in rows:
        if not f.fecha_factura:
            continue
        wd = f.fecha_factura.weekday()
        agg[wd]['total'] += (f.total or 0)
        agg[wd]['facturas'] += 1

    salida = []
    for i in range(7):
        if filtro and i not in filtro:
            continue
        oc = ocur[i]
        salida.append({
            'dia': _NOMBRE_DIA[i],
            'total': round(agg[i]['total']),
            'facturas': agg[i]['facturas'],
            'ocurrencias': oc,
            'promedio_por_dia': round(agg[i]['total'] / oc) if oc else 0,
        })
    return {
        'encontrado': True, 'tipo_vd': 'ventas_por_dia',
        'desde': d0.isoformat(), 'hasta': d1.isoformat(),
        'dias': salida,
        'nota': 'Es FACTURACIÓN (no utilidad). Para punto de equilibrio compara con '
                'el margen si hay costos; si no, dilo.',
    }


_DIAS_SEMANA = {
    'lunes': 0, 'martes': 1, 'miercoles': 2, 'miércoles': 2, 'jueves': 3,
    'viernes': 4, 'sabado': 5, 'sábado': 5, 'domingo': 6,
}
_NOMBRE_DIA = {0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves',
               4: 'viernes', 5: 'sábado', 6: 'domingo'}


def _tool_calendario(desde, hasta, dias):
    """Capacidad universal de calendario: cuenta cuántos días de la semana caen
    en un rango (determinista, sin gastar IA). Sin desde/hasta = mes actual."""
    from calendar import monthrange
    hoy = date.today()

    def _parse(s, default):
        try:
            return datetime.strptime(str(s)[:10], '%Y-%m-%d').date()
        except Exception:
            return default

    d0 = _parse(desde, date(hoy.year, hoy.month, 1))
    d1 = _parse(hasta, date(hoy.year, hoy.month, monthrange(hoy.year, hoy.month)[1]))
    if d1 < d0:
        d0, d1 = d1, d0
    objetivo = set()
    for nom in (dias or []):
        k = _DIAS_SEMANA.get(str(nom).strip().lower())
        if k is not None:
            objetivo.add(k)
    conteo, fechas = {}, []
    total_dias = min((d1 - d0).days + 1, 420)   # tope de seguridad (~14 meses)
    cur = d0
    for _ in range(total_dias):
        wd = cur.weekday()
        if not objetivo or wd in objetivo:
            nombre = _NOMBRE_DIA[wd]
            conteo[nombre] = conteo.get(nombre, 0) + 1
            if len(fechas) < 60:
                fechas.append(cur.isoformat())
        cur += timedelta(days=1)
    return {
        'encontrado': True, 'tipo_cal': 'calendario',
        'desde': d0.isoformat(), 'hasta': d1.isoformat(),
        'dias_pedidos': [_NOMBRE_DIA[k] for k in sorted(objetivo)] or 'todos',
        'conteo': conteo,
        'total': sum(conteo.values()),
        'fechas': fechas,
    }


def _bloque_politica():
    """Reglas del negocio + decisiones + objetivos, para que RALOZ respete la
    política y conozca las metas. Va en el prompt de cada consulta."""
    try:
        from app.services.business_memory import (
            reglas_texto, memoria_texto, progreso_objetivos)
    except Exception:
        return ''
    partes = []
    try:
        from app.models import ConfigSitio
        if ConfigSitio.get('costos_estimados') == '1':
            factor = ConfigSitio.get('costos_factor', '0.6')
            try:
                margen = round((1 - float(factor)) * 100)
            except Exception:
                margen = 40
            partes.append(
                f"⚠️ COSTOS ESTIMADOS: los costos actuales son APROXIMADOS "
                f"(precio × {factor}, margen ~{margen}%), NO son costos reales de "
                f"producción. Cuando hables de margen/utilidad acláralo SIEMPRE "
                f"('margen estimado, aún sin costos reales') y sugiere cargar los reales.")
    except Exception:
        pass
    try:
        rt = reglas_texto()
        if rt:
            partes.append("REGLAS DEL NEGOCIO (respétalas SIEMPRE; si una acción "
                          "las contradice, avísalo y NO la ejecutes sin autorización "
                          "explícita):\n" + rt)
    except Exception:
        pass
    try:
        mt = memoria_texto()
        if mt:
            partes.append("DECISIONES / PREFERENCIAS del Jefe (tenlas en cuenta):\n" + mt)
    except Exception:
        pass
    try:
        metas = progreso_objetivos()
        if metas:
            lineas = []
            for m in metas:
                per = f"{m['anio']}" + (f"-{m['mes']:02d}" if m.get('mes') else '')
                proy = ''
                if m.get('proyecta_ok') is False:
                    proy = ' — al ritmo actual NO alcanza, sugiere acciones'
                lineas.append(f"- {m.get('descripcion') or m['tipo']} ({per}): "
                              f"${int(m['actual']):,} de ${int(m['meta']):,} "
                              f"({m['pct']}%)".replace(',', '.') + proy)
            partes.append("OBJETIVOS (progreso en vivo):\n" + '\n'.join(lineas))
    except Exception:
        pass
    if not partes:
        return ''
    return "=== POLÍTICA Y METAS DEL NEGOCIO ===\n" + '\n\n'.join(partes) + "\n\n"


def _tool_home():
    """Daily Briefing: alertas + metas + cartera + recomendaciones del día."""
    from app.services.business_memory import resumen_home
    try:
        r = resumen_home()
    except Exception as e:
        logger.warning("asistente: _tool_home falló: %s", e)
        return {'encontrado': False, 'error': 'no pude armar el resumen'}
    r['encontrado'] = True
    return r


def _tool_observar():
    """Corre el Observador y devuelve las alertas priorizadas del negocio."""
    from app.services.event_engine import observar
    try:
        r = observar(persistir=True)
    except Exception as e:
        logger.warning("asistente: _tool_observar falló: %s", e)
        return {'encontrado': False, 'error': 'no pude revisar el negocio'}
    r['encontrado'] = True
    return r


def _tool_bitacora(limite):
    """Últimas acciones ejecutadas por el Asistente (para 'qué cambios hiciste',
    'deshaz lo último'). Devuelve id, qué se hizo, si se verificó y si es reversible."""
    try:
        n = min(max(int(limite), 1), 30)
    except Exception:
        n = 10
    filas = (AccionAsistente.query
             .order_by(AccionAsistente.creado_en.desc())
             .limit(n).all())
    return {
        'encontrado': bool(filas),
        'acciones': [{
            'id_accion': a.id_accion, 'tipo': a.tipo, 'descripcion': a.descripcion,
            'verificado': a.verificado, 'reversible': a.reversible,
            'resultado': a.resultado, 'usuario': a.usuario,
            'fecha': a.creado_en.isoformat() if a.creado_en else None,
        } for a in filas],
    }


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
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1500},
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
    return None, ultimo_detalle


def _llamar_grok(prompt_text):
    """Grok (xAI), API compatible con OpenAI. Prueba varios ids de modelo por si
    el configurado no existe (así no depende del nombre exacto)."""
    if not GROK_API_KEY:
        return None, 'sin_grok'
    candidatos = [GROK_MODEL] if GROK_MODEL else []
    for m in ('grok-4', 'grok-3', 'grok-2-latest', 'grok-beta'):
        if m not in candidatos:
            candidatos.append(m)
    ultimo = ''
    for modelo in candidatos:
        for intento in range(2):   # 1 reintento ante saturación (429/503)
            try:
                r = requests.post(
                    'https://api.x.ai/v1/chat/completions',
                    headers={'Authorization': f'Bearer {GROK_API_KEY}',
                             'Content-Type': 'application/json'},
                    json={'model': modelo,
                          'messages': [{'role': 'user', 'content': prompt_text}],
                          'temperature': 0.2, 'max_tokens': 2000, 'stream': False},
                    timeout=45,
                )
            except Exception as e:
                ultimo = f'grok conexión: {e}'
                break   # error de red → probar el siguiente modelo
            if r.status_code == 200:
                try:
                    return (r.json()['choices'][0]['message']['content'] or '').strip(), None
                except Exception:
                    return '', 'grok_vacio'
            ultimo = f'grok {r.status_code}: {r.text[:150]}'
            logger.warning('asistente: Grok %s -> %s: %s', modelo, r.status_code, r.text[:150])
            if r.status_code in (401, 403):
                return None, ultimo   # llave inválida → no seguir probando
            if r.status_code in (429, 503) and intento == 0:
                time.sleep(2)
                continue              # saturado → reintenta el mismo modelo
            break                     # 400/404/422… → probar el siguiente modelo
    return None, ultimo


def _llamar_ia(prompt_text):
    """Orquesta los motores: Grok (principal si hay llave) → Gemini → DeepSeek.
    El cambio de motor es invisible para el Jefe."""
    detalle = 'sin_modelo'
    if GROK_API_KEY:
        g, gd = _llamar_grok(prompt_text)
        if g is not None:
            return g, None
        detalle = gd or detalle
    if GEMINI_API_KEY:
        t, d = _llamar_gemini(prompt_text)
        if t is not None:
            return t, None
        detalle = d or detalle
    if DEEPSEEK_API_KEY:
        ds, dsd = _llamar_deepseek(prompt_text)
        if ds is not None:
            return ds, None
        detalle = dsd or detalle
    # Sin respaldo configurado: devolvemos el error REAL del motor principal
    # (no lo enmascaramos con 'sin_deepseek').
    return None, detalle


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
                  'temperature': 0.2, 'max_tokens': 1500, 'stream': False},
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
    """Devuelve la respuesta de error adecuada (saturación vs. problema real).
    El detalle técnico se REGISTRA en logs, nunca se envía al usuario."""
    logger.warning('asistente: fallo de IA -> %s', detalle)
    # El detalle técnico solo se expone si ASISTENTE_DEBUG=1 (para diagnosticar);
    # por defecto va a los logs y al usuario solo un mensaje limpio.
    extra = {'detalle': detalle} if os.getenv('ASISTENTE_DEBUG', '').strip() == '1' else {}
    d = (detalle or '').upper()
    if 'UNAVAILABLE' in d or (detalle or '').startswith('503') or '429' in d:
        return jsonify({
            'error': '⏳ El asistente está saturado ahora mismo. Espera unos segundos '
                     'y vuelve a intentar.',
            'code': 'ocupado', **extra,
        }), 503
    return jsonify({
        'error': 'El asistente no respondió en este momento. Inténtalo de nuevo en '
                 'unos segundos; si sigue, avísale al administrador.',
        'code': 'ia_error', **extra,
    }), 502


@asistente_bp.route('/preguntar', methods=['POST'])
@jwt_required()
@rol_requerido('administrador', 'vendedor', 'cajero')
@limiter.limit("20 per minute")
def preguntar():
    """Recibe {pregunta} y responde con datos reales vía IA (solo lectura)."""
    if not _hay_ia():
        return jsonify({
            'error': 'El asistente aún no está configurado. Falta una llave de IA '
                     '(GROK_API_KEY, GEMINI_API_KEY o DEEPSEEK_API_KEY) en el servidor.',
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
        "AGENTE (no solo respondes, resuelves procesos): ante una decisión de negocio, sigue "
        "ENTENDER → INVESTIGAR (consulta los datos tú mismo con las herramientas) → ANALIZAR → "
        "SIMULAR (si es futuro o hipotético) → RECOMENDAR → CONFIRMAR → EJECUTAR → VERIFICAR. "
        "Distingue: MENCIONAR ('quiero subir precios') NO es una orden; PREGUNTAR '¿qué pasa "
        "si…?' pide una SIMULACIÓN (no un cambio); una ORDEN clara ('sube 5%') se PREPARA y se "
        "confirma antes de ejecutar; solo ejecutas tras un 'sí' explícito.\n"
        "\n"
        "PLANIFICA Y ENCADENA: una sola pregunta puede necesitar varios datos. Pársala en un "
        "plan mental y pide cada dato con su propia BÚSQUEDA, uno por turno, hasta tenerlo "
        "todo. NO te detengas en el primer resultado si el objetivo pide más (ej. 'qué me deja "
        "lo más vendido' = top_productos → luego el precio y costo de esa prenda → utilidad; "
        "'¿me conviene subir Manyanet?' = precios+costos → simular → comparar). Responde solo "
        "cuando el plan esté completo o cuando falte un dato real (ahí di EXACTAMENTE cuál "
        "falta y qué sí puedes dar). Muestra el resultado, no el paso a paso.\n"
        "\n"
        "OBJETIVOS ABIERTOS: ante metas amplias ('quiero vender más', 'cómo mejoro') NO "
        "preguntes '¿qué hago?': investiga tú (más vendidas, rotación, stock, márgenes) y "
        "vuelve con 2-3 oportunidades concretas.\n"
        "\n"
        "CAPACIDADES UNIVERSALES: resuelve preguntas nuevas combinando los DATOS reales con "
        "matemáticas, porcentajes, fechas/calendario, rangos, proyecciones, comparaciones y "
        "escenarios — NO asumas que falta una herramienta específica. Para contar días de la "
        "semana en un rango usa la BÚSQUEDA 'calendario' (NUNCA cuentes fechas a mano). Ej: "
        "pago de un ayudante por lunes y sábados = contar esos días × tarifa.\n"
        "\n"
        "CERO ≠ SIN DATOS: si un indicador viene en 0 o vacío (ej. gastos_mes=0) NO asumas "
        "que el valor real es 0 — puede que no esté registrado. Investiga otras fuentes "
        "(compras, costos, inventario, cartera) antes de pedirle el dato al Jefe; pídelo solo "
        "si el sistema de verdad no lo tiene, y dilo con claridad ('no llevo un registro de "
        "gastos operativos; sí puedo analizar compras/costos/inventario').\n"
        "\n"
        "DECISIONES EMPRESARIALES (ej. '¿me conviene contratar?'): no respondas solo con el "
        "costo. Separa DATO (el cálculo) · CONTEXTO (ventas, margen, flujo, cartera, carga "
        "operativa) · ANÁLISIS · ESCENARIOS (no hacerlo / parcial / todo) · RECOMENDACIÓN. "
        "Para comparar un costo contra ventas usa MARGEN/utilidad o flujo, NO la facturación "
        "bruta. Si puedes consultar las ventas de esos días, hazlo tú (BÚSQUEDA "
        "'ventas_por_dia'); no lo preguntes. Ej. contratar para lunes+sábado: calendario × "
        "tarifa = costo; ventas_por_dia de esos días = lo que está en juego → compara.\n"
        "\n"
        "OBSERVADOR CON MESURA: las alertas del Observador NO van en toda respuesta. Úsalas "
        "SOLO si el Jefe pide una revisión general, o si una alerta afecta DIRECTAMENTE lo que "
        "preguntó. Si aportas contexto relevante, resúmelo en 1 línea (ej. 'además tienes "
        "$965.000 en cartera'); nunca pegues la lista de inventario en una respuesta que no es "
        "de revisión.\n"
        "\n"
        "SIMULACIONES: ante '¿qué pasa si…?', '¿me conviene…?', '¿y si subo/bajo…?' NO ejecutes; "
        "muestra ACTUAL vs PROPUESTO vs DIFERENCIA (precio, costo, margen, utilidad). Nunca "
        "asumas que subir el precio mantiene las ventas: preséntalos como ESCENARIOS (la demanda "
        "puede cambiar), no predicciones. Usa solo cifras reales; si falta un dato, dilo.\n"
        "\n"
        "MÍNIMA FRICCIÓN: no preguntes lo que puedes consultar en el sistema — investiga tú. "
        "Pregunta SOLO cuando haga falta una decisión humana que cambie la acción (ej. "
        "'¿lo aplico a todas las referencias o solo a Manyanet?'). Antes de proponer descontar "
        "el inventario de una factura, revisa si ya tiene movimientos en el kardex para NO "
        "duplicar la salida.\n"
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
            "Si el usuario pide DESHACER/REVERTIR un cambio ('deshaz lo último', 'devuelve el "
            "stock/costo/precio de antes'), primero mira la bitácora (BUSCAR bitacora) para "
            "hallar el id_accion correcto, propón la reversión y en la ÚLTIMA línea agrega:\n"
            "ACCION_JSON: {\"tipo\":\"revertir\",\"id_accion\":<id de la bitácora>}\n"
            "Solo se puede revertir una acción reversible que no haya sido revertida.\n"
            "Si el usuario fija una REGLA/POLÍTICA del negocio ('no comprar más de "
            "$10M al mes', 'no vender por debajo de $45.000', 'no publicar después de "
            "las 8pm'), NO la trates como charla: propón guardarla y en la ÚLTIMA línea "
            "agrega (categoria = PRECIO|INVENTARIO|COMPRAS|PROVEEDORES|HORARIOS|PAGOS|"
            "PROMOCIONES|WHATSAPP|PUBLICIDAD|AUTONOMIA; incluye parametros si hay un "
            "número, ej. presupuesto de compras):\n"
            "ACCION_JSON: {\"tipo\":\"crear_regla\",\"categoria\":\"COMPRAS\",\"texto\":\"No comprar más de $10.000.000 al mes sin aprobación\",\"parametros\":{\"limite\":10000000,\"periodo\":\"mensual\"}}\n"
            "Si el usuario fija una META de ventas ('quiero vender $30M en septiembre'), "
            "propón guardarla y agrega:\n"
            "ACCION_JSON: {\"tipo\":\"crear_objetivo\",\"descripcion\":\"Ventas septiembre\",\"meta\":30000000,\"anio\":2026,\"mes\":9}\n"
            "Si el usuario expresa una DECISIÓN/PREFERENCIA ('prefiero el proveedor X'), "
            "propón recordarla y agrega:\n"
            "ACCION_JSON: {\"tipo\":\"crear_memoria\",\"tipo_memoria\":\"PREFERENCIA\",\"texto\":\"Prefiere el proveedor X\"}\n"
            "Si el usuario pide ESTIMAR/rellenar costos mientras consigue los reales "
            "('pon costos al 60%', 'estima los costos'), propónlo y agrega (factor = fracción "
            "del precio; 0.6 = margen ~40%):\n"
            "ACCION_JSON: {\"tipo\":\"estimar_costos\",\"factor\":0.6}\n"
            "Si el usuario NO pide una acción, responde normal y NO agregues ACCION_JSON.\n"
            "AUTO-CHEQUEO antes de proponer cualquier acción: ¿entendí el objetivo?, "
            "¿usé datos reales (no inventados)?, ¿hay una regla que lo prohíba?, ¿el "
            "alcance es correcto?, ¿no lo estoy duplicando?, ¿sé cómo verificarlo? Si algo "
            "no cuadra, primero aclara o consulta; no propongas a ciegas."
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
        "BUSCAR: {\"tipo\":\"simular_precio\",\"colegio\":\"<colegio o vacío>\",\"prenda\":\"<prenda o vacío>\",\"porcentaje\":<número, ej 5 o -10>}  → SIMULA (no cambia nada) el margen actual vs con ese % de cambio de precio. Úsalo para '¿qué pasa si subo/bajo los precios?'. Preséntalo como escenario, NO ejecutes\n"
        "BUSCAR: {\"tipo\":\"bitacora\",\"limite\":<n>}  → últimas acciones que ejecutaste (id, qué se hizo, si se verificó, si es reversible). Úsalo para '¿qué cambios hiciste?' o cuando el Jefe pida DESHACER algo: primero mira la bitácora para encontrar el id_accion a revertir\n"
        "BUSCAR: {\"tipo\":\"home\"}  → el Daily Briefing ('Buenos días, Jefe'): alertas priorizadas + progreso de metas + cartera pendiente + las 3 acciones que recomiendas hoy. Úsalo para 'resumen del día', 'buenos días', 'cómo vamos'\n"
        "BUSCAR: {\"tipo\":\"calendario\",\"desde\":\"YYYY-MM-DD\",\"hasta\":\"YYYY-MM-DD\",\"dias\":[\"lunes\",\"sabado\"]}  → cuenta cuántos días de la semana caen en un rango (sin desde/hasta = mes actual). Úsalo SIEMPRE para cálculos de calendario/turnos/pagos por día (ej. cuántos lunes y sábados hay); NO cuentes fechas a mano. Luego multiplica el total por la tarifa\n"
        "BUSCAR: {\"tipo\":\"ventas_por_dia\",\"dias\":[\"lunes\",\"sabado\"]}  → cuánto se factura en promedio por día de la semana (por defecto últimos 90 días). Úsalo para decidir '¿me conviene abrir/contratar para esos días?': compara el pago del ayudante contra lo que se factura esos días\n"
        "BUSCAR: {\"tipo\":\"observar\"}  → SOLO para una revisión general ('¿cómo está el negocio?', 'revisa todo'). NO lo uses en preguntas puntuales ni para adornar respuestas. El Observador revisa el negocio y devuelve alertas ANALIZADAS y priorizadas por 'score' (0-100), agrupadas por prenda, con el POR QUÉ (campo datos.analisis), la RECOMENDACIÓN y a veces una acción sugerida (datos.accion_sugerida). Úsalo para '¿cómo está el negocio?', '¿hay algo importante?', 'revisa todo'. Preséntalo priorizado (🔴🟠🟡), con el porqué y qué recomiendas; si hay una acción sugerida, OFRÉCELA ('¿quieres que prepare …?') pero NO la ejecutes: solo si el Jefe dice que sí, propón el ACCION_JSON correspondiente. Si no hay nada, dilo en una línea\n"
        "Una sola BÚSQUEDA por turno, pero puedes encadenar varias (una tras otra) hasta "
        "completar el objetivo. Si la respuesta ya está en el resumen, NO uses BUSCAR."
    )

    politica = _bloque_politica()
    base = (
        f"{sistema}{busqueda}{acciones}\n\n=== DATOS REALES DEL SISTEMA (hoy {datos.get('fecha_hoy')}) ===\n"
        f"{json.dumps(datos, ensure_ascii=False, default=str)}\n\n"
        f"{politica}"
        f"=== MANUAL DEL SISTEMA ===\n{MANUAL}\n\n"
        f"=== PREGUNTA DEL USUARIO ===\n{pregunta}"
    )

    texto, detalle = _llamar_ia(base)
    if texto is None:
        return _error_gemini(detalle)

    # Bucle de búsqueda: si la IA pide un dato con BUSCAR, lo consultamos y se lo damos.
    ultima_busqueda = None   # para devolver datos estructurados a la UI (tarjetas)
    for _ in range(5):       # varias rondas → el agente encadena un plan multi-paso
        consulta = _extraer_json_marcador(texto, 'BUSCAR')
        if not consulta:
            break
        try:
            resultado = _sin_pii(_ejecutar_busqueda(consulta))
        except Exception as e:
            logger.warning("asistente: búsqueda falló: %s", e)
            resultado = {'error': 'la búsqueda falló'}
        ultima_busqueda = {'tipo': consulta.get('tipo'), 'resultado': resultado}
        seguimiento = (
            f"{base}\n\n=== RESULTADO DE LA BÚSQUEDA ({consulta.get('tipo')}) ===\n"
            f"{json.dumps(resultado, ensure_ascii=False, default=str)}\n\n"
            "Con ese resultado sigue tu plan. Si AÚN te falta un dato para cumplir el objetivo "
            "del usuario, pide otra BÚSQUEDA (una línea, nada más). Si ya tienes todo lo "
            "necesario, responde en español, claro y breve, y NO vuelvas a buscar. No inventes; "
            "si algo no se encontró, dilo y explica qué sí puedes dar."
        )
        texto, detalle = _llamar_ia(seguimiento)
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


# ─────────────────────────────────────────────────────────────────────────
#  Bitácora de acciones · Verificación robusta · Rollback
# ─────────────────────────────────────────────────────────────────────────
def _verificar_accion(tipo, despues):
    """Verificación contra la fuente de verdad. Delega en la capa Safety
    (Governor), dueña de la verificación."""
    from app.services.governor import verificar
    return verificar(tipo, despues)


def _registrar_accion(tipo, descripcion, antes, despues, reversible,
                      verificado, usuario, reversion_de=None, resultado=None):
    """Anota una acción en la bitácora. Best-effort: si falla, no rompe la
    acción (que ya se ejecutó), pero se pierde la posibilidad de rollback."""
    try:
        acc = AccionAsistente(
            tipo=tipo,
            descripcion=(descripcion or '')[:400] or None,
            reversible=bool(reversible),
            verificado=bool(verificado),
            resultado=resultado or ('VERIFICADA' if verificado else 'FALLO_VERIFICACION'),
            reversion_de=reversion_de,
            usuario=usuario,
        )
        acc.set_antes(antes)
        acc.set_despues(despues)
        db.session.add(acc)
        db.session.commit()
        return acc
    except Exception as e:
        db.session.rollback()
        logger.warning("asistente: no se pudo registrar en bitácora: %s", e)
        return None


def _revertir_accion(acc, usuario):
    """Aplica la INVERSA de una acción usando su estado_antes, y verifica el
    resultado contra la BD. Devuelve (ok, mensaje, verificado)."""
    antes = acc.antes or {}
    tipo = acc.tipo
    if tipo == 'ajustar_stock':
        cid, pid = antes.get('id_colegio'), antes.get('id_producto')
        talla = antes.get('talla')
        objetivo = antes.get('cantidad')
        if cid is None or pid is None or talla is None or objetivo is None:
            return False, 'No tengo el estado anterior para revertir.', False
        st, _m = registrar_movimiento(cid, pid, talla, 'AJUSTE', objetivo,
                                      usuario=usuario, motivo='[Asistente] reversión')
        db.session.commit()
        return True, f'Stock restaurado a {objetivo} unidades.', st.cantidad == objetivo

    if tipo == 'fijar_costo':
        filas = antes.get('filas') or []
        if not filas:
            return False, 'No tengo los costos anteriores para revertir.', False
        for f in filas:
            r = PrecioColegio.query.get(f.get('id_precio'))
            if r is not None:
                r.costo_unitario = f.get('costo')
        db.session.commit()
        ok = True
        for f in filas:
            r = PrecioColegio.query.get(f.get('id_precio'))
            if r is None or r.costo_unitario != f.get('costo'):
                ok = False
                break
        return True, 'Costos anteriores restaurados.', ok

    if tipo == 'cambiar_estado_pedido':
        f = Factura.query.get(antes.get('id_factura'))
        if not f:
            return False, 'Ya no existe esa factura.', False
        f.estado_entrega = antes.get('estado_entrega')
        db.session.commit()
        return True, f'Estado de entrega revertido a "{antes.get("estado_entrega")}".', \
            f.estado_entrega == antes.get('estado_entrega')

    if tipo == 'crear_tarea':
        d = acc.despues or {}
        t = Tarea.query.get(d.get('id_tarea'))
        if t is not None:
            db.session.delete(t)
            db.session.commit()
        return True, 'Recordatorio eliminado.', Tarea.query.get(d.get('id_tarea')) is None

    return False, 'Esta acción no se puede revertir.', False


@asistente_bp.route('/bitacora', methods=['GET'])
@jwt_required()
@rol_requerido('administrador')
def bitacora():
    """Últimas acciones ejecutadas por el Asistente (Action Journal)."""
    try:
        limite = min(max(int(request.args.get('limite', 20)), 1), 100)
    except Exception:
        limite = 20
    filas = (AccionAsistente.query
             .order_by(AccionAsistente.creado_en.desc())
             .limit(limite).all())
    return jsonify({'acciones': [a.to_dict() for a in filas]}), 200


@asistente_bp.route('/observar', methods=['GET'])
@jwt_required()
@rol_requerido('administrador')
def observar_endpoint():
    """El Observador: escanea el negocio y devuelve las alertas priorizadas
    ('Buenos días, Jefe: detecté N cosas'). Registra los eventos nuevos."""
    from app.services.event_engine import observar
    try:
        return jsonify(observar(persistir=True)), 200
    except Exception as e:
        logger.warning("asistente: observar falló: %s", e)
        return jsonify({'error': 'No pude revisar el negocio en este momento.'}), 500


@asistente_bp.route('/eventos', methods=['GET'])
@jwt_required()
@rol_requerido('administrador')
def eventos_endpoint():
    """Lista eventos del negocio. ?estado=NUEVO|VISTO|RESUELTO (por defecto abiertos)."""
    estado = (request.args.get('estado') or '').upper().strip()
    try:
        limite = min(max(int(request.args.get('limite', 50)), 1), 200)
    except Exception:
        limite = 50
    q = Evento.query
    if estado in ('NUEVO', 'VISTO', 'RESUELTO'):
        q = q.filter(Evento.estado == estado)
    else:
        q = q.filter(Evento.estado.in_(('NUEVO', 'VISTO')))
    filas = q.order_by(Evento.creado_en.desc()).limit(limite).all()
    return jsonify({'eventos': [e.to_dict() for e in filas]}), 200


@asistente_bp.route('/eventos/<int:id_evento>/estado', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def evento_estado(id_evento):
    """Marca un evento como VISTO o RESUELTO."""
    from datetime import datetime as _dt
    nuevo = (request.get_json(silent=True) or {}).get('estado', 'VISTO')
    nuevo = str(nuevo).upper().strip()
    if nuevo not in ('VISTO', 'RESUELTO', 'NUEVO'):
        return jsonify({'error': 'Estado inválido.'}), 400
    ev = Evento.query.get(id_evento)
    if not ev:
        return jsonify({'error': 'No encontré ese evento.'}), 404
    ev.estado = nuevo
    ev.visto_en = _dt.utcnow() if nuevo != 'NUEVO' else None
    db.session.commit()
    return jsonify({'ok': True, 'evento': ev.to_dict()}), 200


def _aplicar_costos_estimados(factor, solo_faltantes=True):
    """Rellena costo_unitario = precio × factor (costos ESTIMADOS, no reales).
    Por defecto solo toca las que NO tienen costo (no pisa costos reales ya
    cargados). Guarda el flag para que el asistente siempre lo aclare."""
    from app.models import ConfigSitio
    try:
        factor = float(factor)
    except Exception:
        factor = 0.6
    factor = min(max(factor, 0.05), 1.0)
    q = PrecioColegio.query
    if solo_faltantes:
        q = q.filter(PrecioColegio.costo_unitario.is_(None))
    n = 0
    for r in q.all():
        if r.precio_unitario:
            r.costo_unitario = round(r.precio_unitario * factor)
            n += 1
    ConfigSitio.set('costos_estimados', '1')
    ConfigSitio.set('costos_factor', str(factor))
    db.session.commit()
    return n, factor


@asistente_bp.route('/estimar-costos', methods=['POST'])
@jwt_required()
@rol_requerido('administrador')
def estimar_costos_endpoint():
    """Rellena costos estimados (precio × factor) mientras se consiguen los
    reales. body: {factor: 0.6, solo_faltantes: true}."""
    d = request.get_json(silent=True) or {}
    solo = d.get('solo_faltantes', True)
    n, factor = _aplicar_costos_estimados(d.get('factor', 0.6), bool(solo))
    return jsonify({'ok': True, 'actualizadas': n, 'factor': factor,
                    'margen_estimado_pct': round((1 - factor) * 100)}), 200


@asistente_bp.route('/home', methods=['GET'])
@jwt_required()
@rol_requerido('administrador')
def home_endpoint():
    """Daily Briefing: alertas + metas + cartera + recomendaciones del día."""
    from app.services.business_memory import resumen_home
    try:
        return jsonify(resumen_home()), 200
    except Exception as e:
        logger.warning("asistente: home falló: %s", e)
        return jsonify({'error': 'No pude armar el resumen del día.'}), 500


@asistente_bp.route('/reglas', methods=['GET', 'POST'])
@jwt_required()
@rol_requerido('administrador')
def reglas_endpoint():
    from app.models import ReglaNegocio
    if request.method == 'GET':
        rs = ReglaNegocio.query.filter_by(activa=True).order_by(ReglaNegocio.categoria).all()
        return jsonify({'reglas': [r.to_dict() for r in rs]}), 200
    d = request.get_json(silent=True) or {}
    texto = str(d.get('texto', '')).strip()[:400]
    if not texto:
        return jsonify({'error': 'Falta el texto de la regla.'}), 400
    r = ReglaNegocio(categoria=str(d.get('categoria', 'OTRA')).upper()[:20] or 'OTRA',
                     texto=texto, creado_por=(get_current_identity() or {}).get('usuario'))
    if isinstance(d.get('parametros'), dict):
        r.set_parametros(d['parametros'])
    db.session.add(r)
    db.session.commit()
    return jsonify({'ok': True, 'regla': r.to_dict()}), 200


@asistente_bp.route('/reglas/<int:id_regla>', methods=['DELETE'])
@jwt_required()
@rol_requerido('administrador')
def borrar_regla(id_regla):
    from app.models import ReglaNegocio
    r = ReglaNegocio.query.get(id_regla)
    if not r:
        return jsonify({'error': 'No existe esa regla.'}), 404
    r.activa = False
    db.session.commit()
    return jsonify({'ok': True}), 200


@asistente_bp.route('/objetivos', methods=['GET', 'POST'])
@jwt_required()
@rol_requerido('administrador')
def objetivos_endpoint():
    from app.services.business_memory import progreso_objetivos
    from app.models import Objetivo
    if request.method == 'GET':
        return jsonify({'objetivos': progreso_objetivos()}), 200
    d = request.get_json(silent=True) or {}
    try:
        meta = float(d.get('meta'))
        anio = int(d.get('anio'))
    except Exception:
        return jsonify({'error': 'Meta o año inválidos.'}), 400
    mes = d.get('mes')
    try:
        mes = int(mes) if mes not in (None, '', 0) else None
    except Exception:
        mes = None
    o = Objetivo(tipo='VENTAS', descripcion=str(d.get('descripcion', ''))[:200] or None,
                 meta=meta, anio=anio, mes=mes,
                 creado_por=(get_current_identity() or {}).get('usuario'))
    db.session.add(o)
    db.session.commit()
    return jsonify({'ok': True, 'objetivo': o.to_dict()}), 200


@asistente_bp.route('/objetivos/<int:id_objetivo>', methods=['DELETE'])
@jwt_required()
@rol_requerido('administrador')
def borrar_objetivo(id_objetivo):
    from app.models import Objetivo
    o = Objetivo.query.get(id_objetivo)
    if not o:
        return jsonify({'error': 'No existe ese objetivo.'}), 404
    o.activa = False
    db.session.commit()
    return jsonify({'ok': True}), 200


@asistente_bp.route('/memoria', methods=['GET', 'POST'])
@jwt_required()
@rol_requerido('administrador')
def memoria_endpoint():
    from app.models import MemoriaNegocio
    if request.method == 'GET':
        ms = MemoriaNegocio.query.filter_by(activa=True).order_by(MemoriaNegocio.id_memoria).all()
        return jsonify({'memoria': [m.to_dict() for m in ms]}), 200
    d = request.get_json(silent=True) or {}
    texto = str(d.get('texto', '')).strip()[:500]
    if not texto:
        return jsonify({'error': 'Falta el texto.'}), 400
    m = MemoriaNegocio(tipo=str(d.get('tipo', 'NOTA')).upper()[:20] or 'NOTA', texto=texto,
                       creado_por=(get_current_identity() or {}).get('usuario'))
    db.session.add(m)
    db.session.commit()
    return jsonify({'ok': True, 'memoria': m.to_dict()}), 200


@asistente_bp.route('/modo', methods=['GET', 'POST'])
@jwt_required()
@rol_requerido('administrador')
def modo_observador_endpoint():
    """Ver o cambiar el modo de autonomía del Observador.
    SUGERIR (recomienda) · PREPARAR (deja la acción lista) · AUTONOMO
    (ejecuta solo acciones de bajo riesgo: crear recordatorios)."""
    from app.services.event_engine import modo_observador, set_modo_observador, _MODOS
    if request.method == 'GET':
        return jsonify({'modo': modo_observador(), 'opciones': list(_MODOS)}), 200
    nuevo = (request.get_json(silent=True) or {}).get('modo')
    r = set_modo_observador(nuevo)
    if not r:
        return jsonify({'error': 'Modo inválido. Usa SUGERIR, PREPARAR o AUTONOMO.'}), 400
    return jsonify({'ok': True, 'modo': r}), 200


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

    # ── Self-Check / Governor: checklist ANTES de tocar nada ──
    from app.services import governor
    _sc = governor.pre_check(data)
    if not _sc['ok']:
        return jsonify({'error': ' '.join(_sc['bloqueos']) or 'La acción no pasó el auto-chequeo.',
                        'self_check': _sc['checklist'], 'code': 'self_check'}), 409

    # ── Crear recordatorio / tarea ──
    if tipo == 'crear_tarea':
        titulo = str(data.get('titulo', '')).strip()[:200]
        if not titulo:
            return jsonify({'error': 'Falta el título del recordatorio.'}), 400
        # Idempotencia (¿estoy duplicando algo?): si ya existe un recordatorio
        # abierto con el mismo título, no lo repito.
        dup = Tarea.query.filter(Tarea.titulo == titulo,
                                 Tarea.completada.isnot(True)).first()
        if dup:
            return jsonify({'ok': True, 'duplicado': True,
                            'mensaje': f'Ya tienes ese recordatorio: “{titulo}”. No lo dupliqué.'}), 200
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
        despues = {'id_tarea': t.id_tarea}
        verificado = _verificar_accion('crear_tarea', despues)
        acc = _registrar_accion('crear_tarea', f'Recordatorio: {titulo}', {}, despues,
                                reversible=True, verificado=verificado,
                                usuario=ident.get('usuario'))
        return jsonify({
            'ok': True,
            'mensaje': f'✅ Recordatorio creado: “{titulo}”'
                       + (f' para el {fecha.isoformat()}' if fecha else '')
                       + '. Lo ves en el menú *Tareas*.',
            'verificado': verificado,
            'self_check': _sc['checklist'],
            'id_accion': acc.id_accion if acc else None,
            'reversible': bool(acc),
        }), 200

    # ── Guardar una REGLA del negocio (política persistente) ──
    if tipo == 'crear_regla':
        from app.models import ReglaNegocio
        texto_regla = str(data.get('texto', '')).strip()[:400]
        categoria = str(data.get('categoria', 'OTRA')).upper().strip()[:20] or 'OTRA'
        if not texto_regla:
            return jsonify({'error': 'Falta el texto de la regla.'}), 400
        ident = get_current_identity()
        r = ReglaNegocio(categoria=categoria, texto=texto_regla,
                         creado_por=ident.get('usuario'))
        params = data.get('parametros')
        if isinstance(params, dict):
            r.set_parametros(params)
        db.session.add(r)
        db.session.commit()
        try:
            registrar_auditoria('reglas_negocio', r.id_regla, 'CREADA',
                                f'[Asistente] regla [{categoria}] por {ident.get("usuario")}')
        except Exception:
            pass
        return jsonify({'ok': True,
                        'mensaje': f'✅ Regla guardada [{categoria}]. La tendré en cuenta '
                                   'siempre y te avisaré si algo la contradice.'}), 200

    # ── Guardar un OBJETIVO / meta ──
    if tipo == 'crear_objetivo':
        from app.models import Objetivo
        try:
            meta = float(data.get('meta'))
            anio = int(data.get('anio'))
        except Exception:
            return jsonify({'error': 'Meta o año inválidos.'}), 400
        mes = data.get('mes')
        try:
            mes = int(mes) if mes not in (None, '', 0) else None
        except Exception:
            mes = None
        if meta <= 0:
            return jsonify({'error': 'La meta debe ser mayor a 0.'}), 400
        ident = get_current_identity()
        o = Objetivo(tipo='VENTAS', descripcion=str(data.get('descripcion_obj', ''))[:200] or None,
                     meta=meta, anio=anio, mes=mes, creado_por=ident.get('usuario'))
        db.session.add(o)
        db.session.commit()
        return jsonify({'ok': True,
                        'mensaje': f'✅ Meta guardada: ${int(meta):,}. Iré midiendo el avance '
                                   'y te aviso si al ritmo actual no alcanza.'.replace(',', '.')}), 200

    # ── Rellenar costos estimados (precio × factor) ──
    if tipo == 'estimar_costos':
        try:
            factor = float(data.get('factor', 0.6))
        except Exception:
            factor = 0.6
        n, factor = _aplicar_costos_estimados(factor, bool(data.get('solo_faltantes', True)))
        margen = round((1 - factor) * 100)
        return jsonify({
            'ok': True,
            'mensaje': f'✅ Puse costos ESTIMADOS en {n} referencia(s) (precio × {factor:.0%}, '
                       f'margen ~{margen}%). Son aproximados: cuando tengas los costos reales '
                       f'de producción, cámbialos y el margen será exacto.',
        }), 200

    # ── Guardar una DECISIÓN / preferencia ──
    if tipo == 'crear_memoria':
        from app.models import MemoriaNegocio
        texto_mem = str(data.get('texto', '')).strip()[:500]
        tipo_mem = str(data.get('tipo_memoria', 'NOTA')).upper().strip()[:20] or 'NOTA'
        if not texto_mem:
            return jsonify({'error': 'Falta el texto.'}), 400
        ident = get_current_identity()
        m = MemoriaNegocio(tipo=tipo_mem, texto=texto_mem, creado_por=ident.get('usuario'))
        db.session.add(m)
        db.session.commit()
        return jsonify({'ok': True, 'mensaje': f'✅ Anotado [{tipo_mem}]. Lo tendré en cuenta.'}), 200

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
        st_prev = Stock.query.filter_by(id_colegio=cid, id_producto=pid,
                                        talla_individual=talla).first()
        cantidad_antes = st_prev.cantidad if st_prev else 0
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
        antes = {'id_stock': stock.id_stock, 'id_colegio': cid, 'id_producto': pid,
                 'talla': talla, 'cantidad': cantidad_antes}
        despues = {'id_stock': stock.id_stock, 'cantidad': stock.cantidad}
        # Tiempo real: un cambio de stock puede crear/cerrar riesgos → re-evaluar.
        try:
            from app.services.event_engine import disparar
            disparar(current_app._get_current_object(), motivo='stock')
        except Exception:
            pass
        _post = governor.post_check('ajustar_stock', despues)
        verificado = _post['verificado']
        acc = _registrar_accion(
            'ajustar_stock',
            f'{pnombre} T{talla}: {cantidad_antes} → {stock.cantidad}',
            antes, despues, reversible=True, verificado=verificado,
            usuario=ident.get('usuario'))
        return jsonify({
            'ok': True,
            'mensaje': f'✅ Stock actualizado: {pnombre} talla {talla} → '
                       f'{stock.cantidad} unidades.'
                       + ('' if verificado else ' ⚠️ No pude confirmarlo en la base; revísalo.')
                       + (f' Cerré {_post["eventos_cerrados"]} alerta(s) relacionada(s).'
                          if _post['eventos_cerrados'] else ''),
            'verificado': verificado,
            'self_check': _sc['checklist'],
            'eventos_cerrados': _post['eventos_cerrados'],
            'id_accion': acc.id_accion if acc else None,
            'reversible': bool(acc),
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
        filas_antes = [{'id_precio': r.id_precio, 'costo': r.costo_unitario} for r in rows]
        for r in rows:
            r.costo_unitario = costo
        db.session.commit()
        try:
            registrar_auditoria('precios_colegio', rows[0].id_precio, 'ACTUALIZAR',
                                f'[Asistente] costo de {pnombre} = ${costo} '
                                f'({len(rows)} talla/s) por {ident.get("usuario")}')
        except Exception:
            pass
        despues = {'ids_precio': [r.id_precio for r in rows], 'costo': costo}
        verificado = _verificar_accion('fijar_costo', despues)
        acc = _registrar_accion(
            'fijar_costo', f'Costo de {pnombre} = ${int(costo)} ({len(rows)} talla/s)',
            {'filas': filas_antes}, despues, reversible=True, verificado=verificado,
            usuario=ident.get('usuario'))
        costo_fmt = f'${int(costo):,}'.replace(',', '.')
        return jsonify({
            'ok': True,
            'mensaje': f'✅ Costo de {pnombre} fijado en {costo_fmt} '
                       f'(aplica a {len(rows)} talla/s). Ya puedo calcular su margen.'
                       + ('' if verificado else ' ⚠️ No pude confirmarlo en la base; revísalo.'),
            'verificado': verificado,
            'self_check': _sc['checklist'],
            'id_accion': acc.id_accion if acc else None,
            'reversible': bool(acc),
        }), 200

    # ── Revertir (rollback) una acción anterior de la bitácora ──
    if tipo == 'revertir':
        try:
            id_accion = int(data.get('id_accion'))
        except Exception:
            return jsonify({'error': 'Falta el id de la acción a revertir.'}), 400
        acc = AccionAsistente.query.get(id_accion)
        if not acc:
            return jsonify({'error': 'No encontré esa acción en la bitácora.'}), 404
        if not acc.reversible:
            return jsonify({'error': 'Esa acción no se puede revertir.'}), 400
        if acc.resultado == 'REVERTIDA':
            return jsonify({'error': 'Esa acción ya había sido revertida.'}), 400
        ident = get_current_identity()
        try:
            ok, msg, verificado = _revertir_accion(acc, ident['usuario'])
        except Exception as e:
            db.session.rollback()
            logger.warning("asistente: revertir falló: %s", e)
            return jsonify({'error': 'No pude revertir la acción.'}), 500
        if not ok:
            return jsonify({'error': msg}), 400
        acc.resultado = 'REVERTIDA'
        db.session.commit()
        try:
            registrar_auditoria('acciones_asistente', acc.id_accion, 'REVERTIDA',
                                f'[Asistente] {msg} por {ident.get("usuario")}')
        except Exception:
            pass
        _registrar_accion('revertir', f'Reversión de #{id_accion}: {acc.descripcion}',
                          acc.despues, acc.antes, reversible=False, verificado=verificado,
                          usuario=ident.get('usuario'), reversion_de=id_accion,
                          resultado=('VERIFICADA' if verificado else 'FALLO_VERIFICACION'))
        return jsonify({
            'ok': True,
            'mensaje': '↩️ ' + msg
                       + ('' if verificado else ' ⚠️ No pude confirmarlo en la base; revísalo.'),
            'verificado': verificado,
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
    if anterior == estado:   # no-op: ya está en ese estado (¿duplico?)
        return jsonify({'ok': True, 'duplicado': True,
                        'mensaje': f'La factura {factura.numero_factura} ya estaba en '
                                   f'"{_ESTADOS_ENTREGA[estado]}". No cambié nada.'}), 200
    factura.estado_entrega = estado
    db.session.commit()

    identity = get_current_identity()
    try:
        registrar_auditoria('facturas', factura.id_factura, estado,
                            f'[Asistente] Estado de entrega {anterior} -> {estado} '
                            f'por {identity.get("usuario")}')
    except Exception as e:
        logger.warning("asistente: no se pudo auditar: %s", e)

    despues = {'id_factura': factura.id_factura, 'estado_entrega': estado}
    _post = governor.post_check('cambiar_estado_pedido', despues)
    verificado = _post['verificado']
    acc = _registrar_accion(
        'cambiar_estado_pedido',
        f'Factura {factura.numero_factura}: {anterior} → {estado}',
        {'id_factura': factura.id_factura, 'estado_entrega': anterior}, despues,
        reversible=True, verificado=verificado, usuario=identity.get('usuario'))

    return jsonify({
        'ok': True,
        'mensaje': f'✅ Factura {factura.numero_factura} marcada como '
                   f'"{_ESTADOS_ENTREGA[estado]}".'
                   + ('' if verificado else ' ⚠️ No pude confirmarlo en la base; revísalo.')
                   + (f' Cerré {_post["eventos_cerrados"]} alerta(s) relacionada(s).'
                      if _post['eventos_cerrados'] else ''),
        'verificado': verificado,
        'self_check': _sc['checklist'],
        'eventos_cerrados': _post['eventos_cerrados'],
        'id_accion': acc.id_accion if acc else None,
        'reversible': bool(acc),
    }), 200
