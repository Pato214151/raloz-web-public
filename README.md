# RALOZ COL SAS — Sistema de Gestión y Tienda Online

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
| **Tienda Pública** | HTML + CSS + JS puro | [ralozcol-web.pages.dev](https://ralozcol-web.pages.dev) | Clientes finales (padres de familia) |

Ambos comparten el mismo backend Flask. La tienda pública consume los endpoints `/api/tienda/*` que no requieren autenticación.

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENTE FINAL                         │
│              ralozcol-web.pages.dev                      │
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
| `/facturacion` | Nueva Venta | Crea facturas en mostrador con cobro inmediato | Admin, Vendedor, Cajero |
| `/buscar` | Buscar Facturas | Busca, edita, anula, reactiva facturas; registra pagos | Todos |
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

---

## Estructura de Carpetas

```
raloz-web/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # Flask app factory
│   │   ├── api/                 # 23 blueprints (un archivo por dominio)
│   │   │   ├── tienda.py        # Tienda pública + admin pedidos web
│   │   │   ├── facturas.py      # CRUD facturas + PDF
│   │   │   ├── stock.py         # Inventario
│   │   │   ├── auth.py          # JWT login + Google OAuth
│   │   │   └── ...
│   │   ├── models/              # 24 modelos SQLAlchemy
│   │   │   ├── pedido_web.py
│   │   │   ├── pedido_fabricacion.py
│   │   │   ├── factura.py
│   │   │   └── ...
│   │   ├── utils/
│   │   │   ├── email_service.py # Generación PDF + envío Brevo
│   │   │   └── tallas.py        # Conversión tallas grupo↔individual
│   │   └── static/
│   │       └── logo.png         # Logo para PDF
│   ├── run.py                   # Punto de entrada + migraciones inline
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Router principal
│   │   ├── services/api.js      # Axios + interceptores JWT
│   │   ├── context/AuthContext.jsx
│   │   └── components/          # Un directorio por módulo
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
MP_REDIRECT_URL=https://ralozcol-web.pages.dev  # URL de retorno

# Email (Brevo - producción en Render)
BREVO_API_KEY=xkeysib-...      # API key de Brevo (NO la SMTP key)
EMAIL_REMITENTE=raloz@tudominio.com
EMAIL_PASSWORD=app-password    # Solo para SMTP fallback en local
EMAIL_NOMBRE=RALOZ COL SAS
```

---

## Flujo de Datos: Pedido Online

```
1. Cliente elige colegio + productos en ralozcol-web.pages.dev
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

## Notas Importantes

1. **Nombres de productos**: Los nombres en `Raloz/js/data/productos.js` deben coincidir EXACTAMENTE con los nombres en la BD (incluyendo emojis y tildes)
2. **Migraciones**: Se ejecutan automáticamente al iniciar `run.py` via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
3. **Cold start Render**: El servidor free tier tarda ~90s en arrancar tras inactividad. La tienda reintenta automáticamente
4. **Service Worker**: La tienda funciona offline con catálogo estático; sincroniza al reconectarse
5. **Tallas**: Dos formatos — "grupos" (6-8, 10-12) para precios, "individuales" (6, 8, 10) para stock

---

*RALOZ COL SAS — Sistema desarrollado a medida · Bogotá, Colombia*
