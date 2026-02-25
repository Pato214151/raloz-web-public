"""
RALOZ COL SAS - Script de Migración
Envía datos desde el archivo JSON al servidor web (Render).
Solo necesita Python estándar (sin dependencias externas).

Uso:
    python scripts/ejecutar_migracion.py <URL_RENDER>

Ejemplo:
    python scripts/ejecutar_migracion.py https://tu-app.onrender.com
"""

import json
import urllib.request
import urllib.error
import sys
import os
import time

# ── Configuración ──
MIGRATION_KEY = os.getenv('MIGRATION_KEY', 'raloz-migracion-2026-temporal')
BATCH_SIZE = 100  # Enviar de a 100 statements por request


def send_batch(base_url, statements, batch_name, batch_num, total_batches):
    """Envía un lote de SQL statements al servidor"""
    url = f"{base_url}/api/migracion/ejecutar"
    data = json.dumps({'statements': statements}).encode('utf-8')

    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('X-Migration-Key', MIGRATION_KEY)

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            ok = result.get('ejecutados', 0)
            errs = result.get('errores_count', 0)
            print(f"  [{batch_num}/{total_batches}] {batch_name}: {ok} OK, {errs} errores")
            if errs > 0:
                for e in result.get('errores', [])[:5]:
                    print(f"    ⚠ {e}")
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        print(f"  ✗ HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def verificar(base_url):
    """Verifica los conteos después de migrar"""
    url = f"{base_url}/api/migracion/verificar"
    req = urllib.request.Request(url)
    req.add_header('X-Migration-Key', MIGRATION_KEY)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get('conteos', {})
    except Exception as e:
        print(f"Error verificando: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/ejecutar_migracion.py <URL_RENDER>")
        print("Ejemplo: python scripts/ejecutar_migracion.py https://tu-app.onrender.com")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/')
    print(f"\n{'='*60}")
    print(f"  RALOZ COL SAS - Migración de Datos")
    print(f"  Servidor: {base_url}")
    print(f"{'='*60}\n")

    # Cargar datos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'migration_data.json')

    if not os.path.exists(json_path):
        print(f"✗ No se encontró {json_path}")
        print("  Ejecuta primero el generador de datos.")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        batches = json.load(f)

    # Verificar conexión
    print("Verificando conexión...")
    try:
        req = urllib.request.Request(f"{base_url}/api/health")
        with urllib.request.urlopen(req, timeout=30) as resp:
            health = json.loads(resp.read().decode('utf-8'))
            print(f"  ✓ Servidor OK: {health.get('app', 'desconocido')}\n")
    except Exception as e:
        print(f"  ✗ No se puede conectar: {e}")
        sys.exit(1)

    # Orden de migración (respeta foreign keys)
    orden = [
        'colegios', 'productos', 'metodos_pago', 'series_facturacion',
        'precios_colegio', 'stock', 'clientes',
        'facturas', 'factura_detalle', 'pagos', 'gastos',
        'secuencias'
    ]

    total_stmts = sum(len(batches.get(t, [])) for t in orden)
    print(f"Total de registros a migrar: {total_stmts}\n")

    # Calcular total de batches
    total_batches = 0
    for tabla in orden:
        stmts = batches.get(tabla, [])
        total_batches += max(1, (len(stmts) + BATCH_SIZE - 1) // BATCH_SIZE) if stmts else 0

    batch_num = 0
    inicio = time.time()

    for tabla in orden:
        stmts = batches.get(tabla, [])
        if not stmts:
            continue

        print(f"\n── {tabla.upper()} ({len(stmts)} registros) ──")

        # Enviar en lotes
        for i in range(0, len(stmts), BATCH_SIZE):
            chunk = stmts[i:i+BATCH_SIZE]
            batch_num += 1
            result = send_batch(base_url, chunk, tabla, batch_num, total_batches)
            if result is None:
                print(f"  ⚠ Error en lote, continuando...")
            time.sleep(0.5)  # Pausa entre lotes

    elapsed = time.time() - inicio
    print(f"\n{'='*60}")
    print(f"  Migración completada en {elapsed:.1f} segundos")
    print(f"{'='*60}\n")

    # Verificar
    print("Verificando datos migrados...")
    conteos = verificar(base_url)
    if conteos:
        esperado = {
            'colegios': 3, 'productos': 18, 'metodos_pago': 5,
            'precios_colegio': 279, 'stock': 403, 'clientes': 215,
            'facturas': 284, 'factura_detalle': 1191, 'pagos': 357, 'gastos': 139
        }
        print(f"\n{'Tabla':<20} {'Esperado':>10} {'Migrado':>10} {'Estado':>10}")
        print("-" * 55)
        todo_ok = True
        for tabla, esp in esperado.items():
            mig = conteos.get(tabla, 0)
            estado = "✓ OK" if mig >= esp else "⚠ FALTAN"
            if mig < esp:
                todo_ok = False
            print(f"{tabla:<20} {esp:>10} {mig:>10} {estado:>10}")

        if todo_ok:
            print(f"\n✓ ¡Migración exitosa! Todos los datos fueron transferidos.")
        else:
            print(f"\n⚠ Algunos registros no se migraron. Revisa los errores arriba.")
    print()


if __name__ == '__main__':
    main()
