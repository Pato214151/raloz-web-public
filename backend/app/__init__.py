"""
RALOZ COL SAS - Backend Web API
Flask Application Factory
"""

from flask import Flask, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import logging
from dotenv import load_dotenv
from datetime import timedelta

logger = logging.getLogger(__name__)

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute"])


def create_app(config_name=None):
    """Application Factory"""
    app = Flask(__name__)

    # ── Configuración ──
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-cambiar')

    # Database — psycopg v3 (soporta postgres:// de Render y postgresql:// de Supabase)
    db_url = os.getenv('DATABASE_URL', 'sqlite:///raloz_dev.db')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_size': 5,
        'max_overflow': 10,
        'pool_recycle': 300,  # Recicla conexiones cada 5 min — evita SSL stale en Supabase/Render
    }

    # JWT Config
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret-cambiar')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']

    # ── Inicializar extensiones ──
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    # CORS — lee CORS_ORIGINS del env (separados por coma) o permite todo
    _cors_raw = os.getenv('CORS_ORIGINS', '*')
    if _cors_raw.strip() == '*':
        cors_origins = '*'
    else:
        cors_origins = [o.strip().rstrip('/') for o in _cors_raw.split(',') if o.strip()]
        cors_origins += ["http://localhost:5173", "http://localhost:3000"]
    CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)

    # ── Security Headers ──
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # ── JWT Error Handlers (sin hooks, sin callbacks) ──
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token expirado', 'code': 'token_expired'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({'error': 'Token inválido', 'code': 'token_invalid'}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({'error': 'Token requerido', 'code': 'token_missing'}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({'error': 'Token revocado', 'code': 'token_revoked'}), 401

    # ── Registrar Blueprints ──
    from app.api.auth import auth_bp
    from app.api.facturas import facturas_bp
    from app.api.pagos import pagos_bp
    from app.api.stock import stock_bp
    from app.api.productos import productos_bp
    from app.api.colegios import colegios_bp
    from app.api.clientes import clientes_bp
    from app.api.gastos import gastos_bp
    from app.api.caja import caja_bp
    from app.api.pendientes import pendientes_bp
    from app.api.reportes import reportes_bp
    from app.api.usuarios import usuarios_bp
    from app.api.dashboard import dashboard_bp
    from app.api.migracion import migracion_bp
    from app.api.prendas_pendientes import prendas_bp
    from app.api.precios import precios_bp
    from app.api.empaque import empaque_bp
    from app.api.ventas import ventas_bp
    from app.api.metodos_pago import metodos_pago_bp
    from app.api.tareas import tareas_bp
    from app.api.public import public_bp
    from app.api.tienda import tienda_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(facturas_bp, url_prefix='/api/facturas')
    app.register_blueprint(pagos_bp, url_prefix='/api/pagos')
    app.register_blueprint(stock_bp, url_prefix='/api/stock')
    app.register_blueprint(productos_bp, url_prefix='/api/productos')
    app.register_blueprint(colegios_bp, url_prefix='/api/colegios')
    app.register_blueprint(clientes_bp, url_prefix='/api/clientes')
    app.register_blueprint(gastos_bp, url_prefix='/api/gastos')
    app.register_blueprint(caja_bp, url_prefix='/api/caja')
    app.register_blueprint(pendientes_bp, url_prefix='/api/pendientes')
    app.register_blueprint(reportes_bp, url_prefix='/api/reportes')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(migracion_bp, url_prefix='/api/migracion')
    app.register_blueprint(prendas_bp, url_prefix='/api/prendas')
    app.register_blueprint(precios_bp, url_prefix='/api/precios')
    app.register_blueprint(empaque_bp, url_prefix='/api/empaque')
    app.register_blueprint(ventas_bp, url_prefix='/api/ventas')
    app.register_blueprint(metodos_pago_bp, url_prefix='/api/metodos-pago')
    app.register_blueprint(tareas_bp, url_prefix='/api/tareas')
    app.register_blueprint(public_bp, url_prefix='/api/public')
    app.register_blueprint(tienda_bp, url_prefix='/api/tienda')

    # ── Migraciones automáticas al arrancar ──
    with app.app_context():
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE facturas ADD COLUMN IF NOT EXISTS canal VARCHAR(20) DEFAULT 'PRESENCIAL'"
                ))
                conn.execute(text(
                    "ALTER TABLE gastos ADD COLUMN IF NOT EXISTS tipo_gasto VARCHAR(20) DEFAULT 'TIENDA'"
                ))
                conn.execute(text(
                    "ALTER TABLE tareas ADD COLUMN IF NOT EXISTS prioridad VARCHAR(10) DEFAULT 'MEDIA'"
                ))
                conn.execute(text(
                    "UPDATE tareas SET prioridad = 'MEDIA' WHERE prioridad IS NULL"
                ))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS caja_diaria (
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
                    )
                """))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS movimientos_caja (
                        id_movimiento SERIAL PRIMARY KEY,
                        id_caja       INTEGER NOT NULL REFERENCES caja_diaria(id_caja),
                        tipo          VARCHAR(50) NOT NULL,
                        concepto      VARCHAR(500),
                        valor         FLOAT NOT NULL,
                        metodo_pago   VARCHAR(50),
                        referencia    VARCHAR(200),
                        usuario       VARCHAR(100) NOT NULL,
                        fecha_hora    TIMESTAMP DEFAULT NOW()
                    )
                """))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS idx_movimientos_caja ON movimientos_caja(id_caja)"
                ))
                conn.commit()
        except Exception as e:
            logger.error('[INIT] Error en migración automática: %s', str(e), exc_info=True)

    # ── Health check ──
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'app': 'RALOZ COL SAS', 'version': '1.0.0-beta'}

    # ══════════════════════════════════════════════════════════
    # Servir frontend React en producción
    # El build de React (npm run build) genera archivos en ../frontend/dist
    # Flask los sirve como archivos estáticos
    # ══════════════════════════════════════════════════════════
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'frontend', 'dist')
    frontend_dir = os.path.abspath(frontend_dir)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Servir frontend React — archivos estáticos + SPA fallback"""
        # Si es una ruta /api, no llegó aquí (blueprints la manejan)
        # Si existe el archivo estático, servirlo
        file_path = os.path.join(frontend_dir, path)
        if path and os.path.isfile(file_path):
            return send_from_directory(frontend_dir, path)
        # Para cualquier otra ruta, servir index.html (SPA)
        index_path = os.path.join(frontend_dir, 'index.html')
        if os.path.isfile(index_path):
            return send_from_directory(frontend_dir, 'index.html')
        # En desarrollo sin build, retornar info
        return jsonify({
            'message': 'RALOZ COL SAS API activa',
            'nota': 'Frontend no encontrado. En desarrollo usa: npm run dev',
            'api_health': '/api/health',
        })

    return app
