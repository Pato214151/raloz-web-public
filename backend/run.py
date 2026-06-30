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


# ─── Ducklab: latido de telemetría al portal (cada 3 min) ────────
# Reporta "online" + versión al portal Ducklab para el monitoreo en vivo y el
# dead-man switch. Se ACTIVA SOLO si DUCKLAB_API_KEY y DUCKLAB_TELEMETRY_URL
# están en el entorno (la API key NUNCA se hardcodea). Con varios workers de
# gunicorn, un advisory lock hace que solo uno mande el latido por ciclo.
def _job_telemetria_ducklab():
    import os
    import requests
    from sqlalchemy import text
    url = os.getenv('DUCKLAB_TELEMETRY_URL', '').strip()
    key = os.getenv('DUCKLAB_API_KEY', '').strip()
    if not url or not key:
        return  # telemetría desactivada
    version = os.getenv('APP_VERSION', '1.0.0')
    time.sleep(20)  # deja que la app arranque
    while True:
        try:
            with app.app_context():
                tengo_lock = db.session.execute(
                    text("SELECT pg_try_advisory_xact_lock(1003)")
                ).scalar()
                if tengo_lock:
                    requests.post(
                        url,
                        headers={'Authorization': f'Bearer {key}'},
                        json={'status': 'online', 'version': version},
                        timeout=10,
                    )
                db.session.commit()
        except Exception as e:
            logger.warning('[TELEMETRIA] %s', str(e)[:120])
        time.sleep(180)  # cada 3 min (< 5 min de "stale" en el portal)


threading.Thread(target=_job_telemetria_ducklab, daemon=True, name='ducklab-telemetria').start()


# ─── Migración automática versionada ─────────────────────────────
# Las migraciones viven en app/db_migrations.py: cada una tiene versión y
# queda registrada en la tabla schema_migrations (no se re-ejecutan, y un
# fallo se loguea fuerte en vez de tragarse silenciosamente).
def _auto_migrate():
    """Crea tablas nuevas y aplica las migraciones SQL pendientes."""
    with app.app_context():
        from app.db_migrations import aplicar_migraciones
        aplicar_migraciones()


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

        # Usuario admin por defecto.
        # SEGURIDAD: nunca sembrar un password conocido por defecto. Se toma de
        # ADMIN_PASSWORD; si no está, se genera uno aleatorio y se imprime UNA vez.
        import os
        import secrets
        admin = Usuario.query.filter_by(usuario='admin').first()
        if not admin:
            admin_pw = os.getenv('ADMIN_PASSWORD', '').strip()
            generada = not admin_pw
            if generada:
                admin_pw = secrets.token_urlsafe(12)
            salt = bcrypt.gensalt(rounds=12)
            hash_pw = bcrypt.hashpw(admin_pw.encode('utf-8'), salt).decode('utf-8')
            admin = Usuario(
                usuario='admin',
                email=os.getenv('ADMIN_EMAIL', 'admin@raloz.com'),
                contrasena_hash=hash_pw,
                rol='administrador',
            )
            db.session.add(admin)
            if generada:
                print(f"✓ Usuario admin creado con password ALEATORIO: {admin_pw}")
                print("  ⚠️  GUÁRDALO YA y cámbialo al primer ingreso (o define ADMIN_PASSWORD antes de sembrar).")
            else:
                print("✓ Usuario admin creado con el password de ADMIN_PASSWORD")
        else:
            print("ℹ️  Usuario admin ya existe")

        db.session.commit()
        print("\n✅ Datos iniciales insertados")


@app.cli.command('reset-admin-password')
def reset_admin_password():
    """
    Rota el password del usuario admin. Toma el nuevo valor de ADMIN_PASSWORD
    (env) o genera uno aleatorio y lo imprime una sola vez.
    Uso en Render:  ADMIN_PASSWORD='...' flask reset-admin-password
    """
    with app.app_context():
        import os
        import bcrypt
        import secrets
        admin = Usuario.query.filter_by(usuario='admin').first()
        if not admin:
            print("✗ No existe el usuario 'admin'. Corré primero: flask seed")
            return
        nueva = os.getenv('ADMIN_PASSWORD', '').strip()
        generada = not nueva
        if generada:
            nueva = secrets.token_urlsafe(12)
        salt = bcrypt.gensalt(rounds=12)
        admin.contrasena_hash = bcrypt.hashpw(nueva.encode('utf-8'), salt).decode('utf-8')
        admin.intentos_fallidos = 0
        admin.bloqueado_hasta = None
        db.session.commit()
        if generada:
            print(f"✓ Password de admin rotado. Nuevo password ALEATORIO: {nueva}")
            print("  ⚠️  Guardalo ya; no se vuelve a mostrar.")
        else:
            print("✓ Password de admin rotado al valor de ADMIN_PASSWORD.")


if __name__ == '__main__':
    import os
    # debug SOLO si FLASK_DEBUG=1 explícitamente. Nunca activar en producción:
    # con debug=True se expone la consola interactiva de Werkzeug (ejecución de
    # código remoto). En producción se usa gunicorn, no este bloque.
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host='127.0.0.1', port=5000)
