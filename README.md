# RALOZ COL SAS — Sistema Web de Gestión

Sistema completo de facturación, inventario y ventas en línea para RALOZ COL SAS.

## Arquitectura

```
raloz-web/
├── backend/        # API Flask (Python) — desplegado en Render
├── frontend/       # Panel admin React — servido desde el backend
├── docs/           # Guías y documentación
├── scripts/        # Scripts de instalación local (.bat)
├── build.sh        # Script de build para Render
├── render.yaml     # Configuración de Render
└── docker-compose.yml
```

## Despliegue actual

| Servicio        | Plataforma | URL                                  |
|-----------------|------------|--------------------------------------|
| Backend + Admin | Render     | https://raloz-web.onrender.com       |
| Tienda web      | Cloudflare | https://ralozcol-web.pages.dev       |
| Base de datos   | Supabase   | PostgreSQL                           |
| Pagos           | MercadoPago| Credenciales de producción           |

## Variables de entorno (Render)

```env
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=...
MP_ACCESS_TOKEN=APP_USR-...
MP_REDIRECT_URL=https://ralozcol-web.pages.dev
BACKEND_URL=https://raloz-web.onrender.com
CORS_ORIGINS=https://ralozcol-web.pages.dev
NODE_VERSION=18
PYTHON_VERSION=3.11
```

## Correr localmente

### Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
# Crear .env con las variables (ver .env.example)
python run.py
```

Backend disponible en: `http://localhost:5000`

### Modo prueba (sin cobrar dinero real)

El archivo `.env.test` contiene las credenciales sandbox de MercadoPago.
Para activarlo localmente:

```bash
cd backend
# Windows:
copy .env.test .env
# Mac/Linux:
cp .env.test .env

python run.py
```

Tarjetas de prueba para el checkout:

| Tarjeta    | Número               | CVV | Nombre | Resultado  |
|------------|----------------------|-----|--------|------------|
| Mastercard | 5031 7557 3453 0604  | 123 | APRO   | ✅ Aprobado |
| Visa       | 4509 9535 6623 3704  | 123 | APRO   | ✅ Aprobado |
| Cualquiera | 4000 0000 0000 0002  | 123 | OTHE   | ❌ Rechazado|

> ⚠️ El `.env.test` está en `.gitignore` — nunca se sube a GitHub.

### Frontend (panel admin)

```bash
cd frontend
npm install
npm run dev
```

Panel disponible en: `http://localhost:5173`

## Estructura del backend

```
backend/app/
├── api/            # Endpoints por módulo
│   ├── tienda.py   # Tienda pública (sin auth)
│   ├── auth.py
│   ├── facturas.py
│   ├── stock.py
│   ├── productos.py
│   ├── colegios.py
│   └── ...
├── models/         # Modelos SQLAlchemy
├── services/       # Lógica de negocio
└── utils/
```

## Endpoints públicos (sin autenticación)

| Método | Ruta                           | Descripción                        |
|--------|--------------------------------|------------------------------------|
| GET    | /api/health                    | Estado del servidor                |
| GET    | /api/tienda/colegios           | Colegios con catálogo activo       |
| GET    | /api/tienda/catalogo/{id}      | Productos y stock por colegio      |
| POST   | /api/tienda/pedido             | Crear pedido + link MercadoPago    |
| GET    | /api/tienda/pedido/{ref}       | Consultar estado de un pedido      |
| POST   | /api/tienda/mp/webhook         | Webhook de confirmación de pago    |

## Flujo de pago

```
Frontend tienda
    ↓ POST /api/tienda/pedido
Backend valida stock
    ↓
Backend crea preferencia MercadoPago
    ↓ retorna pago_url
Frontend redirige a MercadoPago
    ↓ usuario paga
MercadoPago → POST /api/tienda/mp/webhook
    ↓
Backend actualiza pedido → genera factura → descuenta stock
```

## Documentación adicional

Ver carpeta `/docs/`:
- `GUIA_PASO_A_PASO.md` — Despliegue completo paso a paso
- `RENDER_DEPLOY.md` — Guía rápida de Render
- `INSTRUCCIONES_COMPLETAS.md` — Instrucciones con código
