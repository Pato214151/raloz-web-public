#!/usr/bin/env bash
# ══════════════════════════════════════════
# RALOZ COL SAS — Build script para Render
# ══════════════════════════════════════════
set -o errexit  # Salir si hay error

echo "══════════════════════════════════════"
echo "  RALOZ COL SAS — Build para Render"
echo "══════════════════════════════════════"

# 1. Instalar dependencias Python
echo ""
echo "→ Instalando dependencias Python..."
cd backend
pip install --upgrade pip
pip install -r requirements.txt

# 2. Crear tablas + datos iniciales (con manejo de error si DB no está lista)
echo ""
echo "→ Inicializando base de datos..."
export FLASK_APP=run.py
if python -m flask init-db 2>/dev/null; then
  python -m flask seed 2>/dev/null || echo "  ℹ️  Seed omitido (datos ya existen o DB no disponible)"
  echo "  ✓ Base de datos lista"
else
  echo "  ⚠️  DB no disponible en build — se inicializará al primer arranque"
fi

# 3. Construir frontend React
echo ""
echo "→ Construyendo frontend React..."
cd ../frontend
npm install

# Pasar variables de entorno de Render al build de Vite
echo "VITE_API_URL=/api" > .env.production
if [ -n "$VITE_GOOGLE_CLIENT_ID" ]; then
  echo "VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID" >> .env.production
  echo "  ✓ Google OAuth Client ID configurado"
fi

npm run build

echo ""
echo "══════════════════════════════════════"
echo "  ✅ Build completado exitosamente"
echo "══════════════════════════════════════"
