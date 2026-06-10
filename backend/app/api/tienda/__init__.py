"""
Blueprint de la tienda online (RALOZ COL SAS).

Dividido en módulos para separar responsabilidades:
  - publico.py → endpoints públicos (catálogo, reservas, pedido, webhook MP)
  - admin.py   → endpoints de administración (pedidos y fabricación)
La lógica de negocio vive en app/services/facturacion_web.py.

El blueprint conserva el nombre 'tienda' y el prefijo /api/tienda, así que las
rutas NO cambian para la tienda pública, el panel admin ni MercadoPago.
"""
from flask import Blueprint

tienda_bp = Blueprint('tienda', __name__)

# Importar los módulos de rutas DESPUÉS de crear el blueprint para que registren
# sus endpoints. Ellos hacen `from app.api.tienda import tienda_bp`, que ya está
# definido en este punto (evita el import circular).
from app.api.tienda import publico  # noqa: E402,F401
from app.api.tienda import admin    # noqa: E402,F401
