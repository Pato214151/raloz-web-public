# RALOZ WEB — Instrucciones Completas con Código

**Para:** Julián Ramírez
**Proyecto:** RALOZ COL SAS — Sistema Web de Facturación
**Repositorio:** github.com/Pato214151/raloz-web
**Despliegue:** https://raloz-web.onrender.com/

---

## PASO 1: Preparar tu computador

Antes de empezar, necesitas tener instalados estos programas. Si ya los tienes, pasa al Paso 2.

### 1.1 — Instalar Git

Descarga de: https://git-scm.com/download/win

Durante la instalación, acepta todas las opciones por defecto.

Verifica que funciona abriendo **PowerShell** o **CMD** y escribiendo:

```bash
git --version
```

Debería mostrar algo como: `git version 2.44.0`

### 1.2 — Instalar Node.js

Descarga de: https://nodejs.org/ (versión LTS, botón verde)

Verifica:

```bash
node --version
npm --version
```

### 1.3 — Instalar Python

Descarga de: https://www.python.org/downloads/

**MUY IMPORTANTE:** Durante la instalación, marca la casilla **"Add Python to PATH"**.

Verifica:

```bash
python --version
pip --version
```

---

## PASO 2: Clonar tu repositorio

Abre **PowerShell** como administrador y ejecuta estos comandos uno por uno:

```powershell
# Ir a tu carpeta de Documentos
cd C:\Users\julianr\Documents

# Clonar tu repositorio desde GitHub
git clone https://github.com/Pato214151/raloz-web.git

# Entrar a la carpeta del proyecto
cd raloz-web
```

Si ya tienes el repositorio clonado, en su lugar haz:

```powershell
# Ir a donde tengas el repositorio clonado
cd C:\Users\julianr\Documents\raloz-web

# Descargar los últimos cambios
git pull origin main
```

---

## PASO 3: Copiar los archivos actualizados

Ahora necesitas copiar los archivos actualizados del proyecto desde `RALOZ-Web` a tu repositorio clonado. Esto reemplazará los archivos viejos con los nuevos y mejorados.

```powershell
# Asegúrate de estar en el directorio correcto
cd C:\Users\julianr\Documents\raloz-web

# Copiar TODOS los archivos actualizados del backend
# (esto sobreescribe los archivos existentes y agrega los nuevos)
Copy-Item -Path "C:\Users\julianr\Documents\RALOZ-Web\backend\*" -Destination ".\backend\" -Recurse -Force

# Copiar TODOS los archivos actualizados del frontend
Copy-Item -Path "C:\Users\julianr\Documents\RALOZ-Web\frontend\src\*" -Destination ".\frontend\src\" -Recurse -Force

# Copiar archivos de la raíz actualizados
Copy-Item -Path "C:\Users\julianr\Documents\RALOZ-Web\build.sh" -Destination ".\" -Force
Copy-Item -Path "C:\Users\julianr\Documents\RALOZ-Web\render.yaml" -Destination ".\" -Force
Copy-Item -Path "C:\Users\julianr\Documents\RALOZ-Web\.gitignore" -Destination ".\" -Force
Copy-Item -Path "C:\Users\julianr\Documents\RALOZ-Web\GUIA_PASO_A_PASO.md" -Destination ".\" -Force
```

### Verificar que los archivos nuevos están ahí

```powershell
# Verificar los archivos nuevos del backend
dir backend\app\api\precios.py
dir backend\app\api\empaque.py
dir backend\app\api\ventas.py
dir backend\app\utils\tallas.py

# Verificar los archivos nuevos del frontend
dir frontend\src\components\precios\Precios.jsx
dir frontend\src\components\empaque\Empaque.jsx
```

Si todos los archivos aparecen sin error, los archivos se copiaron correctamente.

---

## PASO 4: Probar localmente (OPCIONAL pero RECOMENDADO)

### 4.1 — Configurar y ejecutar el Backend

Abrir una ventana de **PowerShell**:

```powershell
# Ir a la carpeta del backend
cd C:\Users\julianr\Documents\raloz-web\backend

# Crear entorno virtual de Python (solo la primera vez)
python -m venv venv

# Activar el entorno virtual
.\venv\Scripts\Activate

# Instalar dependencias (dentro del entorno virtual)
pip install -r requirements.txt
```

Ahora crea el archivo `.env` para desarrollo local:

```powershell
# Crear archivo .env para pruebas locales
@"
FLASK_ENV=development
SECRET_KEY=clave-local-de-prueba-123456789
JWT_SECRET_KEY=jwt-local-de-prueba-987654321
DATABASE_URL=sqlite:///raloz_dev.db
CORS_ORIGINS=http://localhost:5173
"@ | Out-File -FilePath .env -Encoding utf8
```

Crear las tablas e iniciar:

```powershell
# Crear las tablas en la base de datos local
$env:FLASK_APP = "run.py"
python -m flask init-db
python -m flask seed

# Iniciar el servidor backend
python run.py
```

Deberías ver: `Running on http://127.0.0.1:5000`

Abre tu navegador y visita: `http://localhost:5000/api/health`
Deberías ver: `{"status": "ok", "app": "RALOZ COL SAS", "version": "1.0.0-beta"}`

### 4.2 — Configurar y ejecutar el Frontend

Abre **OTRA** ventana de PowerShell (deja el backend corriendo):

```powershell
# Ir a la carpeta del frontend
cd C:\Users\julianr\Documents\raloz-web\frontend

# Instalar dependencias (solo la primera vez)
npm install

# Crear archivo de entorno para desarrollo
@"
VITE_API_URL=http://localhost:5000/api
"@ | Out-File -FilePath .env -Encoding utf8

# Iniciar el frontend en modo desarrollo
npm run dev
```

Deberías ver: `Local: http://localhost:5173/`

Abre tu navegador y visita: `http://localhost:5173`
Deberías ver la pantalla de login. Ingresa con: `admin` / `admin123`

### 4.3 — Verificar cada módulo funciona

Una vez logueado, navega a cada sección del sidebar y verifica que no haya errores:

1. **Dashboard** — debe mostrar los KPIs (estarán en $0 porque no hay datos)
2. **Nueva Venta** — debe mostrar el formulario de facturación
3. **Buscar Facturas** — debe mostrar el buscador con filtros
4. **Pagos** — debe mostrar el buscador de facturas para pago
5. **Inventario** — debe mostrar la vista de stock
6. **Hoja de Ventas** — debe mostrar los filtros de fecha y las tablas
7. **Empaque** — debe mostrar el buscador de facturas para empaque
8. **Precios** — debe mostrar selector de colegio y tabla de precios
9. **Reportes** — debe mostrar las gráficas y filtros
10. **Clientes** — debe mostrar la lista de clientes
11. **Gastos** — debe mostrar el formulario de gastos
12. **Caja** — debe mostrar apertura/cierre de caja
13. **Pendientes** — debe mostrar las prendas pendientes
14. **Usuarios** — debe mostrar la lista de usuarios

Para detener los servidores locales, presiona `Ctrl + C` en cada ventana de PowerShell.

---

## PASO 5: Subir los cambios a GitHub

Este es el paso más importante. Después de verificar que todo funciona localmente (o si confías en que está correcto), sube los cambios:

```powershell
# Ir a la raíz del proyecto
cd C:\Users\julianr\Documents\raloz-web

# Ver qué archivos cambiaron
git status

# Agregar TODOS los archivos nuevos y modificados
git add .

# Verificar qué se va a subir
git status
```

Deberías ver en verde los archivos nuevos/modificados. Verifica que NO incluya archivos `.env` o `.db` (el .gitignore los excluye automáticamente).

Ahora crea el commit y súbelo:

```powershell
# Crear commit con mensaje descriptivo
git commit -m "Rebuild completo: nuevos modulos precios, empaque, ventas, pendientes mejorado, facturacion con auto-precios"

# Subir a GitHub
git push origin main
```

Si te pide usuario y contraseña:
- **Username:** Tu usuario de GitHub (Pato214151)
- **Password:** Tu token personal de GitHub (NO tu contraseña de GitHub)

Si no tienes token, necesitas crear uno:
1. Ve a https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Marca los permisos `repo` (todos)
4. Click "Generate token"
5. COPIA y GUARDA el token (solo se muestra una vez)
6. Usa ese token como "contraseña" cuando Git te lo pida

---

## PASO 6: Render despliega automáticamente

Después de hacer `git push`, Render detecta automáticamente el cambio y comienza a construir:

### 6.1 — Monitorear el despliegue

1. Ve a https://dashboard.render.com/
2. Haz clic en tu servicio `raloz-web`
3. Ve a la pestaña **"Events"** o **"Logs"**
4. Observa el progreso del build

El build hace esto automáticamente (definido en `build.sh`):
1. Instala dependencias de Python (`pip install -r requirements.txt`)
2. Crea/actualiza las tablas en PostgreSQL (`flask init-db`)
3. Inserta datos iniciales si no existen (`flask seed`)
4. Instala dependencias de Node.js (`npm install`)
5. Construye el frontend React (`npm run build`)

### 6.2 — Verificar que las variables de entorno están configuradas

En el dashboard de Render, ve a **Environment** y verifica que tienes:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL de tu PostgreSQL | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Clave secreta de Flask | `una-cadena-larga-aleatoria-123` |
| `JWT_SECRET_KEY` | Clave secreta para JWT | `otra-cadena-larga-diferente-456` |
| `PYTHON_VERSION` | Versión de Python | `3.12.0` |
| `NODE_VERSION` | Versión de Node.js | `20.11.0` |

Si alguna falta, agrégala.

### 6.3 — Verificar el despliegue

Una vez que el build termine (toma 3-5 minutos), visita:

```
https://raloz-web.onrender.com/api/health
```

Si ves `{"status": "ok"}`, el backend está funcionando.

Luego visita:

```
https://raloz-web.onrender.com/
```

Deberías ver la pantalla de login. Ingresa con `admin` / `admin123`.

**NOTA IMPORTANTE:** Render en plan gratuito "duerme" el servicio después de 15 minutos de inactividad. La primera vez que lo visites después de dormir, puede tardar 30-60 segundos en despertar.

---

## PASO 7: Configurar datos iniciales en producción

Una vez que la app esté funcionando en Render, necesitas agregar los datos de tu negocio:

### 7.1 — Agregar Colegios

En la app web, ve al módulo de configuración o usa la API directamente:

```bash
# Desde tu terminal (cambia la URL si es diferente)
curl -X POST https://raloz-web.onrender.com/api/colegios \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TU_TOKEN_JWT" \
  -d '{"nombre": "Colegio San Jose", "ciudad": "Medellín"}'
```

O más fácil, desde la interfaz web — navega al sidebar y usa los módulos correspondientes.

### 7.2 — Agregar Productos

Desde la interfaz web, navega a productos y agrega cada uniforme:
- Nombre del producto (ej: "Camisa manga corta")
- Código (opcional)
- Tipo (ej: "uniforme")

### 7.3 — Configurar Precios

1. Ve al módulo **Precios** en el sidebar
2. Selecciona un colegio
3. Para cada producto, configura el precio por grupo de tallas:
   - Talla 6-8: $XX.XXX
   - Talla 10-12: $XX.XXX
   - Talla 14-16: $XX.XXX
   - Talla S-M: $XX.XXX
   - Talla L: $XX.XXX
   - Talla XL: $XX.XXX

---

## PASO 8: Mantenimiento futuro

### Si necesitas hacer cambios en el código:

```powershell
# 1. Ir al proyecto
cd C:\Users\julianr\Documents\raloz-web

# 2. Asegurarte de tener lo último de GitHub
git pull origin main

# 3. Hacer tus cambios (editar archivos)
# ... edita lo que necesites ...

# 4. Ver qué cambió
git status
git diff

# 5. Agregar, commit y push
git add .
git commit -m "Descripción de lo que cambiaste"
git push origin main

# 6. Render despliega automáticamente
```

### Si el build falla en Render:

1. Ve a los **Logs** en Render
2. Busca la línea con el error (en rojo)
3. Los errores más comunes son:
   - **"ModuleNotFoundError"** → Falta una dependencia en `requirements.txt`
   - **"npm ERR!"** → Falta una dependencia en `package.json`
   - **"SyntaxError"** → Error de código en algún archivo
4. Corrige el error localmente, haz commit y push de nuevo

### Si necesitas hacer respaldo de datos:

```powershell
# Necesitas tener PostgreSQL instalado localmente para esto
# O usa pgAdmin (interfaz gráfica)

# Descargar respaldo
pg_dump "TU_DATABASE_URL_DE_RENDER" > respaldo_2026-02-28.sql

# Restaurar respaldo (en una base nueva)
psql "URL_BASE_NUEVA" < respaldo_2026-02-28.sql
```

---

## Resumen de archivos nuevos y cambiados

### Archivos NUEVOS (no existían antes):

| Archivo | Qué hace |
|---------|----------|
| `backend/app/api/precios.py` | API para gestión de precios por colegio/producto/talla |
| `backend/app/api/empaque.py` | API para control de empaque de facturas |
| `backend/app/api/ventas.py` | API para hoja de ventas diaria |
| `backend/app/utils/tallas.py` | Lógica de conversión de tallas (individual ↔ agrupada) |
| `frontend/src/components/precios/Precios.jsx` | Interfaz de gestión de precios |
| `frontend/src/components/empaque/Empaque.jsx` | Interfaz de control de empaque |
| `GUIA_PASO_A_PASO.md` | Guía técnica completa del proyecto |
| `INSTRUCCIONES_COMPLETAS.md` | Este archivo |

### Archivos MEJORADOS (existían pero se mejoraron):

| Archivo | Qué cambió |
|---------|-----------|
| `backend/app/api/pendientes.py` | De 50 a 374 líneas: agrupación por colegio, entrega por lote, resumen |
| `backend/app/api/reportes.py` | Agregados endpoints de cuentas y ventas por colegio |
| `backend/app/__init__.py` | Registrados 3 nuevos blueprints (precios, empaque, ventas) |
| `frontend/src/App.jsx` | Agregadas rutas para Precios y Empaque |
| `frontend/src/components/common/Layout.jsx` | Agregados links de Precios, Empaque en sidebar |
| `frontend/src/components/facturacion/Facturacion.jsx` | De 149 a 460 líneas: auto-carga de precios, validaciones |
| `frontend/src/components/facturacion/BuscarFacturas.jsx` | De 124 a 395 líneas: filtros, paginación, acciones |
| `frontend/src/components/ventas/Ventas.jsx` | De 71 a 277 líneas: hoja diaria completa con métodos de pago |
| `frontend/src/components/pendientes/Pendientes.jsx` | De 255 a 479 líneas: agrupación por colegio |
| `frontend/src/components/clientes/Clientes.jsx` | De 98 a 417 líneas: CRUD completo, historial |
| `frontend/src/components/gastos/Gastos.jsx` | De 83 a 366 líneas: categorías, filtros |
| `frontend/src/components/stock/StockView.jsx` | De 83 a 333 líneas: colores por nivel, edición inline |
| `frontend/src/components/caja/Caja.jsx` | De 87 a 269 líneas: apertura/cierre, diferencias |
| `frontend/src/components/empaque/Empaque.jsx` | De 12 a 307 líneas: flujo completo de empaque |
| `render.yaml` | Eliminado rootDir incorrecto |

---

## Estructura final del proyecto

```
raloz-web/                          (tu repositorio en GitHub)
├── backend/
│   ├── app/
│   │   ├── __init__.py             ← Config Flask (18 blueprints registrados)
│   │   ├── api/                    ← 18 módulos de API REST
│   │   │   ├── auth.py             (207 líneas)
│   │   │   ├── facturas.py         (231 líneas)
│   │   │   ├── precios.py          (379 líneas) ★ NUEVO
│   │   │   ├── pendientes.py       (374 líneas) ★ MEJORADO
│   │   │   ├── ventas.py           (328 líneas) ★ NUEVO
│   │   │   ├── empaque.py          (257 líneas) ★ NUEVO
│   │   │   ├── reportes.py         (423 líneas) ★ MEJORADO
│   │   │   ├── usuarios.py         (157 líneas)
│   │   │   ├── stock.py            (142 líneas)
│   │   │   ├── prendas_pendientes.py (140 líneas)
│   │   │   ├── productos.py        (113 líneas)
│   │   │   ├── pagos.py            (113 líneas)
│   │   │   ├── caja.py             (111 líneas)
│   │   │   ├── migracion.py        (104 líneas)
│   │   │   ├── dashboard.py        (102 líneas)
│   │   │   ├── clientes.py         (95 líneas)
│   │   │   ├── gastos.py           (75 líneas)
│   │   │   └── colegios.py         (70 líneas)
│   │   ├── models/                 ← 16 modelos de base de datos
│   │   └── utils/
│   │       ├── decorators.py       ← Control de roles
│   │       ├── validators.py       ← Validación de datos
│   │       └── tallas.py           ★ NUEVO — mapeo de tallas
│   ├── requirements.txt
│   ├── run.py                      ← Punto de entrada + CLI commands
│   ├── Dockerfile
│   ├── .env.example
│   └── .gitignore
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 ← 17 rutas con protección por rol
│   │   ├── main.jsx
│   │   ├── context/AuthContext.jsx  ← Estado de autenticación + JWT
│   │   ├── services/api.js         ← Cliente HTTP con refresh automático
│   │   ├── styles/index.css        ← Tailwind + estilos custom
│   │   └── components/
│   │       ├── auth/Login.jsx           (169 líneas)
│   │       ├── common/Layout.jsx        (124 líneas)
│   │       ├── dashboard/Dashboard.jsx  (141 líneas)
│   │       ├── facturacion/
│   │       │   ├── Facturacion.jsx      (460 líneas) ★ MEJORADO
│   │       │   └── BuscarFacturas.jsx   (395 líneas) ★ MEJORADO
│   │       ├── pagos/Pagos.jsx          (98 líneas)
│   │       ├── pendientes/Pendientes.jsx (479 líneas) ★ MEJORADO
│   │       ├── clientes/Clientes.jsx    (417 líneas) ★ MEJORADO
│   │       ├── precios/Precios.jsx      (338 líneas) ★ NUEVO
│   │       ├── empaque/Empaque.jsx      (307 líneas) ★ NUEVO/MEJORADO
│   │       ├── gastos/Gastos.jsx        (366 líneas) ★ MEJORADO
│   │       ├── stock/StockView.jsx      (333 líneas) ★ MEJORADO
│   │       ├── ventas/Ventas.jsx        (277 líneas) ★ MEJORADO
│   │       ├── caja/Caja.jsx            (269 líneas) ★ MEJORADO
│   │       ├── reportes/
│   │       │   ├── Reportes.jsx         (174 líneas)
│   │       │   └── CuentasPorCobrar.jsx (114 líneas)
│   │       └── usuarios/Usuarios.jsx    (153 líneas)
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── index.html
│
├── build.sh                        ← Script de construcción para Render
├── render.yaml                     ← Configuración de Render (corregido)
├── docker-compose.yml              ← Para desarrollo local con Docker
├── .gitignore                      ← Excluye .env, node_modules, etc.
├── GUIA_PASO_A_PASO.md             ← Guía técnica
└── INSTRUCCIONES_COMPLETAS.md      ← Este archivo
```

---

## Estadísticas finales

| Componente | Líneas de código |
|-----------|-----------------|
| Backend APIs (18 módulos) | 3,421 |
| Backend Models (16 modelos) | 645 |
| Backend Utils | 232 |
| Backend Config | 220 |
| **Backend Total** | **4,518** |
| Frontend Components (17) | 4,614 |
| Frontend Core (App, Auth, API) | 231 |
| **Frontend Total** | **4,845** |
| **TOTAL PROYECTO** | **9,363 líneas** |

74 endpoints de API. 17 componentes de React. 45 archivos Python. 21 archivos JSX/JS.

---

*Última actualización: Febrero 28, 2026*
