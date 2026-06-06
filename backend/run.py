"""
RALOZ COL SAS - Entry Point
"""

import threading
import time
import logging
from datetime import datetime

from app import create_app, db
from app.models import *

logger = logging.getLogger(__name__)
app = create_app()


# ─── Job: expiración automática de reservas (cada 60 s) ──────────
def _job_limpiar_reservas():
    """
    Hilo daemon que cada 60 s marca como 'expirada' las reservas
    cuya fecha_expiracion ya pasó y siguen en estado 'activa'.
    daemon=True → muere automáticamente cuando gunicorn para el worker.

    Con varios workers de gunicorn, cada uno corre este hilo; para que la
    limpieza la haga SOLO UNO por ciclo usamos un advisory lock de PostgreSQL
    (pg_try_advisory_xact_lock). El que obtiene el lock limpia; los demás saltan.
    """
    from sqlalchemy import text
    time.sleep(15)  # espera inicial — deja que la app arranque completamente
    while True:
        try:
            with app.app_context():
                # lock por transacción (se libera solo al hacer commit)
                tengo_lock = db.session.execute(
                    text("SELECT pg_try_advisory_xact_lock(1001)")
                ).scalar()
                if tengo_lock:
                    actualizadas = Reserva.query.filter(
                        Reserva.estado == 'activa',
                        Reserva.fecha_expiracion < datetime.utcnow(),
                    ).update({'estado': 'expirada'})
                    # Limpiar tokens revocados ya vencidos (un token vencido se
                    # rechaza por sí solo, ya no hace falta tenerlo en la lista negra).
                    TokenRevocado.query.filter(
                        TokenRevocado.expira.isnot(None),
                        TokenRevocado.expira < datetime.utcnow(),
                    ).delete(synchronize_session=False)
                    if actualizadas:
                        logger.info('[RESERVAS-JOB] %d reserva(s) marcadas como expirada', actualizadas)
                db.session.commit()
        except Exception as e:
            logger.error('[RESERVAS-JOB] Error: %s', str(e))
        time.sleep(60)


threading.Thread(target=_job_limpiar_reservas, daemon=True, name='reservas-cleanup').start()


# ─── MEJORA #4: Job: cancelación de pedidos abandonados (cada 5 min) ──
def _job_cancelar_pedidos_abandonados():
    """
    Hilo daemon que cada 5 minutos marca como 'cancelado' los pedidos
    que siguen en estado 'pendiente' después de 24 horas sin pago.
    """
    from sqlalchemy import text
    from datetime import timedelta as td
    time.sleep(30)  # espera inicial
    while True:
        try:
            with app.app_context():
                tengo_lock = db.session.execute(
                    text("SELECT pg_try_advisory_xact_lock(1002)")
                ).scalar()
                if tengo_lock:
                    corte = datetime.utcnow() - td(hours=24)
                    cancelados = PedidoWeb.query.filter(
                        PedidoWeb.estado == 'pendiente',
                        PedidoWeb.fecha_creacion < corte,
                    ).update({'estado': 'cancelado'})
                    if cancelados:
                        logger.info('[PEDIDOS-JOB] %d pedido(s) cancelados por abandono (>24h)', cancelados)
                db.session.commit()
        except Exception as e:
            logger.error('[PEDIDOS-JOB] Error: %s', str(e))
        time.sleep(300)  # cada 5 minutos


threading.Thread(target=_job_cancelar_pedidos_abandonados, daemon=True, name='pedidos-abandonados-cleanup').start()


# ─── Migración automática de columnas nuevas ─────────────────────
def _auto_migrate():
    """Crea tablas nuevas y añade columnas opcionales a tablas existentes."""
    with app.app_context():
        from sqlalchemy import text
        db.create_all()  # crea tablas nuevas (pedidos_fabricacion, stock_pendiente_fabricacion)

        # MEJORA #7: Renombrar columna wompi_transaction_id → mp_preference_id
        try:
            db.session.execute(text(
                "ALTER TABLE pedidos_web RENAME COLUMN wompi_transaction_id TO mp_preference_id"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()  # ya renombrada o no existe, seguir

        migraciones = [
            # Columnas extra en pedidos_web para soporte de fabricación
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS total_orden FLOAT",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS abono_porcentaje INTEGER DEFAULT 100",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS tiene_fabricacion BOOLEAN DEFAULT FALSE",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS tipo_entrega VARCHAR(20) DEFAULT 'completa'",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS direccion_envio VARCHAR(300)",
            # Columna ABONO en facturas (por si no existe)
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS total_abonado FLOAT",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS saldo_pendiente FLOAT DEFAULT 0",
            # Estado de entrega en facturas (flujo: POR_ENTREGAR → EMPACADO → ENTREGADO)
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS estado_entrega VARCHAR(20) DEFAULT 'POR_ENTREGAR'",
            "UPDATE facturas SET estado_entrega = 'POR_ENTREGAR' WHERE estado_entrega IS NULL",
            # Columnas en series_facturacion (por si fueron creadas antes de que existieran)
            "ALTER TABLE series_facturacion ADD COLUMN IF NOT EXISTS prefijo VARCHAR(10) DEFAULT 'FAC'",
            "ALTER TABLE series_facturacion ADD COLUMN IF NOT EXISTS formato VARCHAR(100) DEFAULT 'FAC-{ano}-{consecutivo:06d}'",
            "ALTER TABLE series_facturacion ADD COLUMN IF NOT EXISTS activa BOOLEAN DEFAULT TRUE",
            # Reparar filas existentes con valores NULL
            "UPDATE series_facturacion SET formato = 'FAC-{ano}-{consecutivo:06d}' WHERE formato IS NULL",
            "UPDATE series_facturacion SET prefijo = 'FAC' WHERE prefijo IS NULL",
            "UPDATE series_facturacion SET activa = TRUE WHERE activa IS NULL",
            # Índices para consultas frecuentes en dashboard y reportes
            "CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha_pago)",
            "CREATE INDEX IF NOT EXISTS idx_pedidos_web_estado ON pedidos_web(estado)",
            "CREATE INDEX IF NOT EXISTS idx_pedidos_web_referencia ON pedidos_web(referencia)",
            "CREATE INDEX IF NOT EXISTS idx_facturas_estado_saldo ON facturas(estado, saldo_pendiente)",
            # Dirección en pedidos_fabricacion
            "ALTER TABLE pedidos_fabricacion ADD COLUMN IF NOT EXISTS direccion_envio VARCHAR(300)",
            # ── Consolidado desde app/__init__.py (un solo lugar de migraciones) ──
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS canal VARCHAR(20) DEFAULT 'PRESENCIAL'",
            "ALTER TABLE gastos ADD COLUMN IF NOT EXISTS tipo_gasto VARCHAR(20) DEFAULT 'TIENDA'",
            "ALTER TABLE tareas ADD COLUMN IF NOT EXISTS prioridad VARCHAR(10) DEFAULT 'MEDIA'",
            "UPDATE tareas SET prioridad = 'MEDIA' WHERE prioridad IS NULL",
            """CREATE TABLE IF NOT EXISTS caja_diaria (
                id_caja          SERIAL PRIMARY KEY,
                fecha_apertura   TIMESTAMP NOT NULL,
                fecha_cierre     TIMESTAMP,
                usuario_apertura VARCHAR(100) NOT NULL,
                usuario_cierre   VARCHAR(100),
                monto_inicial    FLOAT DEFAULT 0,
                total_ventas     FLOAT DEFAULT 0,
                total_gastos     FLOAT DEFAULT 0,
                monto_esperado   FLOAT DEFAULT 0,
                monto_real       FLOAT DEFAULT 0,
                diferencia       FLOAT DEFAULT 0,
                estado           VARCHAR(20) DEFAULT 'ABIERTA',
                observaciones    TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS movimientos_caja (
                id_movimiento SERIAL PRIMARY KEY,
                id_caja       INTEGER NOT NULL REFERENCES caja_diaria(id_caja),
                tipo          VARCHAR(50) NOT NULL,
                concepto      VARCHAR(500),
                valor         FLOAT NOT NULL,
                metodo_pago   VARCHAR(50),
                referencia    VARCHAR(200),
                usuario       VARCHAR(100) NOT NULL,
                fecha_hora    TIMESTAMP DEFAULT NOW()
            )""",
            "CREATE INDEX IF NOT EXISTS idx_movimientos_caja ON movimientos_caja(id_caja)",
            # Productos 19-22 (Camiseta/Chaqueta Ed. Física por género — Manyanet)
            "INSERT INTO productos (id_producto, codigo, nombre, tipo, activo) VALUES (19, 'CAMISETA-NINO', 'Camiseta Ed. Física Niño', 'Ed. Física Niño', true) ON CONFLICT DO NOTHING",
            "INSERT INTO productos (id_producto, codigo, nombre, tipo, activo) VALUES (20, 'CAMISETA-NINA', 'Camiseta Ed. Física Niña', 'Ed. Física Niña', true) ON CONFLICT DO NOTHING",
            "INSERT INTO productos (id_producto, codigo, nombre, tipo, activo) VALUES (21, 'CHQ-EDU-NINO', 'Chaqueta Ed. Física Niño', 'Ed. Física Niño', true) ON CONFLICT DO NOTHING",
            "INSERT INTO productos (id_producto, codigo, nombre, tipo, activo) VALUES (22, 'CHQ-EDU-NINA', 'Chaqueta Ed. Física Niña', 'Ed. Física Niña', true) ON CONFLICT DO NOTHING",
            # Actualizar secuencia de productos para evitar colisión de IDs futuros
            "SELECT setval('productos_id_producto_seq', GREATEST(22, (SELECT MAX(id_producto) FROM productos)))",
            # Precios Manyanet (colegio 3) para productos 19-22
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,19,'6-8',40000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,19,'10-12',43000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,19,'14-16',45000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,19,'S-M',53000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,19,'L',57000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,19,'XL',60000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,20,'6-8',40000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,20,'10-12',43000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,20,'14-16',45000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,20,'S-M',53000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,20,'L',57000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,20,'XL',60000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,21,'6-8',86000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,21,'10-12',91000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,21,'14-16',99300) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,21,'S-M',104000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,21,'L',110000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,21,'XL',120000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,22,'6-8',86000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,22,'10-12',91000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,22,'14-16',99300) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,22,'S-M',104000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,22,'L',110000) ON CONFLICT DO NOTHING",
            "INSERT INTO precios_colegio (id_colegio, id_producto, talla_grupo, precio_unitario) VALUES (3,22,'XL',120000) ON CONFLICT DO NOTHING",
        ]
        for sql in migraciones:
            try:
                db.session.execute(text(sql))
            except Exception:
                pass
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


def _auto_migrate_con_retry(intentos=5, espera_inicial=3):
    """
    Llama a _auto_migrate() con reintentos en caso de fallo transitorio de BD
    (DNS failure, cold start de Supabase/Render, timeout de red).
    Si todos los intentos fallan, loguea el error pero NO deja caer la app.
    """
    import math
    for intento in range(1, intentos + 1):
        try:
            _auto_migrate()
            if intento > 1:
                logger.info('[STARTUP] Migración exitosa en intento %d', intento)
            return
        except Exception as e:
            espera = espera_inicial * math.pow(2, intento - 1)  # 3, 6, 12, 24, 48 s
            if intento < intentos:
                logger.warning(
                    '[STARTUP] Error de BD en intento %d/%d (%s). Reintentando en %.0f s...',
                    intento, intentos, str(e)[:120], espera
                )
                time.sleep(espera)
            else:
                logger.error(
                    '[STARTUP] No se pudo conectar a la BD después de %d intentos. '
                    'La app arrancará sin migraciones automáticas: %s',
                    intentos, str(e)
                )

_auto_migrate_con_retry()


@app.cli.command('init-db')
def init_db():
    """Crear todas las tablas"""
    with app.app_context():
        db.create_all()
        print("✓ Tablas creadas exitosamente")


@app.cli.command('seed')
def seed():
    """Insertar datos iniciales"""
    with app.app_context():
        import bcrypt
        from datetime import datetime

        # Métodos de pago
        metodos = ['EFECTIVO', 'NEQUI', 'DAVIPLATA', 'BANCOLOMBIA', 'TRANSFERENCIA']
        for nombre in metodos:
            existente = MetodoPago.query.filter_by(nombre=nombre).first()
            if not existente:
                db.session.add(MetodoPago(nombre=nombre))
        print("✓ Métodos de pago creados")

        # Serie de facturación
        serie = SerieFacturacion.query.filter_by(activa=True).first()
        if not serie:
            db.session.add(SerieFacturacion(ano=datetime.now().year, consecutivo_actual=0))
        print("✓ Serie de facturación creada")

        # Usuario admin por defecto
        admin = Usuario.query.filter_by(usuario='admin').first()
        if not admin:
            salt = bcrypt.gensalt(rounds=12)
            hash_pw = bcrypt.hashpw('admin123'.encode('utf-8'), salt).decode('utf-8')
            admin = Usuario(
                usuario='admin',
                email='admin@raloz.com',
                contrasena_hash=hash_pw,
                rol='administrador',
            )
            db.session.add(admin)
            print("✓ Usuario admin creado (password: admin123) — ¡CAMBIAR EN PRODUCCIÓN!")
        else:
            print("ℹ️  Usuario admin ya existe")

        db.session.commit()
        print("\n✅ Datos iniciales insertados")


if __name__ == '__main__':
    import os
    # debug SOLO si FLASK_DEBUG=1 explícitamente. Nunca activar en producción:
    # con debug=True se expone la consola interactiva de Werkzeug (ejecución de
    # código remoto). En producción se usa gunicorn, no este bloque.
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host='127.0.0.1', port=5000)
