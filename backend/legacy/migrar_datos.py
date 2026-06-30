"""
RALOZ COL SAS — Migrar datos de SQLite (escritorio) a PostgreSQL (web)
Ejecutar: python scripts/migrar_datos.py
"""

import sqlite3
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import (
    Colegio, Producto, PrecioColegio, Stock, Factura, FacturaDetalle,
    Pago, Gasto, Cliente, MetodoPago, SerieFacturacion, CajaDiaria,
    StockPendiente
)
from datetime import datetime, date


def parse_date(val):
    """Convertir string de fecha a objeto date"""
    if not val:
        return None
    try:
        if 'T' in str(val) or ' ' in str(val):
            return datetime.fromisoformat(str(val).replace('T', ' ').split('.')[0]).date()
        return datetime.strptime(str(val), '%Y-%m-%d').date()
    except Exception:
        return None


def parse_datetime(val):
    """Convertir string de datetime a objeto datetime"""
    if not val:
        return None
    try:
        return datetime.fromisoformat(str(val).replace('T', ' ').split('.')[0])
    except Exception:
        return None


def migrate():
    SQLITE_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        '..', 'data', 'usuarios_central.db'
    )

    if not os.path.exists(SQLITE_PATH):
        print(f"❌ No se encontró la base de datos SQLite en: {SQLITE_PATH}")
        sys.exit(1)

    print(f"📂 SQLite: {SQLITE_PATH}")
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    app = create_app()
    with app.app_context():
        # ── 1. Colegios ──
        print("\n→ Migrando colegios...")
        cursor.execute("SELECT * FROM colegios")
        count = 0
        for row in cursor.fetchall():
            existing = Colegio.query.filter_by(id_colegio=row['id_colegio']).first()
            if not existing:
                c = Colegio(
                    id_colegio=row['id_colegio'],
                    nombre=row['nombre'],
                    ciudad=row['ciudad'] or '',
                    activo=bool(row['activo']),
                    fecha_creacion=parse_datetime(row['fecha_creacion']) or datetime.utcnow(),
                )
                db.session.add(c)
                count += 1
        db.session.commit()
        print(f"  ✓ {count} colegios migrados")

        # ── 2. Productos ──
        print("\n→ Migrando productos...")
        cursor.execute("SELECT * FROM productos")
        count = 0
        for row in cursor.fetchall():
            existing = Producto.query.filter_by(id_producto=row['id_producto']).first()
            if not existing:
                p = Producto(
                    id_producto=row['id_producto'],
                    codigo=row['codigo'] or '',
                    nombre=row['nombre'],
                    tipo=row['tipo'] or '',
                    activo=bool(row['activo']),
                    fecha_creacion=parse_datetime(row['fecha_creacion']) or datetime.utcnow(),
                )
                db.session.add(p)
                count += 1
        db.session.commit()
        print(f"  ✓ {count} productos migrados")

        # ── 3. Precios por colegio ──
        print("\n→ Migrando precios...")
        cursor.execute("SELECT * FROM precios_colegio")
        count = 0
        for row in cursor.fetchall():
            existing = PrecioColegio.query.filter_by(id_precio=row['id_precio']).first()
            if not existing:
                pc = PrecioColegio(
                    id_precio=row['id_precio'],
                    id_colegio=row['id_colegio'],
                    id_producto=row['id_producto'],
                    talla_grupo=row['talla_grupo'] or '',
                    precio_unitario=float(row['precio_unitario'] or 0),
                )
                db.session.add(pc)
                count += 1
        db.session.commit()
        print(f"  ✓ {count} precios migrados")

        # ── 4. Stock ──
        print("\n→ Migrando stock...")
        cursor.execute("SELECT * FROM stock")
        count = 0
        for row in cursor.fetchall():
            existing = Stock.query.filter_by(id_stock=row['id_stock']).first()
            if not existing:
                s = Stock(
                    id_stock=row['id_stock'],
                    id_colegio=row['id_colegio'],
                    id_producto=row['id_producto'],
                    talla_individual=row['talla_individual'] or '',
                    cantidad=int(row['cantidad'] or 0),
                    fecha_actualizacion=parse_datetime(row['fecha_actualizacion']),
                )
                db.session.add(s)
                count += 1
        db.session.commit()
        print(f"  ✓ {count} registros de stock migrados")

        # ── 5. Clientes ──
        print("\n→ Migrando clientes...")
        cursor.execute("SELECT * FROM clientes")
        count = 0
        for row in cursor.fetchall():
            existing = Cliente.query.filter_by(id_cliente=row['id_cliente']).first()
            if not existing:
                cl = Cliente(
                    id_cliente=row['id_cliente'],
                    tipo_documento=row['tipo_documento'] or '',
                    numero_documento=row['numero_documento'] or '',
                    nombre=row['nombre'] or '',
                    telefono=row['celular'] or row['telefono'] or '',
                    email=row['email'] or '',
                    direccion=row['direccion'] or '',
                    id_colegio=row['id_colegio'],
                    notas=row['notas'] or '',
                    activo=bool(row['activo']) if row['activo'] is not None else True,
                    fecha_creacion=parse_datetime(row['fecha_creacion']) or datetime.utcnow(),
                )
                db.session.add(cl)
                count += 1
        db.session.commit()
        print(f"  ✓ {count} clientes migrados")

        # ── 6. Facturas ──
        print("\n→ Migrando facturas...")
        cursor.execute("SELECT * FROM facturas ORDER BY id_factura")
        count = 0
        for row in cursor.fetchall():
            existing = Factura.query.filter_by(id_factura=row['id_factura']).first()
            if not existing:
                f = Factura(
                    id_factura=row['id_factura'],
                    numero_factura=row['numero_factura'] or '',
                    id_colegio=row['id_colegio'],
                    cliente_nombre=row['cliente_nombre'] or '',
                    cliente_telefono=row['cliente_telefono'] or '',
                    fecha_factura=parse_date(row['fecha_factura']) or date.today(),
                    total=float(row['total'] or 0),
                    estado=row['estado'] or 'PENDIENTE',
                    usuario_creacion=row['usuario_creacion'] or 'admin',
                    fecha_creacion=parse_datetime(row['fecha_creacion']) or datetime.utcnow(),
                )
                db.session.add(f)
                count += 1
        db.session.commit()
        print(f"  ✓ {count} facturas migradas")

        # ── 7. Detalle de facturas ──
        print("\n→ Migrando detalles de facturas...")
        cursor.execute("SELECT * FROM factura_detalle ORDER BY id_detalle")
        count = 0
        for row in cursor.fetchall():
            existing = FacturaDetalle.query.filter_by(id_detalle=row['id_detalle']).first()
            if not existing:
                fd = FacturaDetalle(
                    id_detalle=row['id_detalle'],
                    id_factura=row['id_factura'],
                    id_producto=row['id_producto'],
                    talla_individual=row['talla_individual'] or '',
                    cantidad=int(row['cantidad'] or 0),
                    precio_unitario=float(row['precio_unitario'] or 0),
                    total_linea=float(row['total_linea'] or 0),
                )
                db.session.add(fd)
                count += 1
        db.session.commit()
        print(f"  ✓ {count} detalles migrados")

        # ── 8. Pagos ──
        print("\n→ Migrando pagos...")
        cursor.execute("SELECT * FROM pagos ORDER BY id_pago")
        count = 0
        for row in cursor.fetchall():
            existing = Pago.query.filter_by(id_pago=row['id_pago']).first()
            if not existing:
                p = Pago(
                    id_pago=row['id_pago'],
                    id_factura=row['id_factura'],
                    fecha_pago=parse_date(row['fecha_pago']) or date.today(),
                    valor=float(row['valor'] or 0),
                    metodo_pago=row['metodo_pago'] or 'EFECTIVO',
                    usuario_registro=row['usuario_registro'] or 'admin',
                    fecha_registro=parse_datetime(row['fecha_registro']) or datetime.utcnow(),
                )
                db.session.add(p)
                count += 1
        db.session.commit()
        print(f"  ✓ {count} pagos migrados")

        # ── 9. Gastos ──
        print("\n→ Migrando gastos...")
        cursor.execute("SELECT * FROM gastos ORDER BY id_gasto")
        count = 0
        for row in cursor.fetchall():
            existing = Gasto.query.filter_by(id_gasto=row['id_gasto']).first()
            if not existing:
                g = Gasto(
                    id_gasto=row['id_gasto'],
                    fecha=parse_date(row['fecha']) or date.today(),
                    descripcion=row['descripcion'] or '',
                    valor=float(row['valor'] or 0),
                    metodo_pago=row['metodo_pago'] or 'EFECTIVO',
                    usuario_registro=row['usuario_registro'] or 'admin',
                    fecha_registro=parse_datetime(row['fecha_registro']) or datetime.utcnow(),
                )
                db.session.add(g)
                count += 1
        db.session.commit()
        print(f"  ✓ {count} gastos migrados")

        # ── 10. Actualizar secuencias de PostgreSQL ──
        print("\n→ Actualizando secuencias de IDs...")
        sequences = [
            ('colegios', 'id_colegio'),
            ('productos', 'id_producto'),
            ('precios_colegio', 'id_precio'),
            ('stock', 'id_stock'),
            ('clientes', 'id_cliente'),
            ('facturas', 'id_factura'),
            ('factura_detalle', 'id_detalle'),
            ('pagos', 'id_pago'),
            ('gastos', 'id_gasto'),
        ]
        for tabla, col in sequences:
            try:
                db.session.execute(db.text(
                    f"SELECT setval(pg_get_serial_sequence('{tabla}', '{col}'), "
                    f"COALESCE((SELECT MAX({col}) FROM {tabla}), 1))"
                ))
            except Exception as e:
                print(f"  ⚠ Secuencia {tabla}.{col}: {e}")
        db.session.commit()
        print("  ✓ Secuencias actualizadas")

        # ── 11. Actualizar serie de facturación ──
        cursor.execute("SELECT MAX(CAST(REPLACE(REPLACE(numero_factura, 'R-', ''), 'FAC-', '') AS INTEGER)) FROM facturas")
        max_num = cursor.fetchone()[0] or 0
        serie = SerieFacturacion.query.filter_by(activa=True).first()
        if serie:
            serie.consecutivo_actual = max(serie.consecutivo_actual, max_num)
            db.session.commit()
            print(f"  ✓ Serie de facturación actualizada a {serie.consecutivo_actual}")

    conn.close()
    print("\n══════════════════════════════════════")
    print("  ✅ MIGRACIÓN COMPLETADA")
    print("══════════════════════════════════════")


if __name__ == '__main__':
    migrate()
