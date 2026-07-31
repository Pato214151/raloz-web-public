"""
Importa facturas históricas desde un CSV, REUTILIZANDO la lógica real de
creación de factura del backend (POST /api/facturas) — sin duplicar la
generación de consecutivos ni el descuento de stock.

⚠️  LO CORRE EL DUEÑO con su DATABASE_URL (con --commit escribe en la BD en vivo).

Cómo reutiliza el flujo normal: NO reimplementa nada. Levanta la app con
create_app(), mintea un JWT de un usuario administrador y hace POST a
/api/facturas con el test client. Así el consecutivo (SerieFacturacion), el
descuento de stock (registrar_movimiento), los precios autoritativos y la
auditoría los maneja el mismo endpoint de siempre.

CSV (con encabezado). Columnas:
    rn, fecha, colegio, cliente, telefono, direccion, items, abono, entregado
  - fecha:     YYYY-MM-DD  o  dd/mm/aaaa
  - colegio:   nombre (ej. "Marillac") o id numérico
  - items:     "producto_id:talla:cantidad:precio_unit" separados por ';'
               ej:  "5:10:2:41500;8:S:1:58000"
  - abono:     número (0 si nada)
  - entregado: true/false   (true = entrega inmediata → descuenta stock)
  - rn:        referencia de origen; se guarda en observaciones (NO es el consecutivo)

SEGURO POR DEFECTO (--dry-run): solo imprime qué crearía, no escribe nada.

  # 1) SIEMPRE backup primero
  python backup_db.py
  # 2) Previsualiza (no toca nada)
  DATABASE_URL="postgresql://..." python tools/importar_facturas_csv.py ventas.csv
  # 3) Si se ve bien, escribe de verdad
  DATABASE_URL="postgresql://..." python tools/importar_facturas_csv.py ventas.csv --commit
"""
import argparse
import csv
import re
import sys
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from app import create_app, db, limiter          # noqa: E402
from app.models import Factura, Colegio, Usuario  # noqa: E402
from flask_jwt_extended import create_access_token  # noqa: E402


# ─────────────────────────── Parsers puros ───────────────────────────

def norm_tel(t):
    """Deja solo dígitos y toma los últimos 10 (ignora +57 / espacios / guiones)."""
    d = re.sub(r'\D', '', t or '')
    return d[-10:] if len(d) >= 10 else d


def parse_fecha(s):
    s = (s or '').strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_items(s):
    """'pid:talla:cant:precio;pid:talla:cant:precio' -> lista de detalles."""
    detalles = []
    for parte in (s or '').split(';'):
        parte = parte.strip()
        if not parte:
            continue
        campos = parte.split(':')
        if len(campos) != 4:
            raise ValueError(f"item mal formado: {parte!r} (esperado pid:talla:cant:precio)")
        pid, talla, cant, precio = campos
        detalles.append({
            'id_producto': int(pid),
            'talla_individual': talla.strip(),
            'cantidad': int(cant),
            'precio_unitario': float(precio),
        })
    if not detalles:
        raise ValueError("sin items")
    return detalles


def resolver_colegio(valor, por_id, por_nombre):
    """Acepta id numérico o nombre (coincidencia parcial, sin distinguir mayúsculas)."""
    v = (valor or '').strip()
    if not v:
        raise ValueError("colegio vacío")
    if v.isdigit():
        idc = int(v)
        if idc in por_id:
            return idc
        raise ValueError(f"colegio id {idc} no existe")
    key = v.lower()
    for nombre, idc in por_nombre.items():
        if key in nombre or nombre in key:
            return idc
    raise ValueError(f"colegio {v!r} no encontrado")


def es_true(v):
    return str(v or '').strip().lower() in ('true', '1', 'si', 'sí', 'x', 'yes', 'y')


# ─────────────────────────────── Main ────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Importa facturas desde CSV reutilizando POST /api/facturas (dry-run por defecto)")
    ap.add_argument('csv', help="Ruta del CSV a importar")
    ap.add_argument('--commit', action='store_true',
                    help="Escribe de verdad. Sin esto es dry-run (no escribe nada).")
    ap.add_argument('--permitir-sobreventa', action='store_true',
                    help="Fuerza entrega inmediata aunque no haya stock (si no, esas filas fallan).")
    ap.add_argument('--dias', type=int, default=3,
                    help="Ventana ± días para detectar posibles duplicados (por defecto 3).")
    args = ap.parse_args()

    app = create_app()
    # La importación es una tanda controlada de un solo origen: sin rate-limit propio.
    try:
        limiter.enabled = False
    except Exception:
        pass

    with app.app_context():
        admin = Usuario.query.filter_by(rol='administrador').first()
        if not admin:
            print("✗ No hay ningún usuario administrador en la BD; no puedo importar.")
            sys.exit(1)

        # JWT igual al del login real: identity=str(id_usuario) + claims usuario/rol.
        token = create_access_token(
            identity=str(admin.id_usuario),
            additional_claims={'usuario': admin.usuario, 'rol': admin.rol},
        )
        auth = {'Authorization': f'Bearer {token}'}
        client = app.test_client()

        por_id = {c.id_colegio: c.nombre for c in Colegio.query.all()}
        por_nombre = {c.nombre.lower(): c.id_colegio for c in Colegio.query.all()}

        try:
            with open(args.csv, encoding='utf-8-sig', newline='') as f:
                filas = list(csv.DictReader(f))
        except OSError as e:
            print(f"✗ No pude abrir el CSV: {e}")
            sys.exit(1)

        modo = "COMMIT (escribe en la BD)" if args.commit else "DRY-RUN (no escribe nada)"
        print(f"\n=== Importar facturas · {modo} · {len(filas)} fila(s) ===")
        print(f"    Admin usado: {admin.usuario} · duplicados: ±{args.dias} días\n")

        creadas = duplicados = fallidas = 0
        fallos = []

        for i, fila in enumerate(filas, 1):
            rn = (fila.get('rn') or '').strip()
            etq = f"[fila {i}{(' rn=' + rn) if rn else ''}]"

            # 1) Parsear/validar la fila
            try:
                fecha = parse_fecha(fila.get('fecha'))
                if not fecha:
                    raise ValueError(f"fecha inválida: {fila.get('fecha')!r}")
                idc = resolver_colegio(fila.get('colegio'), por_id, por_nombre)
                cliente = (fila.get('cliente') or '').strip()
                if not cliente:
                    raise ValueError("cliente vacío")
                tel = (fila.get('telefono') or '').strip()
                direccion = (fila.get('direccion') or '').strip()
                detalles = parse_items(fila.get('items'))
                abono = float(fila.get('abono') or 0)
                entregado = es_true(fila.get('entregado'))
                total_csv = sum(d['cantidad'] * d['precio_unitario'] for d in detalles)
            except Exception as e:
                fallidas += 1
                fallos.append(f"{etq} datos inválidos: {e}")
                print(f"✗ {etq} FALLA (datos): {e}")
                continue

            # 2) Anti-duplicado: teléfono + colegio + total dentro de ±días
            desde, hasta = fecha - timedelta(days=args.dias), fecha + timedelta(days=args.dias)
            candidatas = Factura.query.filter(
                Factura.id_colegio == idc,
                Factura.fecha_factura >= desde,
                Factura.fecha_factura <= hasta,
            ).all()
            dup = next((f for f in candidatas
                        if norm_tel(f.cliente_telefono) == norm_tel(tel)
                        and abs(float(f.total or 0) - total_csv) <= 1.0), None)
            if dup:
                duplicados += 1
                print(f"⧗ {etq} POSIBLE DUPLICADO de {dup.numero_factura} "
                      f"({dup.fecha_factura}, ${float(dup.total or 0):,.0f}) → se salta")
                continue

            # 3) Payload para el endpoint real
            payload = {
                'id_colegio': idc,
                'cliente_nombre': cliente,
                'cliente_telefono': tel,
                'cliente_direccion': direccion,
                'fecha_factura': fecha.isoformat(),
                'abono': abono,
                'entrega_inmediata': entregado,
                'permitir_sobreventa': bool(args.permitir_sobreventa),
                'observaciones': f"Importado CSV rn={rn}" if rn else "Importado CSV",
                'detalles': detalles,
            }

            # 4) Dry-run: solo mostrar
            if not args.commit:
                creadas += 1
                ent = "entrega inmediata" if entregado else "por entregar"
                print(f"＋ {etq} CREARÍA: {cliente} · {por_id[idc]} · {len(detalles)} ítem(s) · "
                      f"${total_csv:,.0f} · abono ${abono:,.0f} · {ent}")
                continue

            # 5) Crear de verdad — MISMO endpoint que la app (consecutivo + stock)
            resp = client.post('/api/facturas', json=payload, headers=auth)
            if resp.status_code == 201:
                creadas += 1
                num = ((resp.get_json() or {}).get('factura') or {}).get('numero_factura', '?')
                print(f"✓ {etq} CREADA {num} · {cliente} · ${total_csv:,.0f}")
            else:
                fallidas += 1
                data = resp.get_json() or {}
                err = data.get('error', f"HTTP {resp.status_code}")
                if data.get('code') == 'sin_stock_suficiente':
                    err += " (usa --permitir-sobreventa si es histórico)"
                fallos.append(f"{etq} {err}")
                print(f"✗ {etq} FALLA ({resp.status_code}): {err}")
                db.session.rollback()  # deja la sesión limpia para la siguiente fila

        # 6) Resumen
        print("\n" + "=" * 52)
        print(f"RESUMEN · {modo}")
        print(f"  {'Se crearían' if not args.commit else 'Creadas'}: {creadas}")
        print(f"  Saltadas por posible duplicado: {duplicados}")
        print(f"  Fallidas: {fallidas}")
        for d in fallos:
            print(f"     - {d}")
        if not args.commit:
            print("\n(DRY-RUN: no se escribió nada. Repite con --commit para crear de verdad.)")


if __name__ == '__main__':
    main()
