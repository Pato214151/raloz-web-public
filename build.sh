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

# 2. Crear tablas + datos iniciales
echo ""
echo "→ Creando tablas en base de datos..."
export FLASK_APP=run.py
python -m flask init-db
python -m flask seed

# 3. Construir frontend React
echo ""
echo "→ Construyendo frontend React..."
cd ../frontend
npm install
npm run build

echo ""
echo "══════════════════════════════════════"
echo "  ✅ Build completado exitosamente"
echo "══════════════════════════════════════"
