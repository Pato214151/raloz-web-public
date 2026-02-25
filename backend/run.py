"""
RALOZ COL SAS - Entry Point
"""

from app import create_app, db
from app.models import *

app = create_app()


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
