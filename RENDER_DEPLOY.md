# Desplegar RALOZ en Render — Guía Rápida

## Lo que se despliega
- **Web Service**: `raloz-web` — Backend Flask (Python) + Frontend React servido desde el backend
- **PostgreSQL**: `raloz-db` — Base de datos gratis en Render

---

## Pasos

### 1. Subir el código a GitHub
El proyecto necesita estar en un repositorio de GitHub para que Render lo lea.

Si ya tienes git:
```
git init
git add .
git commit -m "RALOZ COL SAS - deploy Render"
git remote add origin https://github.com/TU_USUARIO/raloz-web.git
git push -u origin main
```

### 2. Crear el servicio en Render con Blueprint
1. Ve a [render.com](https://render.com) e inicia sesión
2. Click en **New +** → **Blueprint**
3. Conecta tu repositorio de GitHub donde subiste el proyecto
4. Render leerá el `render.yaml` y creará automáticamente:
   - El Web Service `raloz-web`
   - La base de datos `raloz-db`
5. Click **Apply**

### 3. Variables de entorno (opcionales)
Después del deploy, en el Web Service → **Environment**:
- `GOOGLE_CLIENT_ID` — Solo si usas login con Google
- `VITE_GOOGLE_CLIENT_ID` — El mismo valor que el anterior

`SECRET_KEY` y `JWT_SECRET_KEY` se generan solos (el render.yaml los configura con `generateValue: true`).
`DATABASE_URL` se configura solo desde la base de datos `raloz-db`.

### 4. Primer arranque
Al arrancar por primera vez, el backend crea las tablas y el usuario admin:
- **Usuario**: `admin`
- **Contraseña**: `admin123`
- ⚠️ Cámbiala desde la app después de entrar

---

## Si ya tienes el servicio `raloz-web` creado manualmente en Render

En lugar del Blueprint, configura el servicio existente así:

**Build Command:**
```
bash build.sh
```

**Start Command:**
```
cd backend && gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

**Environment Variables** (agregar en el dashboard):
| Variable | Valor |
|---|---|
| `DATABASE_URL` | Connection string de tu PostgreSQL en Render |
| `SECRET_KEY` | (genera uno con: `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `JWT_SECRET_KEY` | (genera otro igual) |

Y crea la base de datos desde **New + → PostgreSQL** con nombre `raloz-db`.
Luego copia el **Internal Database URL** y pégalo en `DATABASE_URL` del web service.

---

## URL final
Tu app quedará en: `https://raloz-web.onrender.com`
