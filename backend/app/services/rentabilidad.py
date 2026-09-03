"""
Rentabilidad — costo de mercancía vendida (CMV) y utilidad real.

El reporte de utilidad NO es "cobrado − gastos": eso ignora lo que costó la
mercancía y muestra una utilidad inflada. La cadena correcta es:

    Ventas
    − CMV (costo de la mercancía vendida)
    = Utilidad bruta

    Utilidad bruta
    − Gastos operativos
    = Utilidad operacional

El costo por prenda vive en `PrecioColegio.costo_unitario` (por colegio +
producto + talla_grupo). Cuando ese costo no está cargado, se ESTIMA como el
60% del precio de venta (misma regla usada en el resto del sistema) y el
resultado se marca como estimado para que quien lo lea sepa que es aproximado.
"""
from app import db
from app.models import Factura, FacturaDetalle, PrecioColegio
from app.utils.tallas import convertir_a_grupo

# Cuando no hay costo real cargado, se asume que la prenda costó el 60% de su
# precio de venta (regla de negocio; ~40% de margen bruto estimado).
COSTO_PCT_ESTIMADO = 0.60


def _mapa_costos():
    """{(id_colegio, id_producto, talla_grupo): costo_unitario} para los que tienen costo."""
    mapa = {}
    for pc in PrecioColegio.query.filter(PrecioColegio.costo_unitario.isnot(None)).all():
        if pc.costo_unitario:
            mapa[(pc.id_colegio, pc.id_producto, pc.talla_grupo)] = float(pc.costo_unitario)
    return mapa


def cmv_periodo(fecha_desde, fecha_hasta, colegio_id=None):
    """Costo de la mercancía vendida en el período (excluye facturas anuladas).

    Devuelve el CMV total separando la parte con costo real de la estimada, y
    marca `hay_estimado` cuando alguna línea usó el 60% por falta de costo.
    """
    q = db.session.query(
        Factura.id_colegio,
        FacturaDetalle.id_producto,
        FacturaDetalle.talla_individual,
        FacturaDetalle.cantidad,
        FacturaDetalle.precio_unitario,
        FacturaDetalle.total_linea,
    ).join(Factura, FacturaDetalle.id_factura == Factura.id_factura).filter(
        Factura.fecha_factura >= fecha_desde,
        Factura.fecha_factura <= fecha_hasta,
        Factura.estado != 'ANULADA',
    )
    if colegio_id:
        q = q.filter(Factura.id_colegio == colegio_id)

    costos = _mapa_costos()
    cmv_real = 0.0
    cmv_estimado = 0.0
    unidades = 0

    for fila in q.all():
        cant = fila.cantidad or 0
        unidades += cant
        try:
            grupo = convertir_a_grupo(fila.talla_individual)
        except Exception:
            grupo = None
        costo = costos.get((fila.id_colegio, fila.id_producto, grupo))
        if not costo:
            # Filas legacy donde el grupo se guardó como talla individual
            # ('M' en vez de 'S-M'): mejor el costo real que el estimado.
            costo = costos.get((fila.id_colegio, fila.id_producto,
                                fila.talla_individual))
        if costo:
            cmv_real += costo * cant
        else:
            base = float(fila.total_linea or (fila.precio_unitario or 0) * cant)
            cmv_estimado += COSTO_PCT_ESTIMADO * base

    return {
        'cmv_total': round(cmv_real + cmv_estimado, 2),
        'cmv_real': round(cmv_real, 2),
        'cmv_estimado': round(cmv_estimado, 2),
        'hay_estimado': cmv_estimado > 0,
        'unidades': unidades,
    }
