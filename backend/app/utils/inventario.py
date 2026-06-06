"""
Lógica central de inventario (kardex).

registrar_movimiento() es el ÚNICO lugar donde se cambia el stock:
actualiza la tabla Stock y deja el registro en el kardex. Así nunca se
desincronizan. NO hace commit (lo hace quien llama, para mantener la
transacción atómica del caller).
"""
from app import db
from app.models import Stock, MovimientoInventario

TIPOS = ('ENTRADA', 'SALIDA', 'AJUSTE')


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
