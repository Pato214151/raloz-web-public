# Tests

Pruebas automáticas del backend. Empiezan por las **rutas críticas** (las que
afectan dinero e inventario): conversión de tallas y validadores de entrada.

## Cómo correrlos

```bash
cd backend
pip install -r requirements-dev.txt   # solo la primera vez
pytest
```

## Qué se prueba hoy
- `test_tallas.py` — conversión talla individual ↔ grupo (base de precios y stock).
- `test_validators.py` — sanitización (anti-XSS), email, teléfono, fecha, números, campos requeridos.

## Próximos tests sugeridos
- Webhook de MercadoPago (idempotencia: que un pago no se procese dos veces).
- Cálculo del total del pedido desde la base de datos (precio server-side).
- Creación de factura desde un pedido pagado.
