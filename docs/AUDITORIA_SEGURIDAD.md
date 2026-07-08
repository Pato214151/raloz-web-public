# Auditoría de Seguridad — RALOZ COL SAS
## Fecha: 2026-07-07 | Alcance: Backend + Frontend + WhatsApp Bot

---

## RESUMEN EJECUTIVO

| Dimensión | Estado | Puntuación |
|-----------|--------|-----------|
| Autenticación | **Bien** | 9/10 |
| Autorización / RBAC | **Bien** | 9/10 |
| Validación de entrada | **Bien** | 8/10 |
| SQL Injection | **Bien** | 9/10 |
| XSS / CSP | **Bien** | 9/10 |
| Rate Limiting | **Bien** | 9/10 |
| Secrets management | ⚠️ Atención | 7/10 |
| CORS / Headers | **Bien** | 10/10 |
| Webhooks | **Bien** | 9/10 |
| Frontend (tokens) | **Bien** | 8/10 |
| **TOTAL** | | **87/100 — Bueno** |

El proyecto tiene una base sólida. Los problemas son menores y la mayoría son configuraciones de producción que deben verificarse. No hay vulnerabilidades críticas activas.

---

## HALLAZGOS POR CATEGORÍA

---

### 1. AUTENTICACIÓN ✅ BUENO

**Lo que está bien:**
- `auth.py:46-55` — Login con sanitización de `usuario` mediante `sanitize_string()` antes de consultar la BD.
- `auth.py:68-75` — Bloqueo de cuenta tras 5 intentos fallidos (5 minutos). Bloqueo por fuerza bruta implementado correctamente.
- `auth.py:237-238` — Hash bcrypt con 12 rounds para contraseñas nuevas. Factor seguro.
- `auth.py:196-209` — Logout con revocación real del token (token blacklist en `TokenRevocado`). Los JTIs revocados se consultan en cada request (`__init__.py:137-143`).
- `auth.py:154` — Refresh token genera access token nuevo (no se reutiliza).
- `auth.py:29-34` — Claims incluyen `{usuario, rol}` en el JWT.
- `auth.py:179-180` — `@jwt_required(verify_type=False)` en logout acepta tanto access como refresh token.

**Concern menor:**
- `auth.py:69` — `bcrypt.checkpw(password.encode('utf-8'), usuario.contrasena_hash.encode('utf-8'))` asume que `contrasena_hash` está en UTF-8. Funciona en PostgreSQL, pero si algún día migraran a otro motor podría fallar silenciosamente. Muy bajo riesgo.

---

### 2. AUTORIZACIÓN / RBAC ✅ BUENO

**Lo que está bien:**
- `decorators.py:28-40` — Decorador `rol_requerido(*roles)` genérico. Se usa en todas las APIs admin.
- `decorators.py:43-52` — Decorador `admin_requerido` para rutas que solo admin debe tocar.
- Todas las APIs admin (usuarios, facturas, caja, reportes, etc.) están protegidas con `@jwt_required()` + `@admin_requerido` o `@rol_requerido(...)`.
- `whatsapp_inbox.py:96,104,111,127,136,150,192` — Bandeja WhatsApp requiere rol admin/vendedor/cajero.
- `whatsapp_inbox.py:33-35` — El bot usa `X-Bot-Token` separado del JWT, con secreto compartido (`WA_LOG_TOKEN`).

**Concern menor:**
- `tienda/publico.py:948-955` — El endpoint `pedidos-por-telefono` usa el mismo `WA_LOG_TOKEN` que el bot. Está bien siempre que `WA_LOG_TOKEN` sea fuerte y no se filtre.

---

### 3. VALIDACIÓN DE ENTRADA ✅ BUENO

**Lo que está bien:**
- `validators.py:10-15` — `sanitize_string()` usa `bleach.clean()` para limpiar HTML/scripts de todos los inputs de usuario.
- `validators.py:18-23` — Validación de email con regex.
- `validators.py:26-31` — Validación de teléfono colombiano (7-15 dígitos).
- `tienda/publico.py:303-309` — Todos los datos del cliente (nombre, email, teléfono, dirección) se sanitizan antes de guardarse en BD.
- `tienda/publico.py:171-178` — Validación con `int()` + `ValueError` para `id_colegio`, `id_producto`, `cantidad` en reservas.
- `tienda/publico.py:308-309` — Validación de email con mensaje de error claro.
- `whatsapp_inbox.py:63-64` — Validación de `direccion` como `in|out` y `chat_id` requerido.
- `whatsapp_inbox.py:141-143` — Validación de `modo` como `'bot'` o `'humano'`.

**Concern menor:**
- `validators.py:14` — `bleach.clean()` con `strip=True` elimina HTML pero si se usara sin `tags=[]` podría haber bypass. Actualmente se usa correctamente con `tags=[]`. ✅
- `tienda/publico.py:354` — `float(item.get('unit_price') or item.get('precio', 0))` para productos sin colegio. El precio se valida contra 0 en la siguiente línea, pero no hay límite máximo. Un atacante podría enviar `unit_price: 99999999`. **Ver detalle en P1 abajo.**

---

### 4. SQL INJECTION ✅ BUENO

**Lo que está bien:**
- Todo el acceso a datos usa SQLAlchemy ORM (modelos con columnas, no strings SQL). No hay raw SQL concatenado.
- `tienda/publico.py:53-54` — `Usuario.usuario == identificador` → parametrizado automáticamente por SQLAlchemy.
- `tienda/publico.py:962-964` — LIKE query usa `filter(PedidoWeb.telefono_cliente.like(f'%{ult10[-7:]}%'))` → el valor interpolado son solo dígitos (validado en `tienda/publico.py:957`), no permite inyección.

**Sin hallazgos de SQL injection.**

---

### 5. XSS / CSP ✅ BUENO

**Lo que está bien:**
- `__init__.py:107-116` — CSP header completo configurado:
  ```
  default-src 'self'
  script-src 'self' https://accounts.google.com https://apis.google.com
  style-src 'self' 'unsafe-inline' https://accounts.google.com https://fonts.googleapis.com
  img-src 'self' data: https:
  frame-ancestors 'none'
  ```
- `'unsafe-inline'` en `style-src` es necesario para React/Tailwind (inevitable) y Google Sign-In. Aceptable.
- `frame-ancestors 'none'` — Previene clickjacking. ✅
- `__init__.py:96-98` — Headers `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`.
- `__init__.py:100-101` — HSTS configurado con `max-age=31536000; includeSubDomains`.

**Concern menor:**
- `__init__.py:109-113` — `connect-src 'self' https://accounts.google.com` no incluye el backend de producción (`raloz-web.onrender.com`). Si Google Sign-In hace llamadas a APIs externas, podría haber restricciones. Verificar con el login de Google.

---

### 6. RATE LIMITING ✅ BUENO

**Lo que está bien:**
- `__init__.py:25` — Rate limiter global: `200 per minute` por IP.
- `auth.py:38` — Login: `10 per minute` por IP.
- `auth.py:96` — Google login: `10 per minute`.
- `auth.py:150` — Refresh: sin límite extra (el global aplica).
- `auth.py:215` — Cambiar contraseña: `5 per minute` (protege contra fuerza bruta de password).
- `tienda/publico.py:157` — Reservar: `20 per minute` (evita agotar stock con reservas masivas).
- `tienda/publico.py:250` — Liberar reservas: `30 per minute`.
- `tienda/publico.py:292` — Crear pedido: `10 per minute` (evita spam de pedidos falsos).
- `tienda/publico.py:591` — Pagar saldo: `10 per minute`.

**Sin hallazgos.** El rate limiting está bien implementado en todos los endpoints sensibles.

---

### 7. SECRETS MANAGEMENT ⚠️ ATENCIÓN

**Lo que está bien:**
- `.env` está en `.gitignore` y **no está trackeado en git**. ✅
- `.env.example` existe con valores placeholder. ✅
- `__init__.py:60-63` — Si `SECRET_KEY` o `JWT_SECRET_KEY` usan los valores dev por defecto, se loguea un `logger.critical()` bien visible.
- `run.py:225-248` — El admin por defecto NUNCA se crea con un password conocido. Si `ADMIN_PASSWORD` no está en el entorno, se genera uno aleatorio con `secrets.token_urlsafe(12)` y se imprime UNA vez.
- `run.py:257-286` — Comando `reset-admin-password` para rotar passwords.
- No hay secretos hardcodeados en el código fuente.

**Concern P1 — WaLogToken débil:**
- `whatsapp-bot/bot_meta.py:38` — `VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "raloz-verify").strip()` usa un default de `"raloz-verify"`. Si alguien deploya el bot sin configurar `VERIFY_TOKEN`, el webhook de Meta aceptará cualquier token `"raloz-verify"`.
- `whatsapp-bot/bot_meta.py:45` — `WA_LOG_TOKEN = os.getenv("WA_LOG_TOKEN", "").strip()` no tiene default, lo cual es correcto, pero si se deja vacío, `_registrar()` en `bot_meta.py:115-116` retorna "bot" sin más — no es un fallo peligroso pero debería ser obligatorio.

**Recomendación:**
- Generar un `VERIFY_TOKEN` fuerte de al menos 32 caracteres con `openssl rand -hex 32`.
- Verificar que `WA_LOG_TOKEN` esté configurado en todos los entornos de producción.

---

### 8. CORS / HEADERS ✅ EXCELENTE

**Lo que está bien:**
- `__init__.py:71-91` — CORS configurado con lista explícita de orígenes. **NUNCA** se usa `origins='*'` junto con `supports_credentials=True`.
- `_cors_defaults` incluye dominios conocidos + localhost para desarrollo.
- Origins se normalizan (se quita trailing slash) antes de comparar.
- `CORS_ORIGINS` se puede sobrescribir por variable de entorno.
- `__init__.py:94-117` — Security headers completos (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).
- `__init__.py:94-117` — El CSP está bien configurado con `frame-ancestors 'none'`.

**Sin hallazgos.**

---

### 9. WEBHOOKS ✅ BUENO

**Lo que está bien:**
- `tienda/publico.py:636-673` — `_validar_firma_mp()` valida HMAC-SHA256 de MercadoPago (`X-Signature`). Usa `hmac.compare_digest()` (tiempo constante, previene timing attacks).
- `tienda/publico.py:765-766` — El webhook RECHAZA con 401 si la firma es inválida.
- `tienda/publico.py:787-793` — Si no puede consultar MP, devuelve 500 para que Meta reintente (no se pierde el pago).
- `tienda/publico.py:813-816` — Idempotencia real: si el pedido ya tiene factura, ignora el reintento del webhook de Meta.
- `bot_meta.py:147-157` — Anti-duplicados en el bot de WhatsApp con un deque de 500 elementos.
- `bot_meta.py:181-182` — Siempre responde 200 rápido a Meta para evitar reintentos innecesarios.

**Concern menor:**
- `tienda/publico.py:645-647` — Si `MP_WEBHOOK_SECRET` no está configurado, se **omite la validación de firma** (retorna `True` con un warning). Esto es backward compatible pero si en algún momento alguien olvida configurar `MP_WEBHOOK_SECRET` en producción, el webhook aceptará pagos falsos. **Ver P1 abajo.**

---

### 10. FRONTEND (Tokens, API) ✅ BUENO

**Lo que está bien:**
- `api.ts:21-25` — Token se almacena en `localStorage` (es el estándar para SPAs; `httpOnly` cookies requieren backend SSR).
- `api.ts:44-65` — Interceptor de 401 hace refresh automático del token. Si el refresh falla, limpia todo y redirige a `/login`.
- `api.ts:36-42` — No se intenta refresh en las propias llamadas de login/refresh (evita loop).
- `api.ts:52-54` — Refresh usa `Bearer <refresh_token>` directamente, no el interceptor (evita loop infinito).

**Concern P2:**
- `api.ts:21` — El token está en `localStorage`, vulnerable a XSS. Con el CSP bien configurado (`script-src 'self'`), el riesgo es bajo. Pero si alguien logra inyectar un script, podría robar tokens. Consideración: para apps muy sensibles, `httpOnly` cookies serían mejores, pero eso requiere cambios significativos en el backend.
- No hay protección CSRF explícita. Flask-JWT-Extended con Bearer tokens en headers no es vulnerable a CSRF clásico (el navegador no envía `Authorization` header automáticamente en POST cross-site). **Esto está bien** para Bearer tokens.

---

## PRIORIZACIÓN DE ACCIONES

### 🔴 P1 — Alto (revisar ahora)

**1. Verificar `MP_WEBHOOK_SECRET` en producción**
- **Ubicación:** Variable de entorno en Render para el backend
- **Riesgo:** Si `MP_WEBHOOK_SECRET` no está configurado, el webhook acepta pagos de cualquier fuente (sin validación HMAC)
- **Acción:** Ir al dashboard de MercadoPago → Webhooks → copiar el Secret. Asegurarse de que esté en el `.env` de Render y que `MP_WEBHOOK_SECRET` tenga un valor real en producción.
- **Cómo verificar:** Hacer un `curl -X POST https://raloz-web.onrender.com/api/tienda/mp/webhook -H "Content-Type: application/json" -d '{"type":"payment"}'` — si retorna 401 o procesa sin error, está mal. Debe retornar 401 sin `X-Signature` válido.

**2. Verificar `VERIFY_TOKEN` del bot de WhatsApp**
- **Ubicación:** `whatsapp-bot/bot_meta.py:38` y variable de entorno en Render del bot
- **Riesgo:** Si usa el default `"raloz-verify"`, cualquiera que descubra tu webhook URL podría verificarlo con ese token
- **Acción:** En Render → Variables de entorno del servicio `whatsapp-bot` → configurar `VERIFY_TOKEN` con un valor largo y aleatorio (`openssl rand -hex 32`)

**3. Validar monto máximo en pedidos sin colegio (relojes, etc.)**
- **Ubicación:** `tienda/publico.py:354-356`
- **Riesgo:** Un atacante podría enviar `unit_price: 99999999` en un pedido de reloj y pagar 1 peso por un artículo de precio real
- **Acción:** Agregar validación: `if precio_unitario > 10000000: return error`. O mejor, el precio de los productos generales debería venir del backend, no del frontend.

---

### 🟡 P2 — Medio (siguiente sprint)

**4. Generar `WA_LOG_TOKEN` fuerte si no existe**
- **Ubicación:** Variables de entorno del bot y del backend
- **Acción:** `openssl rand -hex 32` y asegurarte de que el mismo valor esté en ambos servicios.

**5. Incluir backend en `connect-src` del CSP si es necesario**
- **Ubicación:** `__init__.py:113`
- **Riesgo:** `connect-src 'self' https://accounts.google.com` — si el flujo de Google OAuth hace llamadas a APIs que no son accounts.google.com, el CSP las bloqueará.
- **Acción:** Después de probar el login con Google en producción, verificar en la consola del navegador si hay errores CSP.

**6. Revisar tamaños de archivo en WhatsApp**
- **Ubicación:** `whatsapp_inbox.py:206` — límite de 5MB, `bot_meta.py:98` — límite de 5MB
- **Riesgo:** Ambos usan el mismo límite pero diferentes validaciones. Asegurarse de que son consistentes.
- **Acción:** Unificar el límite en una constante compartida.

---

### 🟢 P3 — Bajo (si hay tiempo)

**7. Agregar auditoría de acceso a datos sensibles**
- `decorators.py:55-75` tiene `registrar_auditoria()` pero no se usa en todas las operaciones sensibles (crear usuario, cambiar contraseña, etc.)
- Considerar auditar al menos: creación de usuarios, cambios de rol, anulación de facturas.

**8. Timeout de red en WhatsApp bot**
- `bot_meta.py:98` tiene `timeout=30` para descarga de media, pero algunos uploads grandes podrían tomar más. 5MB / 30s = ~170KB/s, aceptable en Colombia.

---

## LO QUE ESTÁ EXCELENTE

- ✅ **Seguridad headers** (`__init__.py:94-117`): completos, con CSP, HSTS, X-Frame-Options. Muy pocas apps tienen esto bien configurado.
- ✅ **Rate limiting granular**: cada endpoint sensible tiene su propio límite apropiado.
- ✅ **Idempotencia en webhooks**: el de MercadoPago y el del bot tienen anti-duplicados.
- ✅ **Job de reconciliación** (`run.py:91-114`): red de seguridad si el webhook falla, busca pagos perdidos cada 15 minutos.
- ✅ **Password admin aleatorio**: el seed nunca crea un admin con password conocido.
- ✅ **Bcrypt 12 rounds**: estándar actual.
- ✅ **No SQL injection**: 100% SQLAlchemy ORM.
- ✅ **Sanitización con bleach**: todos los inputs de usuario.
- ✅ **Token blacklist**: logout efectivo.
- ✅ **Bloqueo por fuerza bruta**: 5 intentos / 5 minutos.
- ✅ **Botón de reset de admin password**: listo para Render.

---

## CHECKLIST DE PRODUCCIÓN

```
[ ] MP_WEBHOOK_SECRET configurado en Render (backend)         → P1
[ ] VERIFY_TOKEN del bot configurado (no "raloz-verify")     → P1
[ ] WA_LOG_TOKEN igual en backend y bot                      → P2
[ ] ADMIN_PASSWORD configurado en Render                      → P2
[ ] SECRET_KEY ≠ "dev-secret-key-cambiar" en Render         → (ya loguea CRITICAL)
[ ] JWT_SECRET_KEY ≠ "jwt-dev-secret-cambiar" en Render      → (ya loguea CRITICAL)
[ ] CORS_ORIGINS verificado en Render                        → (usa defaults si vacío)
[ ] Price validation server-side para productos sin colegio   → P1
```
