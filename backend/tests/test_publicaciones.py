"""
Fase 1 — Publicaciones y config del sitio.
Verifica que la tienda respete el estado 'activo', exponga 'destacado'/'orden'
y que el endpoint público /config sirva el banner editable desde el panel.
"""
from datetime import datetime, timedelta

from flask_jwt_extended import create_access_token

from app import db
from app.models import (
    Colegio, Producto, PrecioColegio, Stock, ConfigSitio,
    WaConversacion, Aviso, ReglaAuto,
)
from app.services.reglas import productos_stock_bajo


def _auth_admin():
    token = create_access_token(identity='admin', additional_claims={'rol': 'administrador'})
    return {'Authorization': f'Bearer {token}'}


def _producto(nombre, tipo='camisa', activo=True, destacado=False, orden=0):
    p = Producto(nombre=nombre, tipo=tipo, activo=activo,
                 destacado=destacado, orden=orden)
    db.session.add(p)
    db.session.flush()
    return p


def _publicar(colegio, producto, precio=50000, talla='8', stock=5):
    db.session.add(PrecioColegio(
        id_colegio=colegio.id_colegio, id_producto=producto.id_producto,
        talla_grupo=talla, precio_unitario=precio,
    ))
    db.session.add(Stock(
        id_colegio=colegio.id_colegio, id_producto=producto.id_producto,
        talla_individual=talla, cantidad=stock,
    ))


# ── Config del sitio (banner) ──────────────────────────────────────

def test_config_publica_devuelve_banner(tienda_client):
    ConfigSitio.set('banner_texto', 'Temporada 2026 en stock')
    ConfigSitio.set('banner_activo', '1')
    db.session.commit()

    data = tienda_client.get('/api/tienda/config').get_json()
    assert data['banner']['texto'] == 'Temporada 2026 en stock'
    assert data['banner']['activo'] is True


def test_config_banner_desactivado(tienda_client):
    ConfigSitio.set('banner_activo', '0')
    db.session.commit()
    data = tienda_client.get('/api/tienda/config').get_json()
    assert data['banner']['activo'] is False


# ── Publicaciones: activo / destacado / orden ──────────────────────

def test_catalogo_marca_pausados_como_no_disponibles(tienda_client):
    """Los pausados SÍ aparecen en el catálogo, pero con disponible=False
    (la tienda los muestra atenuados y sin compra)."""
    colegio = Colegio(nombre='COL FASE1', ciudad='Bogotá')
    db.session.add(colegio)
    db.session.flush()

    activo   = _producto('Camisa Activa',  activo=True,  destacado=True, orden=1)
    pausado  = _producto('Camisa Pausada', activo=False)
    _publicar(colegio, activo)
    _publicar(colegio, pausado)
    db.session.commit()

    data = tienda_client.get(f'/api/tienda/catalogo/{colegio.id_colegio}').get_json()
    por_nombre = {p['nombre']: p for p in data['productos']}

    assert 'Camisa Activa' in por_nombre        # ambos aparecen
    assert 'Camisa Pausada' in por_nombre
    assert por_nombre['Camisa Activa']['disponible'] is True
    assert por_nombre['Camisa Pausada']['disponible'] is False
    assert por_nombre['Camisa Activa']['destacado'] is True


def test_colegios_marca_inactivo_como_no_disponible(tienda_client):
    """Un colegio desactivado sigue en la lista pero con disponible=False."""
    activo = Colegio(nombre='COL ACT', ciudad='Bogotá', activo=True)
    inactivo = Colegio(nombre='COL INACT', ciudad='Bogotá', activo=False)
    db.session.add_all([activo, inactivo])
    db.session.flush()
    for c in (activo, inactivo):
        _publicar(c, _producto(f'Prenda {c.nombre}'))
    db.session.commit()

    data = tienda_client.get('/api/tienda/colegios').get_json()
    por_nombre = {c['nombre']: c for c in data['colegios']}
    assert por_nombre['COL ACT']['disponible'] is True
    assert por_nombre['COL INACT']['disponible'] is False


def _reservar(client, colegio, prod, talla='8'):
    return client.post('/api/tienda/reservar', json={
        'session_id': 'sess-test', 'id_colegio': colegio.id_colegio,
        'id_producto': prod.id_producto, 'talla': talla, 'cantidad': 1,
    })


def test_reservar_rechaza_producto_pausado(tienda_client):
    """Pausar = nada de compras: un producto pausado no se puede reservar."""
    colegio = Colegio(nombre='COL RES', ciudad='Bogotá')
    db.session.add(colegio)
    db.session.flush()
    prod = _producto('Pausado', activo=False)
    db.session.add(Stock(id_colegio=colegio.id_colegio, id_producto=prod.id_producto,
                         talla_individual='8', cantidad=5))
    db.session.commit()

    r = _reservar(tienda_client, colegio, prod)
    assert r.status_code == 409


def test_reservar_rechaza_colegio_pausado(tienda_client):
    """Colegio desactivado → toda su tienda bloqueada para comprar."""
    colegio = Colegio(nombre='COL OFF', ciudad='Bogotá', activo=False)
    db.session.add(colegio)
    db.session.flush()
    prod = _producto('Activo', activo=True)
    db.session.add(Stock(id_colegio=colegio.id_colegio, id_producto=prod.id_producto,
                         talla_individual='8', cantidad=5))
    db.session.commit()

    r = _reservar(tienda_client, colegio, prod)
    assert r.status_code == 409


def test_reservar_ok_todo_activo(tienda_client):
    """Con producto y colegio activos + stock, la reserva funciona normal."""
    colegio = Colegio(nombre='COL ON', ciudad='Bogotá', activo=True)
    db.session.add(colegio)
    db.session.flush()
    prod = _producto('Disponible', activo=True)
    db.session.add(Stock(id_colegio=colegio.id_colegio, id_producto=prod.id_producto,
                         talla_individual='8', cantidad=5))
    db.session.commit()

    r = _reservar(tienda_client, colegio, prod)
    assert r.status_code in (200, 201)      # 201 reserva nueva, 200 si ya existía
    assert r.get_json().get('ok') is True


def test_programacion_oculta_producto_futuro(tienda_client):
    """Un producto programado para el futuro no aparece en el catálogo todavía."""
    colegio = Colegio(nombre='COL PROG', ciudad='Bogotá')
    db.session.add(colegio)
    db.session.flush()
    prod = _producto('Promo Futura', activo=True)
    prod.publicar_desde = datetime.utcnow() + timedelta(days=5)   # aún no
    _publicar(colegio, prod)
    db.session.commit()

    data = tienda_client.get(f'/api/tienda/catalogo/{colegio.id_colegio}').get_json()
    nombres = [p['nombre'] for p in data['productos']]
    assert 'Promo Futura' not in nombres     # oculto hasta su fecha


def test_programacion_muestra_producto_en_ventana(tienda_client):
    """Dentro de la ventana (desde ayer, hasta mañana) el producto aparece disponible."""
    colegio = Colegio(nombre='COL PROG2', ciudad='Bogotá')
    db.session.add(colegio)
    db.session.flush()
    prod = _producto('En Ventana', activo=True)
    prod.publicar_desde = datetime.utcnow() - timedelta(days=1)
    prod.publicar_hasta = datetime.utcnow() + timedelta(days=1)
    _publicar(colegio, prod)
    db.session.commit()

    data = tienda_client.get(f'/api/tienda/catalogo/{colegio.id_colegio}').get_json()
    por_nombre = {p['nombre']: p for p in data['productos']}
    assert 'En Ventana' in por_nombre
    assert por_nombre['En Ventana']['disponible'] is True


def test_programacion_vencida_bloquea_compra(tienda_client):
    """Una ventana ya vencida bloquea la reserva (409)."""
    colegio = Colegio(nombre='COL PROG3', ciudad='Bogotá')
    db.session.add(colegio)
    db.session.flush()
    prod = _producto('Vencida', activo=True)
    prod.publicar_hasta = datetime.utcnow() - timedelta(days=1)   # ya terminó
    db.session.add(Stock(id_colegio=colegio.id_colegio, id_producto=prod.id_producto,
                         talla_individual='8', cantidad=5))
    db.session.commit()

    r = _reservar(tienda_client, colegio, prod)
    assert r.status_code == 409


def test_catalogo_ordena_por_campo_orden(tienda_client):
    colegio = Colegio(nombre='COL ORDEN', ciudad='Bogotá')
    db.session.add(colegio)
    db.session.flush()

    _publicar(colegio, _producto('Zeta', orden=1))
    _publicar(colegio, _producto('Alfa', orden=2))
    db.session.commit()

    data = tienda_client.get(f'/api/tienda/catalogo/{colegio.id_colegio}').get_json()
    nombres = [p['nombre'] for p in data['productos']]
    # 'Zeta' (orden 1) va antes que 'Alfa' (orden 2) aunque alfabéticamente sea al revés
    assert nombres == ['Zeta', 'Alfa']


# ── Avisos / campañas por WhatsApp ──────────────────────────────────

def test_avisos_cuenta_destinatarios(tienda_client):
    ahora = datetime.utcnow()
    db.session.add(WaConversacion(chat_id='573001', ultima_fecha=ahora))              # activo (24h)
    db.session.add(WaConversacion(chat_id='573002', ultima_fecha=ahora - timedelta(hours=48)))  # viejo
    db.session.commit()

    r = tienda_client.get('/api/tienda/admin/avisos', headers=_auth_admin())
    assert r.status_code == 200
    d = r.get_json()
    assert d['destinatarios']['todos'] == 2
    assert d['destinatarios']['activos'] == 1


def test_enviar_aviso_registra_historial(tienda_client):
    db.session.add(WaConversacion(chat_id='573009', ultima_fecha=datetime.utcnow()))
    db.session.commit()

    r = tienda_client.post(
        '/api/tienda/admin/avisos',
        json={'texto': 'Hola, llegó la nueva colección', 'segmento': 'activos'},
        headers=_auth_admin(),
    )
    assert r.status_code == 200
    d = r.get_json()
    assert d['total'] == 1
    # Sin WHATSAPP_TOKEN el envío "falla" pero el aviso queda registrado en el historial
    assert Aviso.query.count() == 1
    assert Aviso.query.first().texto.startswith('Hola')


def test_enviar_aviso_sin_texto_400(tienda_client):
    r = tienda_client.post('/api/tienda/admin/avisos', json={'texto': '  '},
                           headers=_auth_admin())
    assert r.status_code == 400


# ── Fase 3: motor de reglas ─────────────────────────────────────────

def test_productos_stock_bajo_lista(tienda_client):
    colegio = Colegio(nombre='COL SB', ciudad='Bogotá', activo=True)
    db.session.add(colegio)
    db.session.flush()
    prod = _producto('Camisa SB', activo=True)
    db.session.add(Stock(id_colegio=colegio.id_colegio, id_producto=prod.id_producto,
                         talla_individual='8', cantidad=3))    # bajo
    db.session.add(Stock(id_colegio=colegio.id_colegio, id_producto=prod.id_producto,
                         talla_individual='10', cantidad=50))  # ok
    db.session.commit()

    bajos = productos_stock_bajo(umbral=5)
    assert all(b['cantidad'] <= 5 for b in bajos)
    assert ('8', 3) in [(b['talla'], b['cantidad']) for b in bajos if b['producto'] == 'Camisa SB']


def test_reglas_listar_y_togglear(tienda_client):
    db.session.add(ReglaAuto(clave='alerta_stock_bajo', activa=False, config='{"umbral": 5}'))
    db.session.commit()

    r = tienda_client.get('/api/tienda/admin/reglas', headers=_auth_admin())
    assert r.status_code == 200
    assert any(x['clave'] == 'alerta_stock_bajo' for x in r.get_json()['reglas'])

    r = tienda_client.put('/api/tienda/admin/reglas/alerta_stock_bajo',
                          json={'activa': True, 'config': {'umbral': 3}},
                          headers=_auth_admin())
    assert r.status_code == 200
    d = r.get_json()['regla']
    assert d['activa'] is True
    assert d['config']['umbral'] == 3


# ── Promociones / publicaciones libres ──────────────────────────────

def test_crear_y_listar_promocion(tienda_client):
    r = tienda_client.post('/api/tienda/admin/promociones',
                           json={'titulo': 'Oferta de hoy', 'texto': '2 pares por $80.000'},
                           headers=_auth_admin())
    assert r.status_code == 201
    pid = r.get_json()['promocion']['id_promocion']

    # aparece en el endpoint público
    pub = tienda_client.get('/api/tienda/promociones').get_json()['promociones']
    assert any(p['id_promocion'] == pid and p['titulo'] == 'Oferta de hoy' for p in pub)


def test_promocion_inactiva_no_sale_en_publico(tienda_client):
    r = tienda_client.post('/api/tienda/admin/promociones',
                           json={'titulo': 'Oculta', 'activa': False},
                           headers=_auth_admin())
    pid = r.get_json()['promocion']['id_promocion']
    pub = tienda_client.get('/api/tienda/promociones').get_json()['promociones']
    assert all(p['id_promocion'] != pid for p in pub)


def test_promocion_sin_titulo_400(tienda_client):
    r = tienda_client.post('/api/tienda/admin/promociones', json={'titulo': ''},
                           headers=_auth_admin())
    assert r.status_code == 400


def test_promocion_foto_invalida_400(tienda_client):
    r = tienda_client.post('/api/tienda/admin/promociones',
                           json={'titulo': 'X', 'foto': 'no-es-imagen'},
                           headers=_auth_admin())
    assert r.status_code == 400


def test_eliminar_promocion(tienda_client):
    r = tienda_client.post('/api/tienda/admin/promociones',
                           json={'titulo': 'Borrar'}, headers=_auth_admin())
    pid = r.get_json()['promocion']['id_promocion']
    d = tienda_client.delete(f'/api/tienda/admin/promociones/{pid}', headers=_auth_admin())
    assert d.status_code == 200
    pub = tienda_client.get('/api/tienda/promociones').get_json()['promociones']
    assert all(p['id_promocion'] != pid for p in pub)
