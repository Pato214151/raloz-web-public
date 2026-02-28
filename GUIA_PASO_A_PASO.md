# RALOZ WEB — Guía Paso a Paso de Despliegue y Mantenimiento

**Versión:** 1.0
**Fecha:** Febrero 2026
**Para:** Julián Ramírez — RALOZ COL SAS

---

## Tabla de Contenido

1. [Resumen de la Arquitectura](#1-resumen-de-la-arquitectura)
2. [Estructura del Proyecto](#2-estructura-del-proyecto)
3. [Cómo Funciona Todo Junto](#3-cómo-funciona-todo-junto)
4. [Paso 1: Configurar el Entorno Local](#paso-1-configurar-el-entorno-local)
5. [Paso 2: Configurar la Base de Datos](#paso-2-configurar-la-base-de-datos)
6. [Paso 3: Ejecutar el Backend Localmente](#paso-3-ejecutar-el-backend-localmente)
7. [Paso 4: Ejecutar el Frontend Localmente](#paso-4-ejecutar-el-frontend-localmente)
8. [Paso 5: Subir Cambios a GitHub](#paso-5-subir-cambios-a-github)
9. [Paso 6: Desplegar en Render.com](#paso-6-desplegar-en-rendercom)
10. [Paso 7: Verificar el Despliegue](#paso-7-verificar-el-despliegue)
11. [Mantenimiento Diario](#mantenimiento-diario)
12. [Solución de Problemas](#solución-de-problemas)
13. [Mapa de Módulos: Desktop vs Web](#mapa-de-módulos-desktop-vs-web)

---

## 1. Resumen de la Arquitectura

Tu aplicación web tiene dos partes principales:

```
┌────────────────────────────────────────────────────────────┐
│                    USUARIO (Navegador)                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           FRONTEND (React + Vite + Tailwind)          │   │
│  │  - Dashboard, Facturación, Pagos, Clientes, etc.      │   │
│  │  - Se comunica con el Backend por API REST             │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 │ API calls (JSON)                            │
│  ┌──────────────▼───────────────────────────────────────┐   │
│  │           BACKEND (Flask + SQLAlchemy)                 │   │
│  │  - Autenticación JWT                                   │   │
│  │  - APIs REST para cada módulo                          │   │
│  │  - Validación y lógica de negocio                      │   │
│  └──────────────┬───────────────────────────────────────┘   │
│                 │ SQL queries                                 │
│  ┌──────────────▼───────────────────────────────────────┐   │
│  │           BASE DE DATOS (PostgreSQL en Render)        │   │
│  │  - 16 tablas (misma estructura que SQLite desktop)     │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

**Diferencia clave con el desktop:**
- Desktop: Python + Tkinter + SQLite (todo en un archivo .exe)
- Web: React (interfaz) + Flask (servidor) + PostgreSQL (base de datos en la nube)

---

## 2. Estructura del Proyecto

```
RALOZ-Web/
├── backend/                    ← Servidor Python (Flask)
│   ├── app/
│   │   ├── __init__.py         ← Configuración principal de Flask
│   │   ├── api/                ← Endpoints REST (uno por módulo)
│   │   │   ├── auth.py         ← Login, registro, JWT
│   │   │   ├── facturas.py     ← Crear, buscar, anular facturas
│   │   │   ├── pagos.py        ← Registrar pagos/abonos
│   │   │   ├── pendientes.py   ← Prendas pendientes de entrega
│   │   │   ├── clientes.py     ← CRUD clientes
│   │   │   ├── precios.py      ← Precios por colegio/producto ★ NUEVO
│   │   │   ├── empaque.py      ← Control de empaque ★ NUEVO
│   │   │   ├── ventas.py       ← Hoja de ventas diaria ★ NUEVO
│   │   │   ├── stock.py        ← Inventario
│   │   │   ├── gastos.py       ← Gastos del negocio
│   │   │   ├── caja.py         ← Apertura/cierre de caja
│   │   │   ├── reportes.py     ← Reportes y gráficos
│   │   │   ├── dashboard.py    ← KPIs del dashboard
│   │   │   ├── colegios.py     ← CRUD colegios
│   │   │   ├── productos.py    ← CRUD productos
│   │   │   └── usuarios.py     ← Gestión de usuarios
│   │   ├── models/             ← Modelos de base de datos (ORM)
│   │   │   ├── factura.py, pago.py, cliente.py, etc.
│   │   └── utils/
│   │       ├── decorators.py   ← Control de roles
│   │       ├── validators.py   ← Validación de datos
│   │       └── tallas.py       ← Sistema de tallas ★ NUEVO
│   ├── requirements.txt        ← Dependencias Python
│   ├── run.py                  ← Punto de entrada
│   ├── Dockerfile              ← Para construir en Render
│   └── .env                    ← Variables de entorno (NO subir a GitHub)
│
├── frontend/                   ← Interfaz React
│   ├── src/
│   │   ├── App.jsx             ← Rutas y protección por rol
│   │   ├── main.jsx            ← Punto de entrada React
│   │   ├── context/
│   │   │   └── AuthContext.jsx  ← Estado de autenticación
│   │   ├── services/
│   │   │   └── api.js          ← Cliente HTTP (Axios + JWT)
│   │   ├── components/
│   │   │   ├── auth/Login.jsx
│   │   │   ├── common/Layout.jsx      ← Sidebar + navegación
│   │   │   ├── dashboard/Dashboard.jsx
│   │   │   ├── facturacion/
│   │   │   │   ├── Facturacion.jsx    ← Nueva venta (con auto-precios)
│   │   │   │   └── BuscarFacturas.jsx ← Buscar con filtros y acciones
│   │   │   ├── pagos/Pagos.jsx
│   │   │   ├── pendientes/Pendientes.jsx ← Con agrupación por colegio
│   │   │   ├── clientes/Clientes.jsx    ← CRUD completo
│   │   │   ├── precios/Precios.jsx      ← ★ NUEVO
│   │   │   ├── empaque/Empaque.jsx      ← ★ NUEVO
│   │   │   ├── stock/StockView.jsx
│   │   │   ├── gastos/Gastos.jsx
│   │   │   ├── caja/Caja.jsx
│   │   │   ├── ventas/Ventas.jsx        ← Hoja de ventas mejorada
│   │   │   ├── reportes/
│   │   │   │   ├── Reportes.jsx
│   │   │   │   └── CuentasPorCobrar.jsx
│   │   │   └── usuarios/Usuarios.jsx
│   │   └── styles/index.css    ← Tailwind + estilos custom
│   ├── package.json
│   └── vite.config.js
│
├── render.yaml                 ← Configuración de despliegue en Render
├── build.sh                    ← Script de construcción
└── docker-compose.yml          ← Para desarrollo local con Docker
```

---

## 3. Cómo Funciona Todo Junto

### Flujo de una operación (ejemplo: Crear Factura)

1. **El usuario** llena el formulario en `Facturacion.jsx`
2. **React** envía un POST a `/api/facturas` con los datos JSON
3. **Flask** recibe la petición en `facturas.py`
4. **El decorador** `@jwt_required()` verifica que el usuario esté autenticado
5. **El decorador** `@rol_requerido()` verifica que tenga permiso
6. **La API** valida los datos, genera número de factura, calcula totales
7. **SQLAlchemy** guarda en PostgreSQL (factura + detalles + descuento stock)
8. **Flask** responde con la factura creada
9. **React** muestra el toast de éxito

### Sistema de roles (igual que el desktop)

| Rol | Acceso |
|-----|--------|
| **administrador** | Todo: facturación, precios, reportes, usuarios, config |
| **cajero** | Facturación, pagos, caja, gastos, ventas |
| **vendedor** | Facturación, pagos, stock, pendientes, clientes |

### Sistema de tallas (lógica crítica del negocio)

```
PRECIOS  → Usan tallas AGRUPADAS: 6-8, 10-12, 14-16, S-M, L, XL
STOCK    → Usa tallas INDIVIDUALES: 4, 6, 8, 10, 12, 14, 16, S, M, L, XL
FACTURAS → Registran talla INDIVIDUAL del item vendido

Conversión automática:
  Talla 6 o 8   → busca precio del grupo "6-8"
  Talla 10 o 12 → busca precio del grupo "10-12"
  Talla S o M   → busca precio del grupo "S-M"
```

---

## Paso 1: Configurar el Entorno Local

### Requisitos previos
- **Python 3.10+** (descargar de python.org)
- **Node.js 18+** (descargar de nodejs.org)
- **Git** (descargar de git-scm.com)

### 1.1 Clonar el repositorio

```bash
cd C:\Users\julianr\Documents
git clone https://github.com/Pato214151/raloz-web.git
cd raloz-web
```

### 1.2 Configurar el Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 1.3 Configurar el Frontend

```bash
cd frontend

# Instalar dependencias
npm install
```

### 1.4 Crear archivo .env del Backend

Crea el archivo `backend/.env` con:

```env
# Base de datos (en desarrollo local puedes usar SQLite)
DATABASE_URL=sqlite:///raloz_dev.db

# En producción (Render), usa la URL de PostgreSQL:
# DATABASE_URL=postgresql://user:pass@host:5432/raloz_db

# Claves secretas (cámbialas en producción)
SECRET_KEY=tu-clave-secreta-cambiar-en-produccion
JWT_SECRET_KEY=tu-jwt-secret-cambiar-en-produccion

# Google OAuth (opcional)
GOOGLE_CLIENT_ID=tu-google-client-id
```

---

## Paso 2: Configurar la Base de Datos

### 2.1 Crear las tablas

```bash
cd backend
# Activar entorno virtual si no está activo
venv\Scripts\activate

# Inicializar las migraciones (solo la primera vez)
flask db init
flask db migrate -m "Estructura inicial"
flask db upgrade
```

### 2.2 Crear usuario administrador

Puedes usar el script de migración o crear uno manualmente:

```bash
python -c "
from app import create_app, db
from app.models import Usuario
import bcrypt

app = create_app()
with app.app_context():
    db.create_all()

    # Crear admin
    hash_pw = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt())
    admin = Usuario(usuario='admin', password_hash=hash_pw.decode(), rol='administrador', activo=True)
    db.session.add(admin)

    # Crear cajero
    hash_pw2 = bcrypt.hashpw('caja123'.encode(), bcrypt.gensalt())
    cajero = Usuario(usuario='cajero', password_hash=hash_pw2.decode(), rol='cajero', activo=True)
    db.session.add(cajero)

    db.session.commit()
    print('Usuarios creados exitosamente')
"
```

---

## Paso 3: Ejecutar el Backend Localmente

```bash
cd backend
venv\Scripts\activate

# Modo desarrollo
python run.py
```

El backend estará disponible en: `http://localhost:5000`

Para verificar: abre `http://localhost:5000/api/health` en el navegador.

---

## Paso 4: Ejecutar el Frontend Localmente

En otra terminal:

```bash
cd frontend

# Crear .env para desarrollo
echo "VITE_API_URL=http://localhost:5000/api" > .env

# Ejecutar en modo desarrollo
npm run dev
```

El frontend estará disponible en: `http://localhost:5173`

---

## Paso 5: Subir Cambios a GitHub

### 5.1 Después de hacer cambios en el código:

```bash
# Ver qué archivos cambiaron
git status

# Agregar los archivos modificados
git add backend/app/api/precios.py
git add frontend/src/components/precios/Precios.jsx
# o agregar todos:
git add .

# Crear commit con descripción
git commit -m "Agregar módulo de precios con CRUD completo"

# Subir a GitHub
git push origin main
```

### 5.2 Regla de oro: NUNCA subir archivos sensibles

Asegúrate de que `.gitignore` contenga:
```
.env
*.db
node_modules/
__pycache__/
venv/
dist/
```

---

## Paso 6: Desplegar en Render.com

### 6.1 Configuración inicial (ya está hecha)

Tu proyecto ya está conectado a Render. Cada vez que hagas `git push` a GitHub, Render automáticamente:

1. Detecta el cambio
2. Ejecuta `build.sh` (instala dependencias del backend y construye el frontend)
3. Reinicia el servidor

### 6.2 Variables de entorno en Render

Ve a **Render Dashboard** → tu servicio → **Environment**:

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | (la URL de tu PostgreSQL en Render) |
| `SECRET_KEY` | (una cadena aleatoria larga) |
| `JWT_SECRET_KEY` | (otra cadena aleatoria larga) |
| `GOOGLE_CLIENT_ID` | (tu ID de Google OAuth, si lo usas) |
| `PYTHON_VERSION` | 3.11.0 |

### 6.3 Verificar el despliegue

Después de cada push, monitorea en Render:
1. Ve a **Dashboard** → tu servicio
2. Revisa la pestaña **Logs** para ver el progreso
3. Si hay errores, los verás en rojo

---

## Paso 7: Verificar el Despliegue

1. Abre `https://raloz-web.onrender.com/api/health`
   - Debería mostrar: `{"status": "ok", "app": "RALOZ COL SAS"}`

2. Abre `https://raloz-web.onrender.com/`
   - Debería mostrar la pantalla de login

3. Inicia sesión con `admin` / `admin123`

4. Verifica cada módulo:
   - Dashboard (KPIs y gráficos)
   - Nueva Venta (creación de facturas)
   - Buscar Facturas (búsqueda y filtros)
   - Pagos (registrar abonos)
   - Stock (inventario)
   - Precios (configurar precios por colegio)
   - Pendientes (prendas por entregar)
   - Empaque (control de empaque)

---

## Mantenimiento Diario

### Respaldos de la base de datos

Render no respalda automáticamente los datos de su base de datos gratuita. Para respaldar:

```bash
# Descargar respaldo (necesitas la URL de conexión de PostgreSQL)
pg_dump DATABASE_URL > respaldo_$(date +%Y%m%d).sql
```

### Monitorear errores

1. Revisa los **Logs** en Render periódicamente
2. Errores comunes:
   - `500 Internal Server Error` → revisa los logs del backend
   - `401 Unauthorized` → el token JWT expiró, vuelve a iniciar sesión
   - `CORS error` → problema de configuración, contacta soporte

### Actualizar dependencias

```bash
# Backend
cd backend
pip install --upgrade -r requirements.txt

# Frontend
cd frontend
npm update
```

---

## Solución de Problemas

### "La página no carga / error 503"

Render apaga los servicios gratuitos después de 15 minutos de inactividad. La primera visita puede tardar 30-60 segundos mientras se reinicia.

**Solución:** Espera un momento y recarga la página.

### "Error al crear factura"

1. Verifica que hayas seleccionado colegio, cliente y al menos un producto
2. Verifica que los precios estén configurados para ese colegio
3. Revisa los logs del backend en Render

### "No puedo iniciar sesión"

1. Verifica usuario y contraseña
2. Si olvidaste la contraseña, debes resetearla en la base de datos
3. Verifica que el usuario esté activo

### "Los precios no aparecen automáticamente"

1. Ve a Precios → selecciona el colegio → configura precios por producto y talla
2. Los precios se cargan automáticamente al seleccionar colegio en Facturación

### "Build falla en Render"

1. Revisa los logs del build en Render
2. Errores comunes:
   - Dependencia faltante → agregar a `requirements.txt` o `package.json`
   - Error de sintaxis → corregir y hacer push de nuevo

---

## Mapa de Módulos: Desktop vs Web

| Módulo Desktop | Módulo Web | Estado |
|----------------|-----------|--------|
| `login.py` | `auth/Login.jsx` + `api/auth.py` | ✅ Completo |
| `dashboard.py` | `dashboard/Dashboard.jsx` + `api/dashboard.py` | ✅ Completo |
| `facturacion_module.py` | `facturacion/Facturacion.jsx` + `api/facturas.py` | ✅ Completo |
| `buscador_facturas.py` | `facturacion/BuscarFacturas.jsx` | ✅ Completo |
| `pagos_module.py` | `pagos/Pagos.jsx` + `api/pagos.py` | ✅ Completo |
| `pendientes_module.py` | `pendientes/Pendientes.jsx` + `api/pendientes.py` | ✅ Completo |
| `clientes_module.py` | `clientes/Clientes.jsx` + `api/clientes.py` | ✅ Completo |
| `precios_module.py` | `precios/Precios.jsx` + `api/precios.py` | ✅ **NUEVO** |
| `empaque_module.py` | `empaque/Empaque.jsx` + `api/empaque.py` | ✅ **NUEVO** |
| `ventas_module.py` | `ventas/Ventas.jsx` + `api/ventas.py` | ✅ **MEJORADO** |
| `stock_module.py` | `stock/StockView.jsx` + `api/stock.py` | ✅ Completo |
| `gastos_module.py` | `gastos/Gastos.jsx` + `api/gastos.py` | ✅ Completo |
| `caja_module.py` | `caja/Caja.jsx` + `api/caja.py` | ✅ Completo |
| `reportes_module.py` | `reportes/Reportes.jsx` + `api/reportes.py` | ✅ Mejorado |
| `reporte_cuentas.py` | `reportes/CuentasPorCobrar.jsx` | ✅ Completo |
| `usuarios_module.py` | `usuarios/Usuarios.jsx` + `api/usuarios.py` | ✅ Completo |
| `config_module.py` | Integrado en Precios + Colegios + Productos | ✅ Completo |
| `pos_rapido.py` | Integrado en Facturacion (simplificado) | ✅ Adaptado |
| `dashboard_cajero.py` | Dashboard con filtro por rol | ✅ Adaptado |
| `dashboard_vendedor.py` | Dashboard con filtro por rol | ✅ Adaptado |

### Funcionalidades agregadas que NO estaban en el desktop:

- **Autenticación JWT** con refresh token automático
- **Google OAuth** como método alternativo de login
- **Responsive design** — funciona en celular, tablet y PC
- **Paginación** en todas las listas
- **Rate limiting** para protección contra abuso
- **Security headers** (XSS, CSRF protection)
- **API REST documentada** con endpoints consistentes

---

## Próximos Pasos Recomendados

1. **Configurar precios** — Ingresa los precios por colegio/producto/talla
2. **Crear colegios** — Agrega todos tus colegios desde el módulo de colegios
3. **Cargar productos** — Registra todos los uniformes con sus códigos
4. **Migrar datos** — Si necesitas migrar datos del desktop, usa el endpoint `/api/migracion`
5. **Capacitar usuarios** — Crea cuentas para cajeros y vendedores

---

*Documento generado como parte de la reorganización del proyecto RALOZ COL SAS.*
*Para soporte técnico, contacta a tu desarrollador.*
