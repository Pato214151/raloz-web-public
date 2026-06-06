"""
Lógica central de inventario (kardex).

registrar_movimiento() es el ÚNICO lugar donde se cambia el stock:
actualiza la tabla Stock y deja el registro en el kardex. Así nunca se
desincronizan. NO hace commit (lo hace quien llama, para mantener la
transacción atómica del caller).
"""
from app import db
from app.models import Stock, MovimientoInventario, PrecioColegio
from app.utils.tallas import TALLA_GRUPO_A_INDIVIDUALES

TIPOS = ('ENTRADA', 'SALIDA', 'AJUSTE')

# Orden lógico de tallas para mostrar el catálogo
_TALLA_ORDEN = ['2', '4', '6', '8', '10', '12', '14', '16',
                'XS', 'S', 'M', 'L', 'XL', 'XXL', 'Única',
                '6-8', '8-10', '10-12', '12-14', '14-16', 'S-M']


def _orden_talla(t):
    try:
        return (0, _TALLA_ORDEN.index(t), '')
    except ValueError:
        return (1, 99, str(t))


def construir_catalogo_colegio(colegio_id):
    """
    Devuelve el catálogo completo de un colegio: cada prenda que vende
    (según precios_colegio) con su stock por talla — INCLUIDAS las tallas
    en 0. Lista de dicts ordenada por nombre de producto.
    """
    precios = PrecioColegio.query.filter_by(id_colegio=colegio_id).all()

    stock_map = {
        (s.id_producto, s.talla_individual): (s.cantidad or 0)
        for s in Stock.query.filter_by(id_colegio=colegio_id).all()
    }

    productos = {}
    for p in precios:
        info = productos.setdefault(p.id_producto, {
            'id_producto': p.id_producto,
            'producto_nombre': p.producto.nombre if p.producto else f'Prod#{p.id_producto}',
            'producto_tipo': p.producto.tipo if p.producto else None,
            'tallas': set(),
        })
        for t in TALLA_GRUPO_A_INDIVIDUALES.get(p.talla_grupo, [p.talla_grupo]):
            info['tallas'].add(t)

    catalogo = []
    for pid, info in productos.items():
        tallas_ord = sorted(info['tallas'], key=_orden_talla)
        filas = [{'talla': t, 'cantidad': stock_map.get((pid, t), 0)} for t in tallas_ord]
        catalogo.append({
            'id_producto': info['id_producto'],
            'producto_nombre': info['producto_nombre'],
            'producto_tipo': info['producto_tipo'],
            'tallas': filas,
            'total': sum(f['cantidad'] for f in filas),
        })
    catalogo.sort(key=lambda c: c['producto_nombre'])
    return catalogo


def registrar_movimiento(id_colegio, id_producto, talla, tipo, cantidad,
                         usuario, motivo='', referencia=None):
    """
    Aplica un movimiento de inventario y lo registra en el kardex.

    tipo:
      ENTRADA → suma `cantidad` al stock
      SALIDA  → resta `cantidad` (con piso en 0)
      AJUSTE  → fija el stock en `cantidad` (corrección manual)

    Devuelve (stock, movimiento). No hace commit.
    """
    tipo = tipo.upper()
    if tipo not in TIPOS:
        raise ValueError(f'Tipo de movimiento inválido: {tipo}')
    cantidad = int(cantidad)

    stock = Stock.query.filter_by(
        id_colegio=id_colegio, id_producto=id_producto, talla_individual=talla,
    ).first()
    if not stock:
        stock = Stock(id_colegio=id_colegio, id_producto=id_producto,
                      talla_individual=talla, cantidad=0)
        db.session.add(stock)
        db.session.flush()

    if tipo == 'ENTRADA':
        stock.cantidad = (stock.cantidad or 0) + cantidad
    elif tipo == 'SALIDA':
        stock.cantidad = max(0, (stock.cantidad or 0) - cantidad)
    else:  # AJUSTE
        stock.cantidad = max(0, cantidad)

    mov = MovimientoInventario(
        id_colegio=id_colegio,
        id_producto=id_producto,
        talla_individual=talla,
        tipo=tipo,
        cantidad=cantidad,
        stock_resultante=stock.cantidad,
        motivo=motivo or '',
        referencia=referencia,
        usuario=usuario or 'sistema',
    )
    db.session.add(mov)
    return stock, mov
