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
    Idempotente: múltiples workers haciendo el UPDATE al mismo tiempo es seguro.
    """
    time.sleep(15)  # espera inicial — deja que la app arranque completamente
    while True:
        try:
            with app.app_context():
                actualizadas = Reserva.query.filter(
                    Reserva.estado == 'activa',
                    Reserva.fecha_expiracion < datetime.utcnow(),
                ).update({'estado': 'expirada'})
                db.session.commit()
                if actualizadas:
                    logger.info('[RESERVAS-JOB] %d reserva(s) marcadas como expirada', actualizadas)
        except Exception as e:
            logger.error('[RESERVAS-JOB] Error: %s', str(e))
        time.sleep(60)


threading.Thread(target=_job_limpiar_reservas, daemon=True, name='reservas-cleanup').start()


# ─── Migración automática de columnas nuevas ─────────────────────
def _auto_migrate():
    """Crea tablas nuevas y añade columnas opcionales a tablas existentes."""
    with app.app_context():
        from sqlalchemy import text
        db.create_all()  # crea tablas nuevas (pedidos_fabricacion, stock_pendiente_fabricacion)
        migraciones = [
            # Columnas extra en pedidos_web para soporte de fabricación
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS total_orden FLOAT",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS abono_porcentaje INTEGER DEFAULT 100",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS tiene_fabricacion BOOLEAN DEFAULT FALSE",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS tipo_entrega VARCHAR(20) DEFAULT 'completa'",
            # Columna ABONO en facturas (por si no existe)
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS total_abonado FLOAT",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS saldo_pendiente FLOAT DEFAULT 0",
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

_auto_migrate()


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
    app.run(debug=True, host='0.0.0.0', port=5000)
