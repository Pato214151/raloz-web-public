# RALOZ — Textos para CV / LinkedIn / Portafolio

Copia y pega lo que necesites. Hay versiones en **español** e **inglés**, de
distintas longitudes. Ajusta nombres/fechas a tu gusto.

---

## 🇪🇸 ESPAÑOL

### Una línea (para titular o intro)
> Plataforma full-stack de e-commerce en producción (Flask + React + PostgreSQL) con pagos, facturación, bot de WhatsApp y auditoría de seguridad.

### Párrafo corto (LinkedIn "Acerca de" / portafolio)
> Diseñé y desarrollé de punta a punta un sistema de comercio electrónico real para un negocio de uniformes escolares: una tienda pública (PWA), un panel administrativo/POS en React y un backend en Flask con API REST. Integra pagos con MercadoPago (webhooks firmados), facturación electrónica con PDF en memoria, notificaciones por correo y un bot de WhatsApp. Está desplegado en producción (Render + Cloudflare + Supabase) e incluye una auditoría de seguridad documentada (JWT con revocación, control de acceso por roles, anti-XSS/SQLi, rate limiting). ~23.000 líneas de código.

### Descripción de proyecto (LinkedIn → Proyectos)
> **RALOZ — Sistema de gestión y tienda online**
> Sistema full-stack para un negocio de uniformes escolares en Bogotá, en
> producción. Cubre el ciclo completo: catálogo, compra online, pago,
> facturación, inventario, fabricación bajo pedido, entrega y soporte.
>
> - **Frontend tienda:** HTML/CSS/JS (ES Modules) como PWA con modo offline.
> - **Panel admin/POS:** React + Vite con rutas protegidas por rol.
> - **Backend:** Flask + SQLAlchemy, API REST con 20 módulos y 25 modelos.
> - **Integraciones:** MercadoPago, Brevo (email), Google OAuth, WhatsApp.
> - **Seguridad:** auditoría completa (JWT + blocklist, roles, HMAC, anti-XSS/SQLi, rate limiting, HSTS/CSP).
> - **Infra:** Render, Cloudflare Pages, Supabase, Docker.

### Viñetas para el CV (orientadas a logros)
- Desarrollé de extremo a extremo una plataforma de e-commerce **en producción** (~23.000 LOC) con tienda pública, panel administrativo y backend REST.
- Integré **pagos con MercadoPago** mediante webhooks con **firma HMAC** e idempotencia, generando facturas en PDF y notificaciones automáticas.
- Diseñé un backend modular en **Flask** (20 módulos, 25 modelos) con autenticación **JWT por roles** y control de acceso.
- Implementé una **tienda PWA offline-first** que sigue funcionando si el backend está caído (fallback estático + Service Worker).
- Realicé una **auditoría de seguridad** y corregí vulnerabilidades (XSS, control de acceso, precios del lado del cliente, CORS, rate limiting) y agregué respaldos automáticos de base de datos.
- Construí un **bot de WhatsApp** (máquina de estados) para soporte/garantías y avisos automáticos del estado del pedido.

---

## 🇬🇧 ENGLISH

### One-liner (headline / intro)
> Full-stack e-commerce platform in production (Flask + React + PostgreSQL) with payments, invoicing, a WhatsApp bot and a documented security audit.

### Short paragraph (LinkedIn "About" / portfolio)
> I designed and built end to end a real e-commerce system for a school-uniform business: a public storefront (PWA), a React admin/POS panel, and a Flask REST API backend. It integrates MercadoPago payments (signed webhooks), e-invoicing with in-memory PDFs, email notifications and a WhatsApp bot. It runs in production (Render + Cloudflare + Supabase) and includes a documented security audit (JWT with revocation, role-based access control, anti-XSS/SQLi, rate limiting). ~23,000 lines of code.

### Project description (LinkedIn → Projects)
> **RALOZ — Management system & online store**
> A full-stack system for a school-uniform business in Bogotá, running in
> production. It covers the full lifecycle: catalog, online purchase, payment,
> invoicing, inventory, made-to-order production, delivery and support.
>
> - **Storefront:** HTML/CSS/JS (ES Modules) as an offline-capable PWA.
> - **Admin/POS panel:** React + Vite with role-based protected routes.
> - **Backend:** Flask + SQLAlchemy REST API with 20 modules and 25 models.
> - **Integrations:** MercadoPago, Brevo (email), Google OAuth, WhatsApp.
> - **Security:** full audit (JWT + blocklist, roles, HMAC, anti-XSS/SQLi, rate limiting, HSTS/CSP).
> - **Infra:** Render, Cloudflare Pages, Supabase, Docker.

### CV bullet points (achievement-oriented)
- Built end to end a **production** e-commerce platform (~23,000 LOC): public store, admin panel and REST backend.
- Integrated **MercadoPago payments** via **HMAC-signed**, idempotent webhooks, generating PDF invoices and automatic notifications.
- Architected a modular **Flask** backend (20 modules, 25 models) with **role-based JWT** authentication and access control.
- Shipped an **offline-first PWA** storefront that keeps working when the backend is down (static fallback + Service Worker).
- Ran a **security audit** and remediated vulnerabilities (XSS, access control, client-side pricing, CORS, rate limiting) and added automated database backups.
- Built a **WhatsApp bot** (state machine) for support/warranty handling and automatic order-status updates.

---

## 🎤 Para entrevistas (puntos de conversación)

- **Decisión técnica:** "La tienda es offline-first porque el backend está en
  Render gratis (cold start ~90 s); con Service Worker + catálogo estático de
  respaldo el cliente nunca ve un sitio caído."
- **Seguridad:** "El precio se calcula en el servidor, nunca se confía en el
  cliente; el webhook de pago valida firma HMAC y es idempotente."
- **Diseño de datos:** "Los precios van por grupo de talla y el stock por talla
  individual; las reservas expiran solas con un hilo daemon para no bloquear
  inventario."
- **Resultado:** "Es un sistema real en uso, no un proyecto de tutorial."

## 🛠️ Habilidades demostradas
`Python` · `Flask` · `SQLAlchemy` · `REST API` · `React` · `Vite` · `JavaScript`
· `PostgreSQL` · `JWT/OAuth` · `Integración de pagos` · `Webhooks` · `Docker`
· `CI/CD` · `Seguridad web` · `PWA` · `Arquitectura de software`
