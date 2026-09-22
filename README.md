# RALOZ COL SAS — Sistema de Gestión y Tienda Online

![Python](https://img.shields.io/badge/Backend-Flask%20(Python)-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/Admin-React%20%2B%20Vite-61DAFB?logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/DB-PostgreSQL%20(Supabase)-4169E1?logo=postgresql&logoColor=white)
![Payments](https://img.shields.io/badge/Pagos-MercadoPago-00B1EA?logo=mercadopago&logoColor=white)
![Deploy](https://img.shields.io/badge/Deploy-Render%20%7C%20Cloudflare-46E3B7?logo=cloudflare&logoColor=white)
![Code](https://img.shields.io/badge/Code-~23k%20LOC-success)

**Plataforma full-stack de e-commerce, en producción**, para un negocio real de
uniformes escolares en Bogotá: tienda pública, panel administrativo/POS, pasarela
de pagos, facturación electrónica, bot de WhatsApp y una auditoría de seguridad
documentada. *Full-stack e-commerce platform running in production.*

> **Nota:** esta es la copia pública del código. El repositorio de producción es privado; del historial se retiraron los archivos de migración que contenían datos de clientes.

🛒 [Tienda en vivo](https://ralozcolsas.com) · 🖥️ [Panel admin](https://raloz-web.onrender.com) · 📐 [Arquitectura](docs/ARQUITECTURA.md) · 💼 [Resumen para CV/LinkedIn](docs/PORTFOLIO.md)

> **Empresa:** RALOZ COL SAS · Uniformes Escolares · Bogotá, Colombia  
> **Versión:** 1.0.0-beta  
> **Stack:** Flask (Python) + React (Vite) + PostgreSQL (Supabase) + Cloudflare Pages

> 📐 **Documentación técnica / Technical docs:**
> [Arquitectura (ES)](docs/ARQUITECTURA.md) · [Architecture (EN)](docs/ARCHITECTURE.md)
> — diagramas de arquitectura, modelo de datos, flujos de negocio y seguridad.
> 📄 Versión descargable (PDF): [Español](docs/RALOZ_Arquitectura_ES.pdf) · [English](docs/RALOZ_Architecture_EN.pdf)

---

## ¿Qué es esto?

Este repositorio contiene **dos sistemas integrados**:

| Sistema | Tecnología | URL Producción | Usuarios |
|---------|-----------|----------------|---------|
| **POS / Admin** | Flask + React | [raloz-web.onrender.com](https://raloz-web.onrender.com) | Administradores, vendedores, cajeros |
| **Tienda Pública** | HTML + CSS + JS puro | [ralozcolsas.com](https://ralozcolsas.com) | Clientes finales (padres de familia) |

Ambos comparten el mismo backend Flask. La tienda pública consume los endpoints `/api/tienda/*` que no requieren autenticación.

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENTE FINAL                         │
│              ralozcolsas.com                      │
│        (HTML/CSS/JS estático en Cloudflare Pages)        │
└────────────────────────┬────────────────────────────────┘
                         │ POST /api/tienda/pedido
                         │ GET  /api/tienda/catalogo/:id
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  BACKEND FLASK                           │
│            raloz-web.onrender.com/api                    │
│                                                          │
│  blueprints: auth · tienda · facturas · stock · ...      │
│  Flask-JWT-Extended · Flask-Migrate · ReportLab          │
│  MercadoPago SDK · Brevo (email)                         │
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
               ▼                      ▼
┌──────────────────────┐  ┌──────────────────────────────┐
│   PostgreSQL          │  │  SERVICIOS EXTERNOS           │
│   (Supabase)          │  │                              │
│                       │  │  MercadoPago — pagos         │
│  pedidos_web          │  │  Brevo — emails transacc.    │
│  facturas             │  │  Google OAuth — login         │
│  pedidos_fabricacion  │  └──────────────────────────────┘
│  stock                │
│  clientes             │
│  colegios             │
│  ...24 tablas         │
└──────────────────────┘
               ▲
               │ JWT Bearer Token
               │
┌──────────────────────────────────────────────────────────┐
│                  POS / ADMIN                              │
│              raloz-web.onrender.com                      │
│              (React + Vite, servido por Flask)            │
│                                                          │
│  Dashboard · Facturación · Pedidos Online                │
│  Fabricación · Stock · Pagos · Caja · Reportes           │
└──────────────────────────────────────────────────────────┘
```

---

## Módulos del POS

| Ruta | Módulo | Qué hace | Roles |
|------|--------|----------|-------|
| `/` | Dashboard | KPIs del día/mes, gráfica ventas 7 días, accesos rápidos | Todos |
| `/facturacion` | Nueva Venta | Crea facturas en mostrador con cobro inmediato; imprime **ticket 76mm** (Epson TM-U220PD) | Admin, Vendedor, Cajero |
| `/buscar` | Buscar Facturas | Busca, edita, anula, reactiva facturas; registra pagos; reimprime **ticket 76mm** o **factura A4** | Todos |
| `/pagos` | Registrar Pago | Registra abonos a facturas existentes | Admin, Cajero |
| `/stock` | Stock Actual | Inventario por colegio/talla, ajustes, historial | Admin, Vendedor |
| `/fabricacion/stock` | Stock Fabricación | Prendas pendientes de fabricar por colegio | Admin, Vendedor |
| `/precios` | Precios | Configurar precios por colegio/producto/talla | Admin |
| `/pedidos-online` | Pedidos Online | Órdenes de la tienda web: estados, facturas, entregas | Admin, Vendedor |
| `/fabricacion` | Fabricación | Pedidos en producción: progreso, WhatsApp, saldo | Admin, Vendedor |
| `/pendientes` | Prendas Pendientes | Entregas pendientes al cliente (por recoger) | Todos |
| `/empaque` | Empaque | Preparar y registrar entregas físicas | Todos |
| `/caja` | Caja | Apertura/cierre de caja, movimientos | Admin, Cajero |
| `/gastos` | Gastos | Registro de egresos del negocio | Admin, Cajero |
| `/reportes` | Reportes | Ventas por período, productos más vendidos | Admin |
| `/cuentas` | Cuentas por Cobrar | Facturas con saldo pendiente | Admin, Vendedor |
| `/clientes` | Clientes | CRM básico con historial de compras | Todos |
| `/ventas` | Hoja de Ventas | Resumen diario de ventas por vendedor | Admin, Vendedor |
| `/tareas` | Tareas | Lista de tareas/pendientes del equipo | Todos |
| `/usuarios` | Usuarios | Crear/bloquear usuarios del POS | Admin |
| `/configuracion` | Configuración | Colegios, productos, métodos de pago | Admin |

> 📱 **PWA:** el panel es instalable como app en el celular (pantalla completa, sin
> tienda de apps). Manifest + service worker en `frontend/public/`; el SW nunca
> cachea `/api/*` (JWT/datos en vivo) y se registra solo en producción.

---

## Estructura de Carpetas

```
raloz-web/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   ├── api/                 # 23 dominios (un blueprint por dominio)
│   │   │   ├── tienda/          # PAQUETE: publico.py + admin.py
│   │   │   ├── facturas.py      # CRUD facturas + PDF
│   │   │   ├── stock.py         # Inventario
│   │   │   ├── auth.py          # JWT login + Google OAuth
│   │   │   └── ...
│   │   ├── services/            # Lógica de negocio (facturacion_web.py)
│   │   ├── models/              # 24 modelos SQLAlchemy
│   │   ├── utils/
│   │   │   ├── email_service.py # Generación PDF + envío Brevo
│   │   │   └── tallas.py        # Conversión tallas grupo↔individual
│   │   └── db_migrations.py     # Migraciones versionadas (schema_migrations)
│   ├── run.py                   # Punto de entrada + jobs daemon
│   ├── security_check.py        # Chequeo de seguridad contra producción
│   ├── tests/                   # ~97 tests (pytest)
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Router principal
│   │   ├── services/api.ts      # Axios tipado + interceptores JWT
│   │   ├── types/api.ts         # Tipos de dominio (migración gradual a TS)
│   │   ├── context/AuthContext.tsx
│   │   └── components/          # Un directorio por módulo
│   ├── tsconfig.json           # TS gradual (allowJs: JS y TS conviven)
│   ├── dist/                    # Build producción (servido por Flask)
│   └── package.json
│
└── ../Raloz/                    # Tienda pública (carpeta hermana)
    ├── index.html
    ├── js/
    │   ├── core/api.js          # Fetch wrapper → backend
    │   ├── modules/checkout.js  # Talla modal + carrito + MercadoPago
    │   └── data/                # Catálogo estático (fallback offline)
    └── sw.js                    # Service Worker (offline)
```

---

## Cómo Correr Localmente

### Backend

```bash
cd "sofware raloz/raloz-web/backend"
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Configurar variables de entorno (crear .env)
cp .env.test .env

python run.py                  # Servidor en localhost:5000
```

### Frontend (POS)

```bash
cd "sofware raloz/raloz-web/frontend"
npm install
npm run dev    # Dev server en localhost:5173 (proxy → :5000)
```

### Tienda Pública

```bash
cd Raloz
python -m http.server 8080     # Servidor estático en localhost:8080
```

---

## Variables de Entorno Requeridas

```bash
# Base de datos
DATABASE_URL=postgresql://...supabase.co/postgres?sslmode=require

# JWT
JWT_SECRET_KEY=clave-secreta-muy-larga

# MercadoPago
MP_ACCESS_TOKEN=APP_USR-...    # Token de producción
MP_REDIRECT_URL=https://ralozcolsas.com  # URL de retorno

# Email (Brevo - producción en Render)
BREVO_API_KEY=xkeysib-...      # API key de Brevo (NO la SMTP key)
EMAIL_REMITENTE=raloz@tudominio.com
EMAIL_PASSWORD=app-password    # Solo para SMTP fallback en local
EMAIL_NOMBRE=RALOZ COL SAS
```

---

## Flujo de Datos: Pedido Online

```
1. Cliente elige colegio + productos en ralozcolsas.com
2. Agrega al carrito → checkout form (nombre, email, tel, dirección)
3. POST /api/tienda/pedido → backend crea PedidoWeb (estado=pendiente)
4. Backend genera preferencia en MercadoPago → retorna init_point URL
5. Cliente paga en MercadoPago (tarjeta / PSE / efectivo)
6. MercadoPago envía webhook a POST /api/tienda/mp/webhook
7. Backend consulta estado del pago en MP API
8. Si aprobado:
   a. Actualiza PedidoWeb.estado = 'pagado'
   b. Crea Factura (PAGADA o ABONO) + descuenta stock
   c. Si hay prendas de fabricación → crea PedidoFabricacion
   d. Envía email con PDF de factura al cliente (vía Brevo)
9. Vendedor ve pedido en /pedidos-online con badge de entrega
10. Sigue flujo: POR_ENTREGAR → EMPACADO → ENTREGADO
    (fabricación: EN_PRODUCCION → LISTO → WhatsApp → ENTREGADO)
```

---

## Deployment

| Componente | Plataforma | Notas |
|-----------|-----------|-------|
| Backend + Admin | Render (free tier) | Cold start ~90s. Auto-deploy en `git push` |
| Tienda pública | Cloudflare Pages | CDN global. Auto-deploy en `git push` |
| Base de datos | Supabase | PostgreSQL managed. SSL requerido |
| Email | Brevo | HTTP API (Render bloquea SMTP saliente) |
| Pagos | MercadoPago | Modo producción + sandbox disponible |

```bash
# Build del frontend y deploy
cd "sofware raloz/raloz-web/frontend"
npm run build
cd ..
git add -A
git commit -m "descripción del cambio"
git push   # Render detecta el push y redespliega en ~2-3 min
```

---

## Autenticación

- **JWT**: access token (2h) + refresh token (30 días) con auto-refresh via interceptor Axios
- **Login**: usuario/contraseña o Google OAuth
- **Roles**: `administrador`, `vendedor`, `cajero`
- **Rutas públicas**: todo `/api/tienda/*` (sin JWT)
- **Rutas protegidas**: todo lo demás requiere `Authorization: Bearer <token>`

---

## Calidad: Tests, CI y Seguridad

```bash
cd backend && python -m pytest tests/ -q      # ~97 tests (webhook, stock, roles, deudas...)
cd backend && python security_check.py        # chequeo de seguridad contra producción
cd frontend && npm run typecheck && npm run build
```

- **CI** (GitHub Actions): en cada push a `main` y PR corre `pytest` + `tsc --noEmit` + `vite build`.
- **Seguridad** (auditada): JWT con lista negra al logout, bloqueo de cuenta, rate limiting,
  CORS por allowlist, headers (HSTS, CSP en modo enforce, X-Frame DENY), webhook MercadoPago
  con firma HMAC, sanitización de entradas. `security_check.py` los verifica en vivo.
- **TypeScript gradual**: `allowJs` deja convivir `.jsx` y `.ts(x)`; solo los convertidos se
  type-checkean. Migrar archivo por archivo importando tipos de `src/types/`.

---

## Notas Importantes

1. **Catálogo de la tienda**: `Raloz/js/data/{colegios,productos,precios}.js` se **generan** desde la BD con `Raloz/tools/sync_catalogo.mjs` (`--check` reporta drift, `--write` regenera). No editar a mano.
2. **Migraciones**: versionadas en `app/db_migrations.py` (lista `MIGRACIONES`), registradas en `schema_migrations`; corren al iniciar y nunca se re-ejecutan. Para agregar una columna, añade un dict con la siguiente versión.
3. **Cold start Render**: El servidor free tier tarda ~90s en arrancar tras inactividad. La tienda reintenta automáticamente
4. **Service Worker**: La tienda funciona offline con catálogo estático; sincroniza al reconectarse
5. **Tallas**: Dos formatos — "grupos" (6-8, 10-12) para precios, "individuales" (6, 8, 10) para stock

---

*RALOZ COL SAS — Sistema desarrollado a medida · Bogotá, Colombia*
