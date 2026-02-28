#!/usr/bin/env python3
"""
Script de migración: SQLite → PostgreSQL
Migra todos los datos de la base de datos SQLite existente
al nuevo PostgreSQL de la versión web.

Uso:
  python scripts/migrar_sqlite_a_postgres.py --sqlite ../../data/usuarios_central.db
"""

import argparse
import sqlite3
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import *


def migrar(sqlite_path):
    """Migrar datos de SQLite a PostgreSQL"""
    if not os.path.exists(sqlite_path):
        print(f"❌ No se encontró: {sqlite_path}")
        return

    app = create_app()

    with app.app_context():
        # Crear tablas
        db.create_all()
        print("✓ Tablas PostgreSQL creadas")

        # Conectar a SQLite
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Usuarios
        print("\n[1/10] Migrando usuarios...")
        cursor.execute("SELECT * FROM usuarios")
        for row in cursor.fetchall():
            existente = Usuario.query.filter_by(usuario=row['usuario']).first()
            if not existente:
                u = Usuario(
                    usuario=row['usuario'],
                    contrasena_hash=row['contraseña_hash'],
                    rol=row['rol'] or 'vendedor',
                    activo=bool(row['activo']),
                )
                db.session.add(u)
        db.session.commit()
        print(f"   ✓ {Usuario.query.count()} usuarios")

        # 2. Colegios
        print("[2/10] Migrando colegios...")
        cursor.execute("SELECT * FROM colegios")
        for row in cursor.fetchall():
            c = Colegio(nombre=row['nombre'], ciudad=row['ciudad'], activo=bool(row['activo']))
            db.session.add(c)
        db.session.commit()
        print(f"   ✓ {Colegio.query.count()} colegios")

        # 3. Productos
        print("[3/10] Migrando productos...")
        cursor.execute("SELECT * FROM productos")
        for row in cursor.fetchall():
            p = Producto(codigo=row['codigo'], nombre=row['nombre'], tipo=row['tipo'], activo=bool(row['activo']))
            db.session.add(p)
        db.session.commit()
        print(f"   ✓ {Producto.query.count()} productos")

        # 4. Métodos de pago
        print("[4/10] Migrando métodos de pago...")
        cursor.execute("SELECT * FROM metodos_pago")
        for row in cursor.fetchall():
            m = MetodoPago(nombre=row['nombre'], activo=bool(row['activo']))
            db.session.add(m)
        db.session.commit()
        print(f"   ✓ {MetodoPago.query.count()} métodos")

        # 5. Precios
        print("[5/10] Migrando precios...")
        cursor.execute("SELECT * FROM precios_colegio")
        for row in cursor.fetchall():
            p = PrecioColegio(
                id_colegio=row['id_colegio'], id_producto=row['id_producto'],
                talla_grupo=row['talla_grupo'], precio_unitario=row['precio_unitario']
            )
            db.session.add(p)
        db.session.commit()
        print(f"   ✓ {PrecioColegio.query.count()} precios")

        # 6. Stock
        print("[6/10] Migrando stock...")
        cursor.execute("SELECT * FROM stock")
        for row in cursor.fetchall():
            s = Stock(
                id_colegio=row['id_colegio'], id_producto=row['id_producto'],
                talla_individual=row['talla_individual'], cantidad=row['cantidad']
            )
            db.session.add(s)
        db.session.commit()
        print(f"   ✓ {Stock.query.count()} registros de stock")

        # 7. Clientes
        print("[7/10] Migrando clientes...")
        try:
            cursor.execute("SELECT * FROM clientes")
            for row in cursor.fetchall():
                c = Cliente(
                    nombre=row['nombre'], telefono=row['telefono'],
                    email=row['email'], direccion=row['direccion'],
                    id_colegio=row['id_colegio'],
                )
                db.session.add(c)
            db.session.commit()
            print(f"   ✓ {Cliente.query.count()} clientes")
        except Exception:
            print("   ⚠️ Tabla clientes no encontrada, saltando...")

        # 8. Facturas + Detalles
        print("[8/10] Migrando facturas...")
        cursor.execute("SELECT * FROM facturas ORDER BY id_factura")
        for row in cursor.fetchall():
            f = Factura(
                numero_factura=row['numero_factura'],
                id_colegio=row['id_colegio'],
                cliente_nombre=row['cliente_nombre'],
                fecha_factura=row['fecha_factura'],
                total=row['total'],
                estado=row['estado'],
                usuario_creacion=row['usuario_creacion'],
            )
            db.session.add(f)
            db.session.flush()

            # Detalles
            cursor2 = conn.cursor()
            cursor2.execute("SELECT * FROM factura_detalle WHERE id_factura = ?", (row['id_factura'],))
            for det in cursor2.fetchall():
                d = FacturaDetalle(
                    id_factura=f.id_factura,
                    id_producto=det['id_producto'],
                    talla_individual=det['talla_individual'],
                    cantidad=det['cantidad'],
                    precio_unitario=det['precio_unitario'],
                    total_linea=det['total_linea'],
                )
                db.session.add(d)

        db.session.commit()
        print(f"   ✓ {Factura.query.count()} facturas")

        # 9. Pagos
        print("[9/10] Migrando pagos...")
        cursor.execute("SELECT * FROM pagos")
        for row in cursor.fetchall():
            p = Pago(
                id_factura=row['id_factura'],
                fecha_pago=row['fecha_pago'],
                valor=row['valor'],
                metodo_pago=row['metodo_pago'],
                usuario_registro=row['usuario_registro'],
            )
            db.session.add(p)
        db.session.commit()
        print(f"   ✓ {Pago.query.count()} pagos")

        # 10. Gastos
        print("[10/10] Migrando gastos...")
        cursor.execute("SELECT * FROM gastos")
        for row in cursor.fetchall():
            g = Gasto(
                fecha=row['fecha'],
                descripcion=row['descripcion'],
                valor=row['valor'],
                metodo_pago=row['metodo_pago'],
                usuario_registro=row['usuario_registro'],
            )
            db.session.add(g)
        db.session.commit()
        print(f"   ✓ {Gasto.query.count()} gastos")

        conn.close()
        print("\n" + "=" * 50)
        print("   ✅ MIGRACIÓN COMPLETADA")
        print("=" * 50)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrar SQLite a PostgreSQL')
    parser.add_argument('--sqlite', required=True, help='Ruta a la base SQLite')
    args = parser.parse_args()
    migrar(args.sqlite)
