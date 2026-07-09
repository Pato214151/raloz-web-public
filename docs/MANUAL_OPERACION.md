# Manual de operación — Sistema RALOZ COL S.A.S

Guía práctica para operar el negocio día a día y para mantener el sistema.
Dividido en dos partes: **Operación diaria** (para todo el equipo) y
**Administración y técnica** (para el dueño / responsable de TI).

> Última actualización: 2026-07-09.

---

## 0. Panorama: las piezas del sistema

| Pieza | Qué es | Dónde vive |
|---|---|---|
| **Panel / POS** | Donde el equipo factura, cobra, maneja pedidos, stock, WhatsApp y citas. | `https://raloz-web.onrender.com` (Render) |
| **Tienda web** | La tienda online para clientes. | `https://ralozcolsas.com` (Cloudflare Pages) |
| **Bot de WhatsApp** | Responde solo a los clientes por WhatsApp. | Render (`raloz-bot`) + Meta WhatsApp Cloud API |
| **Base de datos** | Donde se guarda todo (facturas, stock, pedidos…). | PostgreSQL (Supabase) |

Servicios de apoyo: **UptimeRobot** (mantiene despiertos el bot y el backend),
**Brevo** (envía correos), **MercadoPago** (pagos de la tienda), **Meta** (WhatsApp).

---

# PARTE A — Operación diaria (todo el equipo)

## 1. Entrar al panel
1. Abre `https://raloz-web.onrender.com`.
2. Inicia sesión con tu usuario y contraseña.
3. Roles: **administrador** (todo), **vendedor** (ventas, pedidos, clientes),
   **cajero** (facturar, cobrar, caja). Cada rol ve solo lo que le toca.

> Si la primera carga tarda unos segundos, es normal (el servidor estaba en reposo).

## 2. Vender y cobrar
- **Nueva Venta** (`/facturacion`): arma la factura, elige colegio, productos y tallas.
- **Registrar Pago** (`/pagos`): abona a una factura (total o parcial).
- **Buscar Facturas** (`/buscar`): encuentra una venta por número o cliente.
- **Por Cobrar** (`/cuentas`): quién debe y cuánto.
- **Caja** (`/caja`): abre/cierra caja y ve movimientos del día.

## 3. Pedidos (del pedido a la entrega)
Menú **Pedidos**:
1. **Centro de Pedidos** (`/pedidos-online`): pedidos que llegan de la tienda web.
2. **Fabricación**: prendas que hay que mandar a hacer.
3. **Empaque**: pedidos listos para empacar.
4. **Por Entregar**: lo que falta entregar al cliente.

El **badge rojo** en el menú avisa cuántos pedidos nuevos hay sin atender.

## 4. Bandeja de WhatsApp
Menú **Comunicación → WhatsApp**. Aquí ves las conversaciones con los clientes.

- **Modo Bot vs. Yo (humano)**: cada chat lo atiende el bot automáticamente.
  Si quieres responder tú, abre el chat y pulsa **"Yo"** → el bot se calla en ese
  chat. Para devolvérselo al bot, pulsa **"Bot"**.
  > ⚠️ Si un chat quedó en **"Yo" (humano)**, el bot NO responde ahí. Si un cliente
  > se queja de que "no le contestan", revisa que su chat no esté en modo humano.
- **Enviar**: escribe y Enter (Shift+Enter = salto de línea). También puedes mandar
  **foto** (ícono de imagen) y usar **respuestas rápidas** (botones de plantillas).
- **Badge de no leídos**: el número verde indica mensajes sin leer.

## 5. Citas
Menú **Comunicación → Citas**: agenda de citas. Al confirmar una cita, al cliente
le llega un WhatsApp de confirmación automático.

---

# PARTE B — Administración y técnica (dueño / TI)

## 6. Cómo se publica cada cosa (deploys)

Todo se despliega **solo** al hacer `git push` a la rama `main` del repo correspondiente.

| Qué | Repo GitHub | Se despliega en | Al hacer push a `main` |
|---|---|---|---|
| Backend + Panel | `Pato214151/raloz-web` | Render | Redeploy automático |
| Bot de WhatsApp | `Pato214151/raloz-whatsapp-bot` | Render | Redeploy automático |
| Tienda web | `Pato214151/ralozcol-web` | Cloudflare Pages | Deploy automático |

La tienda se edita en `D:\proyectos\raloz-col\Raloz\` (ya es un repo git conectado).
Flujo: editar → `git add -A` → `git commit -m "..."` → `git push`.

> El código vivo está en `D:\proyectos\raloz-col`, NO en las copias de OneDrive.

## 7. Servicios y cuentas (dónde está cada cosa)

| Servicio | Para qué | Notas |
|---|---|---|
| **Render** | Corre el backend y el bot | Plan gratis: se duermen sin tráfico (ver §9) |
| **Cloudflare Pages** | Sirve la tienda | Deploy al push a `ralozcol-web` |
| **Supabase** | Base de datos PostgreSQL | El backend conecta por `DATABASE_URL` |
| **Meta (WhatsApp Cloud API)** | Envía/recibe WhatsApp | Token `WHATSAPP_TOKEN`, `PHONE_NUMBER_ID` |
| **UptimeRobot** | Ping cada 5 min a `/health` para no dormir | 2 monitores: bot y backend |
| **Brevo** | Correos internos (avisos, reportes) | `BREVO_API_KEY` |
| **MercadoPago** | Pagos de la tienda | Webhook de pago al backend |

## 8. Mantenimiento automático (respaldos + monitoreo)

Cada **lunes 3:00 a.m.** corre solo un workflow (*Weekly Maintenance* en GitHub
Actions del repo `raloz-web`) que:
1. Hace un **respaldo** de la base de datos.
2. Corre el **diagnóstico de integridad** (huérfanos, kardex, pagos).
3. Revisa **alertas de stock bajo** antes de temporada.
4. Te avisa por **email (Brevo)** si algo sale mal o si hay hallazgos nuevos.

- El respaldo se guarda como **artifact** en GitHub Actions (90 días).
  Para descargarlo: GitHub → repo `raloz-web` → Actions → *Weekly Maintenance* →
  una corrida → sección Artifacts.
- **Requiere** el secret `DATABASE_URL` en GitHub (Settings → Secrets → Actions).
  Para los correos, además: `BREVO_API_KEY`, `EMAIL_REMITENTE`, `EMAIL_AVISO_TO`.
- Correr a mano: Actions → *Weekly Maintenance* → **Run workflow**.

Otros scripts útiles (en `backend/tools/`, se corren a mano):
- `analisis_temporada.py` — cuánto fabricar por talla/colegio antes de temporada.
- `reporte_semanal.py` — resumen de ventas/pagos/pedidos de la semana.
- `revisar_precios_combos.py` — revisa que los uniformes completos cuadren con la suma.
- `alertas_stock.py` — items por agotarse.

## 9. Problemas comunes y cómo resolverlos

**"El bot de WhatsApp no responde / escribo hola y nada".**
1. Casi siempre es porque el servicio **se durmió** (Render gratis) o el token de Meta.
2. Revisa que **UptimeRobot** esté activo pingeando `raloz-bot.onrender.com/health`.
3. Revisa en el panel que el chat no esté en **modo "Yo" (humano)**.
4. Si sigue, revisa en Meta que el **token de WhatsApp** no esté vencido y que el
   **webhook** esté suscrito a `messages`.

**"La página o el panel cargan lento la primera vez".**
Es el servicio despertando de reposo (Render gratis). Con UptimeRobot activo, casi no pasa.

**"Salieron errores 500 intermitentes en el panel".**
Suelen ser conexiones de base viejas cuando el servidor despierta; se resuelven solos.
El código ya recicla conexiones (`pool_pre_ping`).

## 10. Seguridad — cosas que cuidar
- **`APP_SECRET`** (bot, en Render): activa la verificación de firma de Meta en el
  webhook. Debe ser el **App Secret exacto** de la app de Meta. ⚠️ Si lo pones mal,
  el bot rechaza todos los mensajes. Al ponerlo, manda un "hola" para confirmar.
- **Claves** `JWT_SECRET_KEY` y `SECRET_KEY` (backend, en Render): son largas y
  secretas. Cambiarlas cierra todas las sesiones abiertas (hay que re-loguearse).
- No subir tokens ni contraseñas a git (los `.env` están en `.gitignore`).

---

## Contactos y accesos (llenar)
- Dueño / admin principal: ______
- Cuenta GitHub: `Pato214151`
- Panel Render: ______
- Panel Cloudflare: ______
- Meta / WhatsApp Business: ______

> Mantén este manual actualizado cuando cambie un proceso o un servicio.
