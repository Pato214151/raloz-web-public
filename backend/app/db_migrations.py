"""
Migraciones versionadas de la base de datos.

Reemplaza el antiguo sistema de SQL inline con try/except pass de run.py:
  - Cada migración tiene versión, descripción y lista de sentencias SQL.
  - La tabla schema_migrations registra qué versiones ya se aplicaron
    (historial consultable: SELECT * FROM schema_migrations ORDER BY version).
  - Una migración ya aplicada NUNCA se vuelve a ejecutar.
  - Si una migración falla, se hace rollback y se LANZA el error (visible en
    logs de Render) en vez de tragarlo silenciosamente.
  - Con varios workers de gunicorn, un advisory lock de PostgreSQL garantiza
    que solo uno migre a la vez; los demás esperan y luego ven todo aplicado.

Para agregar una migración: añadir un dict al final de MIGRACIONES con la
siguiente versión consecutiva. Usar SQL idempotente (IF NOT EXISTS /
ON CONFLICT DO NOTHING) cuando sea posible, por si hay que re-correrla a mano.

Las migraciones SQL son específicas de PostgreSQL (Supabase). En SQLite
(desarrollo local / tests) solo se ejecuta db.create_all().
"""

import logging
from datetime import datetime

from sqlalchemy import text

from app import db

logger = logging.getLogger(__name__)

# Lock para que solo un worker de gunicorn migre a la vez
_LOCK_MIGRACIONES = 1003

MIGRACIONES = [
    {
        'version': '0001',
        'descripcion': 'Renombrar pedidos_web.wompi_transaction_id → mp_preference_id',
        # tolerante: si falla (columna ya renombrada en despliegues anteriores)
        # se marca como aplicada y se continúa.
        'tolerante': True,
        'sql': [
            "ALTER TABLE pedidos_web RENAME COLUMN wompi_transaction_id TO mp_preference_id",
        ],
    },
    {
        'version': '0002',
        'descripcion': 'Columnas de fabricación y envío en pedidos_web',
        'sql': [
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS total_orden FLOAT",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS abono_porcentaje INTEGER DEFAULT 100",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS tiene_fabricacion BOOLEAN DEFAULT FALSE",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS tipo_entrega VARCHAR(20) DEFAULT 'completa'",
            "ALTER TABLE pedidos_web ADD COLUMN IF NOT EXISTS direccion_envio VARCHAR(300)",
        ],
    },
    {
        'version': '0003',
        'descripcion': 'Abono, saldo y estado de entrega en facturas',
        'sql': [
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS total_abonado FLOAT",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS saldo_pendiente FLOAT DEFAULT 0",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS estado_entrega VARCHAR(20) DEFAULT 'POR_ENTREGAR'",
            "UPDATE facturas SET estado_entrega = 'POR_ENTREGAR' WHERE estado_entrega IS NULL",
        ],
    },
    {
        'version': '0004',
        'descripcion': 'Columnas prefijo/formato/activa en series_facturacion',
        'sql': [
            "ALTER TABLE series_facturacion ADD COLUMN IF NOT EXISTS prefijo VARCHAR(10) DEFAULT 'FAC'",
            "ALTER TABLE series_facturacion ADD COLUMN IF NOT EXISTS formato VARCHAR(100) DEFAULT 'FAC-{ano}-{consecutivo:06d}'",
            "ALTER TABLE series_facturacion ADD COLUMN IF NOT EXISTS activa BOOLEAN DEFAULT TRUE",
            "UPDATE series_facturacion SET formato = 'FAC-{ano}-{consecutivo:06d}' WHERE formato IS NULL",
            "UPDATE series_facturacion SET prefijo = 'FAC' WHERE prefijo IS NULL",
            "UPDATE series_facturacion SET activa = TRUE WHERE activa IS NULL",
        ],
    },
    {
        'version': '0005',
        'descripcion': 'Índices para dashboard y reportes',
        'sql': [
            "CREATE INDEX IF NOT EXISTS idx_pagos_fecha ON pagos(fecha_pago)",
            "CREATE INDEX IF NOT EXISTS idx_pedidos_web_estado ON pedidos_web(estado)",
            "CREATE INDEX IF NOT EXISTS idx_pedidos_web_referencia ON pedidos_web(referencia)",
            "CREATE INDEX IF NOT EXISTS idx_facturas_estado_saldo ON facturas(estado, saldo_pendiente)",
        ],
    },
    {
        'version': '0006',
        'descripcion': 'Dirección en pedidos_fabricacion e idempotencia de pago de saldo',
        'sql': [
            "ALTER TABLE pedidos_fabricacion ADD COLUMN IF NOT EXISTS direccion_envio VARCHAR(300)",
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS mp_saldo_payment_id VARCHAR(50)",
        ],
    },
    {
        'version': '0007',
        'descripcion': 'Canal de venta en facturas, tipo de gasto y prioridad de tareas',
        'sql': [
            "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS canal VARCHAR(20) DEFAULT 'PRESENCIAL'",
            "ALTER TABLE gastos ADD COLUMN IF NOT EXISTS tipo_gasto VARCHAR(20) DEFAULT 'TIENDA'",
            "ALTER TABLE tareas ADD COLUMN IF NOT EXISTS prioridad VARCHAR(10) DEFAULT 'MEDIA'",
            "UPDATE tareas SET prioridad = 'MEDIA' WHERE prioridad IS NULL",
        ],
    },
    {
        'version': '0008',
        'descripcion': 'Tablas de caja diaria y movimientos de caja',
        'sql': [
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
        ],
    },
    {
        'version': '0009',
        'descripcion': 'Productos Ed. Física por género (19-22) y precios Manyanet',
        'sql': [
            "INSERT INTO productos (id_producto, codigo, nombre, tipo, activo) VALUES (19, 'CAMISETA-NINO', 'Camiseta Ed. Física Niño', 'Ed. Física Niño', true) ON CONFLICT DO NOTHING",
            "INSERT INTO productos (id_producto, codigo, nombre, tipo, activo) VALUES (20, 'CAMISETA-NINA', 'Camiseta Ed. Física Niña', 'Ed. Física Niña', true) ON CONFLICT DO NOTHING",
            "INSERT INTO productos (id_producto, codigo, nombre, tipo, activo) VALUES (21, 'CHQ-EDU-NINO', 'Chaqueta Ed. Física Niño', 'Ed. Física Niño', true) ON CONFLICT DO NOTHING",
            "INSERT INTO productos (id_producto, codigo, nombre, tipo, activo) VALUES (22, 'CHQ-EDU-NINA', 'Chaqueta Ed. Física Niña', 'Ed. Física Niña', true) ON CONFLICT DO NOTHING",
            "SELECT setval('productos_id_producto_seq', GREATEST(22, (SELECT MAX(id_producto) FROM productos)))",
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
        ],
    },
    {
        'version': '0010',
        'descripcion': 'Deudas en gastos: estado_pago + fecha_pago',
        'sql': [
            # 'PAGADO' (gasto normal) o 'PENDIENTE' (deuda aún no pagada).
            "ALTER TABLE gastos ADD COLUMN IF NOT EXISTS estado_pago VARCHAR(20) DEFAULT 'PAGADO'",
            "ALTER TABLE gastos ADD COLUMN IF NOT EXISTS fecha_pago DATE",
            "UPDATE gastos SET estado_pago = 'PAGADO' WHERE estado_pago IS NULL",
        ],
    },
    {
        'version': '0011',
        'descripcion': 'Tabla ordenes_produccion (órdenes de confección al taller)',
        'sql': [
            """
            CREATE TABLE IF NOT EXISTS ordenes_produccion (
                id_orden         SERIAL PRIMARY KEY,
                numero           INTEGER NOT NULL,
                prenda           VARCHAR(200) NOT NULL,
                id_colegio       INTEGER REFERENCES colegios(id_colegio),
                nombre_colegio   VARCHAR(200),
                taller           VARCHAR(200),
                fecha            TIMESTAMP DEFAULT NOW(),
                fecha_entrega    DATE,
                insumos_json     TEXT,
                tallas_json      TEXT,
                logo_descripcion VARCHAR(200),
                logo_ubicacion   VARCHAR(120),
                logo_tecnica     VARCHAR(80),
                logo_tamano      VARCHAR(60),
                observaciones    TEXT,
                costo_tela       FLOAT DEFAULT 0,
                costo_insumos    FLOAT DEFAULT 0,
                costo_mano_obra  FLOAT DEFAULT 0,
                estado           VARCHAR(30) DEFAULT 'creada',
                usuario_creacion VARCHAR(120),
                created_at       TIMESTAMP DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_ordprod_fecha ON ordenes_produccion(fecha)",
            "CREATE INDEX IF NOT EXISTS idx_ordprod_colegio ON ordenes_produccion(id_colegio)",
        ],
    },
    {
        'version': '0012',
        'descripcion': 'Bandeja de WhatsApp: conversaciones y mensajes (bot + humano)',
        'sql': [
            """
            CREATE TABLE IF NOT EXISTS wa_conversaciones (
                chat_id         VARCHAR(40) PRIMARY KEY,
                nombre          VARCHAR(160),
                ultimo_mensaje  TEXT,
                ultima_fecha    TIMESTAMP DEFAULT NOW(),
                no_leidos       INTEGER DEFAULT 0,
                modo            VARCHAR(10) DEFAULT 'bot'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS wa_mensajes (
                id_mensaje  SERIAL PRIMARY KEY,
                chat_id     VARCHAR(40) NOT NULL,
                direccion   VARCHAR(4) NOT NULL,
                texto       TEXT,
                autor       VARCHAR(120),
                fecha       TIMESTAMP DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_wamsg_chat ON wa_mensajes(chat_id, fecha)",
        ],
    },
    {
        'version': '0013',
        'descripcion': 'Tabla citas (agendamiento desde el bot de WhatsApp)',
        'sql': [
            """
            CREATE TABLE IF NOT EXISTS citas (
                id_cita   SERIAL PRIMARY KEY,
                chat_id   VARCHAR(40),
                nombre    VARCHAR(160),
                dia       VARCHAR(120),
                hora      VARCHAR(60),
                colegio   VARCHAR(120),
                estado    VARCHAR(20) DEFAULT 'pendiente',
                creada    TIMESTAMP DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_citas_estado ON citas(estado, creada)",
        ],
    },
    {
        'version': '0014',
        'descripcion': 'Soporte de imágenes/archivos en los mensajes de WhatsApp',
        'sql': [
            "ALTER TABLE wa_mensajes ADD COLUMN IF NOT EXISTS media_tipo VARCHAR(20)",
            "ALTER TABLE wa_mensajes ADD COLUMN IF NOT EXISTS media_b64 TEXT",
        ],
    },
    {
        'version': '0015',
        'descripcion': 'Tabla de leads capturados desde la tienda web',
        'sql': [
            "CREATE TABLE IF NOT EXISTS leads ("
            "  id_lead SERIAL PRIMARY KEY,"
            "  nombre VARCHAR(160),"
            "  telefono VARCHAR(40),"
            "  email VARCHAR(200),"
            "  mensaje TEXT,"
            "  estado VARCHAR(20) DEFAULT 'pendiente',"
            "  origen VARCHAR(20) DEFAULT 'web',"
            "  creada TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")",
            "CREATE INDEX IF NOT EXISTS idx_leads_estado ON leads(estado, creada)",
        ],
    },
    {
        'version': '0016',
        'descripcion': 'Publicaciones: destacar y ordenar productos en la tienda',
        'sql': [
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS destacado BOOLEAN DEFAULT FALSE",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS orden INTEGER DEFAULT 0",
        ],
    },
    {
        'version': '0017',
        'descripcion': 'Config del sitio (banner editable desde el panel)',
        'sql': [
            "CREATE TABLE IF NOT EXISTS config_sitio ("
            "  clave VARCHAR(60) PRIMARY KEY,"
            "  valor TEXT,"
            "  actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")",
            "INSERT INTO config_sitio (clave, valor) VALUES "
            "('banner_texto', 'Temporada 2026 — Uniformes en stock para Marillac, Adventista y Manyanet') "
            "ON CONFLICT (clave) DO NOTHING",
            "INSERT INTO config_sitio (clave, valor) VALUES ('banner_activo', '1') "
            "ON CONFLICT (clave) DO NOTHING",
        ],
    },
    {
        'version': '0018',
        'descripcion': 'Programar publicaciones por fecha (publicar_desde/hasta)',
        'sql': [
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS publicar_desde TIMESTAMP",
            "ALTER TABLE productos ADD COLUMN IF NOT EXISTS publicar_hasta TIMESTAMP",
        ],
    },
    {
        'version': '0019',
        'descripcion': 'Historial de avisos/campañas por WhatsApp',
        'sql': [
            "CREATE TABLE IF NOT EXISTS avisos ("
            "  id_aviso SERIAL PRIMARY KEY,"
            "  texto TEXT NOT NULL,"
            "  segmento VARCHAR(30),"
            "  total INTEGER DEFAULT 0,"
            "  enviados INTEGER DEFAULT 0,"
            "  fallidos INTEGER DEFAULT 0,"
            "  autor VARCHAR(80),"
            "  fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")",
        ],
    },
    {
        'version': '0020',
        'descripcion': 'Motor de reglas de automatización (Fase 3)',
        'sql': [
            "CREATE TABLE IF NOT EXISTS reglas_auto ("
            "  clave VARCHAR(50) PRIMARY KEY,"
            "  activa BOOLEAN DEFAULT FALSE,"
            "  config TEXT,"
            "  ultima_ejecucion TIMESTAMP"
            ")",
            "INSERT INTO reglas_auto (clave, activa, config) VALUES "
            "('alerta_stock_bajo', FALSE, '{\"umbral\": 5}') "
            "ON CONFLICT (clave) DO NOTHING",
        ],
    },
    {
        'version': '0021',
        'descripcion': 'Promociones/publicaciones libres para la portada',
        'sql': [
            "CREATE TABLE IF NOT EXISTS promociones ("
            "  id_promocion SERIAL PRIMARY KEY,"
            "  titulo VARCHAR(120) NOT NULL,"
            "  texto TEXT,"
            "  foto TEXT,"
            "  activa BOOLEAN DEFAULT TRUE,"
            "  orden INTEGER DEFAULT 0,"
            "  fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")",
        ],
    },
    {
        'version': '0022',
        'descripcion': 'Suscriptores con consentimiento (opt-in de la tienda)',
        'sql': [
            "CREATE TABLE IF NOT EXISTS suscriptores ("
            "  id_suscriptor SERIAL PRIMARY KEY,"
            "  telefono VARCHAR(40) UNIQUE NOT NULL,"
            "  nombre VARCHAR(160),"
            "  acepta_datos BOOLEAN DEFAULT TRUE,"
            "  activo BOOLEAN DEFAULT TRUE,"
            "  fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")",
        ],
    },
    {
        'version': '0023',
        'descripcion': 'Regla: devolver chats de modo humano a modo bot tras N horas',
        'sql': [
            "INSERT INTO reglas_auto (clave, activa, config) VALUES "
            "('volver_a_bot', TRUE, '{\"horas\": 12}') "
            "ON CONFLICT (clave) DO NOTHING",
        ],
    },
    {
        'version': '0024',
        'descripcion': 'Suscripciones Web Push del panel (notificaciones de WhatsApp)',
        'sql': [
            "CREATE TABLE IF NOT EXISTS push_subscriptions ("
            "  id SERIAL PRIMARY KEY,"
            "  endpoint TEXT UNIQUE NOT NULL,"
            "  p256dh TEXT NOT NULL,"
            "  auth TEXT NOT NULL,"
            "  usuario VARCHAR(80),"
            "  fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")",
        ],
    },
    {
        'version': '0025',
        'descripcion': 'Estado del bot de WhatsApp en la BD (bot integrado en el backend)',
        'sql': [
            "ALTER TABLE wa_conversaciones ADD COLUMN IF NOT EXISTS bot_estado VARCHAR(40) DEFAULT 'menu'",
            "ALTER TABLE wa_conversaciones ADD COLUMN IF NOT EXISTS bot_datos TEXT",
        ],
    },
    {
        'version': '0026',
        'descripcion': 'Gestión de la bandeja de WhatsApp: asignación, etiquetas y notas',
        'sql': [
            "ALTER TABLE wa_conversaciones ADD COLUMN IF NOT EXISTS asignado_a VARCHAR(120)",
            "ALTER TABLE wa_conversaciones ADD COLUMN IF NOT EXISTS etiquetas TEXT",
            "ALTER TABLE wa_conversaciones ADD COLUMN IF NOT EXISTS notas TEXT",
        ],
    },
    {
        'version': '0027',
        'descripcion': 'Costo unitario por precio (para margen y rentabilidad)',
        'sql': [
            "ALTER TABLE precios_colegio ADD COLUMN IF NOT EXISTS costo_unitario DOUBLE PRECISION",
        ],
    },
    {
        'version': '0028',
        'descripcion': 'Bitácora de acciones del Asistente (journal + rollback + verificación)',
        'sql': [
            """
            CREATE TABLE IF NOT EXISTS acciones_asistente (
                id_accion       SERIAL PRIMARY KEY,
                tipo            VARCHAR(40) NOT NULL,
                descripcion     VARCHAR(400),
                estado_antes    TEXT,
                estado_despues  TEXT,
                reversible      BOOLEAN NOT NULL DEFAULT FALSE,
                verificado      BOOLEAN NOT NULL DEFAULT FALSE,
                resultado       VARCHAR(30) NOT NULL DEFAULT 'EJECUTADA',
                reversion_de    INTEGER REFERENCES acciones_asistente(id_accion),
                usuario         VARCHAR(120),
                creado_en       TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_acciones_asistente_creado ON acciones_asistente(creado_en DESC)",
        ],
    },
    {
        'version': '0029',
        'descripcion': 'Event Engine: eventos del negocio detectados por el Observador',
        'sql': [
            """
            CREATE TABLE IF NOT EXISTS eventos (
                id_evento     SERIAL PRIMARY KEY,
                tipo          VARCHAR(50) NOT NULL,
                severidad     VARCHAR(15) NOT NULL DEFAULT 'INFORMATIVO',
                titulo        VARCHAR(200) NOT NULL,
                detalle       VARCHAR(500),
                entidad_tipo  VARCHAR(30),
                entidad_id    INTEGER,
                datos         TEXT,
                clave_dedup   VARCHAR(160) NOT NULL,
                estado        VARCHAR(15) NOT NULL DEFAULT 'NUEVO',
                creado_en     TIMESTAMP NOT NULL DEFAULT NOW(),
                visto_en      TIMESTAMP
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_eventos_dedup ON eventos(clave_dedup)",
            "CREATE INDEX IF NOT EXISTS idx_eventos_estado_sev ON eventos(estado, severidad)",
        ],
    },
    {
        'version': '0030',
        'descripcion': 'Análisis de eventos: score de prioridad y recomendación',
        'sql': [
            "ALTER TABLE eventos ADD COLUMN IF NOT EXISTS score INTEGER",
            "ALTER TABLE eventos ADD COLUMN IF NOT EXISTS recomendacion VARCHAR(500)",
        ],
    },
    {
        'version': '0031',
        'descripcion': 'Business Memory: reglas del negocio, decisiones y objetivos',
        'sql': [
            """
            CREATE TABLE IF NOT EXISTS reglas_negocio (
                id_regla    SERIAL PRIMARY KEY,
                categoria   VARCHAR(20) NOT NULL DEFAULT 'OTRA',
                texto       VARCHAR(400) NOT NULL,
                parametros  TEXT,
                activa      BOOLEAN NOT NULL DEFAULT TRUE,
                creado_por  VARCHAR(120),
                creado_en   TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS memoria_negocio (
                id_memoria  SERIAL PRIMARY KEY,
                tipo        VARCHAR(20) NOT NULL DEFAULT 'NOTA',
                texto       VARCHAR(500) NOT NULL,
                activa      BOOLEAN NOT NULL DEFAULT TRUE,
                creado_por  VARCHAR(120),
                creado_en   TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS objetivos (
                id_objetivo SERIAL PRIMARY KEY,
                tipo        VARCHAR(20) NOT NULL DEFAULT 'VENTAS',
                descripcion VARCHAR(200),
                meta        DOUBLE PRECISION NOT NULL,
                anio        INTEGER NOT NULL,
                mes         INTEGER,
                activa      BOOLEAN NOT NULL DEFAULT TRUE,
                creado_por  VARCHAR(120),
                creado_en   TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """,
        ],
    },
    {
        'version': '0032',
        'descripcion': 'Liquidación Adventista: precios de venta al 50% (contrato terminado)',
        'sql': [
            # Se aplica UNA sola vez. Por NOMBRE (no por id) para no tocar otros colegios.
            # Solo el precio de venta; el costo no se cambia.
            """
            UPDATE precios_colegio
               SET precio_unitario = ROUND(precio_unitario * 0.5)
             WHERE id_colegio IN (
                   SELECT id_colegio FROM colegios
                    WHERE LOWER(nombre) LIKE '%adventista%')
            """,
        ],
    },
]


def _asegurar_tabla_versiones():
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     VARCHAR(20) PRIMARY KEY,
            descripcion VARCHAR(300),
            aplicada_en TIMESTAMP NOT NULL
        )
    """))
    db.session.commit()


def _registrar_version(migracion):
    db.session.execute(
        text("INSERT INTO schema_migrations (version, descripcion, aplicada_en) "
             "VALUES (:v, :d, :f)"),
        {'v': migracion['version'], 'd': migracion['descripcion'], 'f': datetime.utcnow()},
    )


def _ejecutar_pendientes(migraciones):
    """
    Aplica en orden las migraciones cuya versión no esté en schema_migrations.
    Cada migración es una transacción: o se aplica completa y queda registrada,
    o se hace rollback y se lanza el error (salvo 'tolerante': True, que se
    registra como aplicada aunque falle — para casos como un RENAME ya hecho).
    """
    _asegurar_tabla_versiones()
    aplicadas = {
        r[0] for r in db.session.execute(text("SELECT version FROM schema_migrations")).fetchall()
    }

    for migracion in migraciones:
        version = migracion['version']
        if version in aplicadas:
            continue
        try:
            for sql in migracion['sql']:
                db.session.execute(text(sql))
            _registrar_version(migracion)
            db.session.commit()
            logger.info('[MIGRACION] %s aplicada — %s', version, migracion['descripcion'])
        except Exception as e:
            db.session.rollback()
            if migracion.get('tolerante'):
                _registrar_version(migracion)
                db.session.commit()
                logger.warning(
                    '[MIGRACION] %s falló pero es tolerante (se marca aplicada): %s',
                    version, str(e)[:200],
                )
            else:
                logger.error(
                    '[MIGRACION] FALLO en %s (%s): %s — la app NO aplicará las siguientes '
                    'migraciones hasta corregir esta.',
                    version, migracion['descripcion'], str(e)[:300],
                )
                raise


def aplicar_migraciones():
    """
    Punto de entrada en el arranque (run.py). Requiere app context activo.
    En PostgreSQL: crea tablas nuevas de los modelos y aplica las migraciones
    pendientes, serializado entre workers con un advisory lock.
    En SQLite (dev local / tests): solo db.create_all() — el SQL de las
    migraciones es específico de PostgreSQL.
    """
    db.create_all()  # tablas nuevas definidas en los modelos

    if db.engine.dialect.name != 'postgresql':
        logger.info('[MIGRACION] BD %s: solo create_all(), las migraciones SQL son de PostgreSQL',
                    db.engine.dialect.name)
        return

    # Lock dedicado en una conexión propia: con varios workers de gunicorn,
    # solo uno migra; los demás esperan aquí y luego encuentran todo aplicado.
    lock_conn = db.engine.connect()
    try:
        lock_conn.execute(text(f"SELECT pg_advisory_lock({_LOCK_MIGRACIONES})"))
        lock_conn.commit()
        _ejecutar_pendientes(MIGRACIONES)
    finally:
        try:
            lock_conn.execute(text(f"SELECT pg_advisory_unlock({_LOCK_MIGRACIONES})"))
            lock_conn.commit()
        finally:
            lock_conn.close()
