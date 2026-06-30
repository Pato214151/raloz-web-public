"""
RALOZ COL SAS - Migración de CORRECCIÓN COMPLETA
Agrega campos faltantes a facturas, clientes, usuarios,
crea tablas prendas_pendientes, empaque_pendientes, series_remision,
migra todos los datos.

Uso:
    python scripts/ejecutar_fix.py https://raloz-web.onrender.com
"""

import json
import urllib.request
import urllib.error
import sys
import os
import time

MIGRATION_KEY = os.getenv('MIGRATION_KEY', 'raloz-migracion-2026-temporal')
BATCH_SIZE = 50


def send_batch(base_url, statements, batch_name, batch_num, total_batches):
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
                    print(f"    ! {e}")
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ''
        print(f"  X HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  X Error: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/ejecutar_fix.py <URL_RENDER>")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/')
    print(f"\n{'='*60}")
    print(f"  RALOZ COL SAS - Migracion COMPLETA de Correccion")
    print(f"  Servidor: {base_url}")
    print(f"{'='*60}\n")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'migration_fix.json')

    if not os.path.exists(json_path):
        print(f"X No se encontro {json_path}")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        batches = json.load(f)

    # Verify connection
    print("Verificando conexion...")
    try:
        req = urllib.request.Request(f"{base_url}/api/health")
        with urllib.request.urlopen(req, timeout=30) as resp:
            health = json.loads(resp.read().decode('utf-8'))
            print(f"  OK Servidor: {health.get('app', '?')}\n")
    except Exception as e:
        print(f"  X No se puede conectar: {e}")
        sys.exit(1)

    # Orden de ejecución (primero ALTERs, luego CREATEs, luego INSERTs/UPDATEs)
    orden = [
        'alter_facturas',
        'alter_clientes',
        'alter_usuarios',
        'update_facturas',
        'update_clientes',
        'create_prendas',
        'insert_prendas',
        'create_empaque',
        'create_series_remision',
        'insert_series_remision',
        'fix_sequences',
        'create_indexes',
    ]

    total_batches = 0
    for tabla in orden:
        stmts = batches.get(tabla, [])
        total_batches += max(1, (len(stmts) + BATCH_SIZE - 1) // BATCH_SIZE) if stmts else 0

    batch_num = 0
    inicio = time.time()
    total_ok = 0
    total_err = 0

    for tabla in orden:
        stmts = batches.get(tabla, [])
        if not stmts:
            continue

        print(f"\n-- {tabla.upper()} ({len(stmts)} statements) --")

        for i in range(0, len(stmts), BATCH_SIZE):
            chunk = stmts[i:i+BATCH_SIZE]
            batch_num += 1
            result = send_batch(base_url, chunk, tabla, batch_num, total_batches)
            if result:
                total_ok += result.get('ejecutados', 0)
                total_err += result.get('errores_count', 0)
            time.sleep(0.5)

    elapsed = time.time() - inicio
    print(f"\n{'='*60}")
    print(f"  Correccion completada en {elapsed:.1f} segundos")
    print(f"  Total ejecutados: {total_ok}")
    print(f"  Total errores: {total_err}")
    print(f"{'='*60}")

    # Verificar
    print("\nVerificando tablas...")
    try:
        req = urllib.request.Request(f"{base_url}/api/migracion/verificar")
        req.add_header('X-Migration-Key', MIGRATION_KEY)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for table, count in data.get('tablas', {}).items():
                print(f"  {table}: {count} registros")
    except Exception as e:
        print(f"  No se pudo verificar: {e}")

    print()


if __name__ == '__main__':
    main()
