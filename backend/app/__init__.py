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

    # ── Guard de secretos ──
    # Si se está corriendo con los valores 'dev' por defecto (falta el env en
    # Render), avisar FUERTE en los logs. No rompe el arranque, pero deja
    # rastro claro de una configuración insegura.
    if app.config['SECRET_KEY'] == 'dev-secret-key-cambiar':
        logger.critical('[SEGURIDAD] SECRET_KEY usa el valor por defecto — configúralo en el entorno')
    if app.config['JWT_SECRET_KEY'] == 'jwt-dev-secret-cambiar':
        logger.critical('[SEGURIDAD] JWT_SECRET_KEY usa el valor por defecto — configúralo en el entorno')

    # ── Inicializar extensiones ──
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    # CORS — orígenes permitidos. Por seguridad NUNCA usamos '*' junto con
    # supports_credentials (es inválido y peligroso). Si CORS_ORIGINS no está
    # configurado, caemos a una lista segura conocida.
    _cors_defaults = [
        "https://ralozcol-web.pages.dev",   # tienda pública (Cloudflare)
        "https://raloz-web.onrender.com",   # panel admin (mismo backend)
        "http://localhost:5173",            # frontend dev (Vite)
        "http://localhost:3000",
        "http://localhost:8080",            # tienda local
    ]
    _cors_raw = os.getenv('CORS_ORIGINS', '').strip()
    if _cors_raw and _cors_raw != '*':
        cors_origins = [o.strip().rstrip('/') for o in _cors_raw.split(',') if o.strip()]
        for d in _cors_defaults:
            if d not in cors_origins:
                cors_origins.append(d)
    else:
        cors_origins = _cors_defaults
    CORS(app, resources={r"/api/*": {"origins": cors_origins}}, supports_credentials=True)

    # ── Security Headers ──
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # HSTS: fuerza HTTPS en el navegador (Render sirve siempre por HTTPS)
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # CSP en modo ENFORCE. Verificado contra el panel React + Google OAuth:
        # el build no tiene scripts inline (solo el módulo desde 'self'); la única
        # dependencia externa es accounts.google.com (GSI). 'unsafe-inline' en
        # style-src cubre los estilos en línea de React/Tailwind y del botón GSI.
        # Si algo del panel se rompiera, volver a 'Content-Security-Policy-Report-Only'.
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' https://accounts.google.com https://apis.google.com; "
            "style-src 'self' 'unsafe-inline' https://accounts.google.com https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self' https://accounts.google.com; "
            "frame-src https://accounts.google.com; "
            "frame-ancestors 'none'"
        )
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

    # ── Lista negra: ¿este token fue revocado (logout)? ──
    @jwt.token_in_blocklist_loader
    def token_revocado_loader(jwt_header, jwt_payload):
        from app.models.token_revocado import TokenRevocado
        jti = jwt_payload.get('jti')
        if not jti:
            return False
        return db.session.query(TokenRevocado.id).filter_by(jti=jti).first() is not None

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
    # [ARCHIVED] from app.api.pendientes import pendientes_bp  # ahora usa prendas_bp
    from app.api.reportes import reportes_bp
    from app.api.usuarios import usuarios_bp
    from app.api.dashboard import dashboard_bp
    from app.api.prendas_pendientes import prendas_bp
    from app.api.operaciones import operaciones_bp
    from app.api.precios import precios_bp
    from app.api.empaque import empaque_bp
    from app.api.ventas import ventas_bp
    from app.api.metodos_pago import metodos_pago_bp
    from app.api.tareas import tareas_bp
    from app.api.tienda import tienda_bp
    from app.api.ordenes_produccion import ordenes_produccion_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(facturas_bp, url_prefix='/api/facturas')
    app.register_blueprint(pagos_bp, url_prefix='/api/pagos')
    app.register_blueprint(stock_bp, url_prefix='/api/stock')
    app.register_blueprint(productos_bp, url_prefix='/api/productos')
    app.register_blueprint(colegios_bp, url_prefix='/api/colegios')
    app.register_blueprint(clientes_bp, url_prefix='/api/clientes')
    app.register_blueprint(gastos_bp, url_prefix='/api/gastos')
    app.register_blueprint(caja_bp, url_prefix='/api/caja')
    # [ARCHIVED] app.register_blueprint(pendientes_bp, url_prefix='/api/pendientes')  # ahora usa prendas_bp
    app.register_blueprint(reportes_bp, url_prefix='/api/reportes')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(prendas_bp, url_prefix='/api/prendas')
    app.register_blueprint(operaciones_bp, url_prefix='/api/operaciones')
    app.register_blueprint(precios_bp, url_prefix='/api/precios')
    app.register_blueprint(empaque_bp, url_prefix='/api/empaque')
    app.register_blueprint(ventas_bp, url_prefix='/api/ventas')
    app.register_blueprint(metodos_pago_bp, url_prefix='/api/metodos-pago')
    app.register_blueprint(tareas_bp, url_prefix='/api/tareas')
    app.register_blueprint(tienda_bp, url_prefix='/api/tienda')
    app.register_blueprint(ordenes_produccion_bp, url_prefix='/api/ordenes-produccion')

    # ── Config de conexión (timeout de red explícito a Supabase) ──
    # pool_pre_ping ya está activo; connect_args agrega timeout de red.
    # NOTA: todas las migraciones automáticas viven ahora en run.py (_auto_migrate),
    # en un solo lugar, para no duplicarlas ni que diverjan.
    app.config['SQLALCHEMY_ENGINE_OPTIONS'].setdefault('connect_args', {}).update({
        'connect_timeout': 10,  # máx 10 s esperando conexión TCP a Supabase
    })

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
