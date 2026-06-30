"""
Chequeo de seguridad contra el backend EN VIVO (read-only, no modifica nada).
Verifica cada control de seguridad de producción y reporta PASA/FALLA.

Uso:
    python security_check.py
    BASE=https://raloz-web.onrender.com python security_check.py
"""
import os
import sys
import requests

try:
    sys.stdout.reconfigure(encoding='utf-8')  # consola de Windows (cp1252) → UTF-8
except Exception:
    pass

BASE = os.getenv('BASE', 'https://raloz-web.onrender.com').rstrip('/')
TIMEOUT = 30
ok = 0
fail = 0


def check(nombre, condicion, detalle=''):
    global ok, fail
    estado = 'PASA ' if condicion else 'FALLA'
    if condicion:
        ok += 1
    else:
        fail += 1
    print(f'  [{estado}] {nombre}' + (f'  ({detalle})' if detalle else ''))


def main():
    print(f'Chequeo de seguridad: {BASE}\n')

    # 1. El backend responde por HTTPS
    r = requests.get(f'{BASE}/api/health', timeout=120)  # 120 por cold start de Render
    check('Backend vivo (health 200)', r.status_code == 200, f'status {r.status_code}')
    h = r.headers

    # 2. Security headers
    print('\n Headers de seguridad:')
    check('X-Content-Type-Options: nosniff', h.get('X-Content-Type-Options') == 'nosniff')
    check('X-Frame-Options: DENY', h.get('X-Frame-Options') == 'DENY')
    check('Referrer-Policy presente', bool(h.get('Referrer-Policy')))
    check('HSTS (Strict-Transport-Security)', 'max-age' in (h.get('Strict-Transport-Security') or ''))
    csp = h.get('Content-Security-Policy')
    csp_ro = h.get('Content-Security-Policy-Report-Only')
    check('CSP en modo ENFORCE (no report-only)', bool(csp) and not csp_ro,
          'enforce' if csp else ('solo report-only' if csp_ro else 'sin CSP'))
    check("CSP bloquea frame-ancestors", "frame-ancestors 'none'" in (csp or ''))

    # 3. Webhook de MercadoPago rechaza pagos sin firma válida
    print('\n Webhook MercadoPago:')
    try:
        rw = requests.post(f'{BASE}/api/tienda/mp/webhook',
                           json={'type': 'payment', 'data': {'id': '999999'}}, timeout=TIMEOUT)
        firma_activa = rw.status_code == 401
    except Exception:
        firma_activa = False
    check('Rechaza webhook de pago sin firma (401)', firma_activa,
          'firma HMAC activa' if firma_activa else 'OJO: validación de firma desactivada')

    # 4. Endpoints admin exigen autenticación
    print('\n Autenticación de endpoints admin (deben dar 401 sin token):')
    admin_endpoints = [
        ('GET',  '/api/tienda/admin/pedidos'),
        ('GET',  '/api/tienda/admin/pedidos/conteo-nuevos'),
        ('POST', '/api/tienda/admin/pedidos/1/marcar-pagado'),
        ('GET',  '/api/tienda/admin/fabricacion/pedidos'),
        ('GET',  '/api/reportes/cuentas'),
        ('GET',  '/api/gastos'),
        ('POST', '/api/gastos/1/pagar'),
        ('GET',  '/api/usuarios'),
        ('GET',  '/api/stock'),
    ]
    for metodo, url in admin_endpoints:
        try:
            rr = requests.request(metodo, f'{BASE}{url}', timeout=TIMEOUT)
            check(f'{metodo} {url}', rr.status_code == 401, f'status {rr.status_code}')
        except Exception as e:
            check(f'{metodo} {url}', False, str(e)[:40])

    # 5. Login con credenciales inválidas no revela si el usuario existe
    print('\n Login:')
    try:
        rl = requests.post(f'{BASE}/api/auth/login',
                           json={'usuario': 'usuario_que_no_existe_xyz', 'password': 'x'}, timeout=TIMEOUT)
        check('Credenciales inválidas → 401 (sin filtrar info)', rl.status_code == 401, f'status {rl.status_code}')
    except Exception as e:
        check('Login', False, str(e)[:40])

    print(f'\n── Resultado: {ok} PASA · {fail} FALLA ──')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
