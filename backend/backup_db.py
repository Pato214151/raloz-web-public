"""
Respaldo (backup) de la base de datos RALOZ — en Python puro.

Guarda TODOS los datos de la base en un archivo .sql con fecha, dentro de
la carpeta "backups/". No necesitas instalar pg_dump ni nada extra: usa
psycopg (que ya viene con el backend).

USO:
    cd "sofware raloz/raloz-web/backend"
    python backup_db.py

El archivo queda en  backend/backups/raloz_backup_FECHA.sql
Guárdalo también en Google Drive / USB para estar 100% seguro.

Lee la conexión de DATABASE_URL (del archivo .env, igual que el backend).
"""

import os
import sys
import datetime
from pathlib import Path

# Para que la consola de Windows muestre acentos sin romperse
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import psycopg
from psycopg.sql import SQL, Identifier, Literal

AQUI = Path(__file__).parent


def leer_database_url() -> str:
    """Obtiene DATABASE_URL del entorno o del archivo .env (sin depender de dotenv)."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    env_file = AQUI / ".env"
    if env_file.exists():
        for linea in env_file.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea.startswith("DATABASE_URL="):
                return linea.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main():
    database_url = leer_database_url()
    if not database_url:
        print("ERROR: no encontre DATABASE_URL (ni en variables de entorno ni en .env)")
        sys.exit(1)

    # SQLAlchemy usa 'postgresql+psycopg://'; psycopg quiere 'postgresql://'
    dsn = database_url.replace("postgresql+psycopg://", "postgresql://")
    # Supabase exige SSL: lo agregamos si no esta
    if "sslmode=" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"

    out_dir = AQUI / "backups"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
    out_file = out_dir / f"raloz_backup_{stamp}.sql"

    print("Conectando a la base de datos...")
    try:
        conn = psycopg.connect(dsn, connect_timeout=20)
    except Exception as e:
        print(f"ERROR al conectar: {e}")
        sys.exit(1)

    total_filas = 0
    n_tablas = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
            )
            tablas = [r[0] for r in cur.fetchall()]

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"-- Respaldo RALOZ COL SAS  ({stamp})\n")
            f.write("-- Contiene SOLO datos (INSERTs). Para restaurar: arranca la app\n")
            f.write("-- (que crea las tablas) y luego ejecuta este archivo en la BD.\n")
            f.write("BEGIN;\n")

            for t in tablas:
                with conn.cursor() as cur:
                    cur.execute(SQL("SELECT * FROM {}").format(Identifier(t)))
                    cols = [d.name for d in cur.description]
                    filas = cur.fetchall()
                if not filas:
                    print(f"  {t}: 0 filas (vacia)")
                    continue
                f.write(f"\n-- Tabla: {t} ({len(filas)} filas)\n")
                col_sql = SQL(", ").join(Identifier(c) for c in cols)
                for row in filas:
                    vals = SQL(", ").join(Literal(v) for v in row)
                    stmt = SQL("INSERT INTO {} ({}) VALUES ({});").format(
                        Identifier(t), col_sql, vals
                    )
                    f.write(stmt.as_string(conn) + "\n")
                total_filas += len(filas)
                n_tablas += 1
                print(f"  {t}: {len(filas)} filas")

            f.write("\nCOMMIT;\n")
    finally:
        conn.close()

    tam_kb = out_file.stat().st_size / 1024
    print("\n========================================")
    print(f"  RESPALDO LISTO")
    print(f"  Tablas con datos: {n_tablas}")
    print(f"  Filas totales:    {total_filas}")
    print(f"  Tamano:           {tam_kb:.1f} KB")
    print(f"  Archivo:          {out_file}")
    print("========================================")
    print("Sugerencia: copia este archivo a Google Drive o un USB.")


if __name__ == "__main__":
    main()
