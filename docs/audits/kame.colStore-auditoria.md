# AUDITORÍA TÉCNICA Y COMERCIAL — KAMECOL

## 1. RESUMEN EJECUTIVO

KameCol es una plataforma de e-commerce colombiana de streetwear construida sobre Django 5.2 + Next.js 14, desplegada en Render (backend) y Vercel (frontend), con PostgreSQL gestionado, almacenamiento en Cloudflare R2 y pagos mediante Wompi.

La plataforma está **en producción funcional** con un flujo comercial completo: catálogo → carrito → checkout → pago → confirmación → envío. Implementa patrones sólidos de concurrencia (locks atómicos en stock), seguridad (2FA, firma de webhooks, rate limiting) y observabilidad (Sentry, analytics interno, GA4, Meta Pixel).

**No existe infraestructura de atención al cliente ni sistema de agentes inteligentes.** El canal principal de soporte es WhatsApp vía enlaces directos. Esto representa la mayor oportunidad para JARVIS.

---

## 2. ARQUITECTURA

```
┌──────────────────────────────────────────────────────────────┐
│                      INTERNET PÚBLICO                        │
└──────────────────────────┬───────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
       ┌────▼─────┐              ┌────────▼───────┐
       │  Vercel  │              │  Render.com    │
       │ Next.js  │──/api/*──▶  │  Django+Gunicorn│
       │ 14 (App  │  proxy      │  Python 3.11   │
       │ Router)  │              └────────┬───────┘
       └──────────┘                       │
                                   ┌──────┴──────┐
                                   │ PostgreSQL  │
                                   │ (managed)   │
                                   └─────────────┘

Servicios externos:
  ├── Wompi (pagos: tarjeta, Nequi, PSE, Daviplata, QR)
  ├── Resend (email transaccional)
  ├── Cloudflare R2 (storage S3-compatible)
  ├── Sentry (monitoreo errores backend+frontend)
  ├── Google Analytics 4 (tracking)
  └── Meta Pixel (retargeting)
```

---

## 3. STACK TECNOLÓGICO

| Componente | Tecnología | Versión |
|---|---|---|
| Backend | Django + DRF | 5.2.17 / 3.15.2 |
| Frontend | Next.js (App Router) + React | 14.2.15 / 18.3.1 |
| Lenguaje backend | Python | 3.11.14 |
| Lenguaje frontend | TypeScript | 5.6.3 |
| Base de datos | PostgreSQL | 16 (Docker local) |
| Estado cliente | Zustand | 5.0.1 |
| Estilos | Tailwind CSS | 3.4.14 |
| Formularios | React Hook Form + Zod | 7.53.2 / 3.23.8 |
| Imágenes | django-imagekit + Pillow | 6.0.0 / 12.3.0 |
| Storage | boto3 + django-storages (Cloudflare R2) | 1.42.52 / 1.14.6 |
| Servidor WSGI | Gunicorn | 22.0.0 |
| Archivos estáticos | WhiteNoise | 6.11.0 |
| 2FA | django-otp + django-two-factor-auth | ≥1.4.0 / ≥1.16.0 |
| Monitoreo | Sentry SDK | ≥2.0.0 (backend), 10.48.0 (frontend) |
| E2E Testing | Playwright | 1.44.0+ |
| SAST | Bandit | ≥1.7.0 |
| CI/CD | GitHub Actions | 4 workflows |

---

## 4. MODELO DE NEGOCIO

### Flujo comercial reconstruido desde el código:

```
Departamento → Categoría (árbol) → Producto → Variantes (talla+color)
                                                    │
                                              InventoryPool
                                            (fuente de verdad
                                              del stock)
```

1. **Taxonomía**: Departamentos (Hombre/Mujer/Accesorios) → Categorías (árbol auto-referencial) → Productos (solo en categorías hoja).
2. **Variantes**: Controladas por `variant_schema` en la categoría: `size_color`, `jean_size`, `shoe_size`, `no_variant`.
3. **Inventario**: `InventoryPool` es la fuente de verdad. `ProductVariant.stock` es legacy/read-only.
4. **Precios**: Precio base en `Product.price`. Descuentos vía `DiscountRule` (porcentaje o monto fijo).
5. **Carrito**: Frontend (Zustand + localStorage). No hay modelo Cart en Django.
6. **Checkout**: El frontend envía items al backend. El backend **ignora precios del frontend** y recalcula desde la DB.
7. **Pagos**: Wompi widget (iframe). El backend nunca ve datos de tarjeta.
8. **Stock**: Se decrementa **únicamente** cuando Wompi confirma pago (APPROVED), no al crear la orden.
9. **Notificaciones**: Emails vía Resend (orden creada, pago confirmado, pago declinado, recordatorio, notificación al dueño).
10. **Envío**: Costo calculado por ciudad (Bogotá/Nacional). Gratis sobre umbral (≥170,000 COP). Tracking vía Servientrega.

---

## 5. CATÁLOGO Y PRODUCTOS

### Almacenamiento

- **Product**: `name`, `slug` (único), `description`, `price` (DecimalField), `category` (FK a hoja), `is_active`, `show_in_home_marquee`.
- **ProductVariant**: `product` (FK), `value` (talla), `color`, `is_active`. Constraint único: `(product, value, color)`.
- **ProductImage**: Por variante. Derivados ImageKit: thumb (420px), medium (1200px), large (1600px), email (JPEG).
- **ProductColorImage**: Imágenes reutilizables por color para productos `size_color`. Son la fuente primaria de imágenes para ropa.

### Gestión de variantes

- Sincronización automática vía signals: cuando se guarda un `InventoryPool` o `ProductColorImage`, se crean/actualizan/desactivan `ProductVariant` automáticamente.
- Para `size_color`: solo se crean variantes si el producto tiene imágenes para ese color.
- `variant_rules.py` define tallas permitidas (`XS`-`2XL`), colores canónicos, y tallas de zapatos (`36`-`42`).

### Cálculo de precios

- Precio base: `Product.price`.
- Descuento activo: `DiscountRule` con jerarquía: Producto (40) > Categoría (30) > Departamento (20) > Tienda (10).
- Tipos: porcentaje o monto fijo (COP).
- Ventana temporal: `starts_at` / `ends_at` (opcional).

### Disponibilidad

- Fuente de verdad: `InventoryPool.quantity` por `(category, value, color)`.
- Pool map: `get_pool_map(category_id)` → diccionario `{(value, color): qty}` en una sola query.
- Validación frontend: `POST /api/orders/stock-validate/` con debounce de 150ms.

### APIs públicas del catálogo

| Endpoint | Datos | Cache |
|---|---|---|
| `GET /api/navigation/` | Departamentos → Categorías activas | ISR 300s |
| `GET /api/products/` | Listado con filtros (category, department, search) | no-store |
| `GET /api/products/{slug}/` | Detalle con variantes, imágenes, descuento, stock | ISR 60s |
| `GET /api/homepage-banners/` | Banners hero | ISR 300s |
| `GET /api/homepage-promos/` | Promos (TOP/MID) | ISR 300s |
| `GET /api/homepage-marquee-products/` | Productos destacados | ISR 300s |
| `GET /api/homepage-story/` | Secciones editoriales | ISR 300s |

**Datos públicos**: nombre, slug, descripción, precio, imágenes, variantes (talla/color), stock disponible, descuento activo.
**Datos que requieren auth**: ninguno para lectura del catálogo. Todos los endpoints de catálogo son públicos.

### Valor para un asistente de ventas (JARVIS)

Un agente podría consumir directamente: navegación de categorías, búsqueda de productos, detalle de producto con stock en tiempo real, precios con descuentos activos, imágenes, y guías de tallas (`CategorySizeGuide`). Todo esto está disponible vía API pública sin autenticación.

---

## 6. INVENTARIO

- **Modelo**: `InventoryPool` — pool por categoría con `(value, color, quantity)`.
- **Ajustes**: `InventoryAdjustmentLog` registra cambios manuales con `previous_stock`, `new_stock`, `reason`, `adjusted_by`.
- **Operaciones bulk**: `process_bulk_stock_lines()` para carga masiva CSV.
- **Concurrencia**: `select_for_update()` en todas las operaciones de stock.
- **Admin endpoints**: CRUD de pools, bulk load, historial de ajustes.

---

## 7. FLUJO DE PEDIDOS

### Ciclo de vida completo:

```
PENDING_PAYMENT ──(Wompi APPROVED)──▶ PAID ──(admin marca)──▶ SHIPPED
       │                                 │
       │──(Wompi DECLINED/ERROR)──▶ CANCELLED
       │──(admin cancela)─────────▶ CANCELLED
       │                                 │
       └──(futuro)──────────────▶ REFUNDED
```

### Detalle por etapa:

1. **Creación** (`POST /api/orders/checkout/`):
   - Resuelve/crea Customer por `(document_type, cedula)`.
   - Crea Order con status `PENDING_PAYMENT`.
   - Genera `payment_reference`: `KAME-{order_id}-{BASE32_RANDOM}`.
   - Calcula shipping vía `calculate_shipping_cost()`.
   - Snapshot de datos del cliente en la orden.
   - **NO decrementa stock**.
   - Envía email "Pedido recibido".
   - Respuesta incluye `whatsapp_link` para soporte.

2. **Pago** (Wompi webhook → `POST /api/orders/wompi-webhook/`):
   - Valida firma SHA256.
   - Verifica monto vs total de la orden.
   - Si `APPROVED`: `confirm_order_payment()` con `select_for_update()`.
     - Decrementa `InventoryPool` (idempotente vía `stock_deducted_at`).
     - Envía emails post-commit: confirmación al cliente + notificación al dueño.
   - Si `DECLINED`/`ERROR`: cancela orden, envía email de pago declinado.

3. **Envío** (`POST /api/admin/orders/{ref}/ship/`):
   - Admin agrega `tracking_number` (Servientrega).
   - Crea `OrderStatusLog`.

4. **Cancelación** (`POST /api/admin/orders/{ref}/cancel/`):
   - Solo para `PENDING_PAYMENT`.
   - No se puede cancelar una orden pagada.

5. **Recordatorio** (`POST /api/admin/orders/{ref}/send-reminder/`):
   - Rate limit: 1 por 24 horas por orden.
   - Envía email con instrucciones de pago.

### Auditoría:
- `OrderStatusLog`: registra cada cambio de estado con timestamp y nota.
- `InventoryAdjustmentLog`: registra ajustes manuales de inventario.

---

## 8. PAGOS

### Integración Wompi

| Aspecto | Detalle |
|---|---|
| Proveedor | Wompi (Colombia) |
| Métodos | Tarjeta, Nequi, PSE, Daviplata, QR, Puntos Colombia |
| Modelo | Widget iframe (PCI compliant — backend nunca ve datos de tarjeta) |
| Firma widget | `SHA256(reference + amount_cents + COP + integrity_secret)` |
| Firma webhook | `SHA256(val1 + val2 + ... + timestamp + events_secret)` |
| Moneda | COP (pesos colombianos), convertidos a centavos (×100) |
| Idempotencia | `stock_deducted_at` previene doble deducción |

### Flujo:
1. Frontend solicita firma: `GET /api/orders/wompi-signature/?reference={ref}`
2. Frontend muestra widget Wompi con firma.
3. Wompi procesa transacción.
4. Wompi envía webhook: `POST /api/orders/wompi-webhook/`
5. Backend valida, confirma pago, decrementa stock.
6. Frontend consulta estado: `GET /api/transaction-status/{ref}/`

---

## 9. ENVÍOS

- **Cálculo**: `calculate_shipping_cost(city_code, subtotal)`.
- **Ciudades**: Lista estática en `CITY_CHOICES` (código + label).
- **Tarifas**: Bogotá (`SHIPPING_BOGOTA`), Nacional (`SHIPPING_NATIONAL`).
- **Gratis**: Subtotal ≥ `FREE_SHIPPING_THRESHOLD` (170,000 COP).
- **Tracking**: Campo `tracking_number` en Order (Servientrega).
- **No existe**: Integración directa con API de Servientrega ni cálculo dinámico de tarifas.

---

## 10. INTEGRACIONES

| Servicio | Estado | Tipo | Evidencia |
|---|---|---|---|
| **Wompi** | Implementado | Pagos (widget + webhook) | `apps/orders/services/wompi.py`, `views_api.py` |
| **Resend** | Implementado | Email transaccional | `apps/notifications/emails.py` |
| **Cloudflare R2** | Implementado | Storage S3-compatible | `config/settings.py` (líneas 253-320) |
| **ImageKit (django)** | Implementado | Derivados de imagen (WebP) | `apps/catalog/models.py` (ImageSpecField) |
| **Sentry** | Implementado | Monitoreo errores | `config/settings.py` (líneas 516-570), `@sentry/nextjs` |
| **Google Analytics 4** | Implementado | Analytics externo | `NEXT_PUBLIC_GA_MEASUREMENT_ID`, `components/analytics/GoogleAnalytics.tsx` |
| **Meta Pixel** | Implementado | Retargeting | `NEXT_PUBLIC_META_PIXEL_ID`, `components/analytics/MetaPixel.tsx` |
| **WhatsApp** | Solo enlaces | Links `wa.me/` en emails y checkout | `apps/notifications/email_context.py` |
| **Servientrega** | Solo tracking manual | Campo `tracking_number` sin API | `Order.tracking_number` |
| **Cloudinary** | Legacy/referencia | Pattern en next.config.mjs pero no usado activamente | `next.config.mjs` remotePatterns |

---

## 11. ATENCIÓN AL CLIENTE

### Estado actual: **Mínimo/Inexistente**

| Capacidad | Existe | Detalle |
|---|---|---|
| Gestionar consultas | No | No hay sistema de tickets ni chat |
| Obtener info de pedidos | Solo admin | Panel admin, no self-service del cliente |
| Consultar productos | Solo catálogo público | Sin asistente ni recomendaciones |
| Registrar conversaciones | No | No hay historial de interacciones |
| Escalar solicitudes | No | No hay workflow de escalación |
| Enviar notificaciones | Solo email | 4 tipos de email transaccional |
| Gestionar reclamaciones | No | No hay sistema de devoluciones/RMA |
| Medir satisfacción | No | No hay encuestas ni NPS |
| WhatsApp | Solo enlaces | Sin API oficial, sin bot, sin historial |

**Esta es la mayor oportunidad para JARVIS.**

---

## 12. APIs

### Resumen de endpoints

| Grupo | Endpoints | Auth | Propósito |
|---|---|---|---|
| **Catálogo público** | 8 endpoints GET | Ninguna | Navegación, productos, banners, promos |
| **Checkout** | 5 endpoints (GET/POST) | Ninguna (throttled) | Ciudades, shipping, stock validate, checkout, Wompi sig |
| **Webhooks** | 1 endpoint POST | Firma Wompi | Callback de pago |
| **Estado transacción** | 1 endpoint GET | Ninguna | Consulta por reference |
| **Analytics ingestion** | 1 endpoint POST | Ninguna (1000/min) | Eventos frontend |
| **Admin auth** | 4 endpoints | 2FA + sesión | Login, OTP, logout, me |
| **Admin dashboard** | 2 endpoints GET | IsAdminUser | KPIs, analytics |
| **Admin orders** | 5 endpoints | IsAdminUser | CRUD órdenes, ship, cancel, reminder |
| **Admin inventory** | 4 endpoints | IsAdminUser | CRUD pools, bulk, historial |
| **Admin customers** | 3 endpoints | IsAdminUser | CRUD clientes |
| **Admin products** | 7+ endpoints | IsAdminUser | CRUD productos, variantes, imágenes |
| **Admin homepage** | 6 endpoints | IsAdminUser | Banners, promos, secciones |
| **Admin discounts** | 3 endpoints | IsAdminUser | CRUD descuentos |
| **Admin recovery** | 1 endpoint GET | IsAdminUser | Órdenes pendientes de pago |

**Total: ~50+ endpoints documentados.**

---

## 13. DATOS Y MÉTRICAS

### Fuentes de datos disponibles

| Métrica | Fuente | Disponible |
|---|---|---|
| **Ventas totales** | `Order` (status=PAID) | Admin dashboard |
| **Revenue por período** | `Order.total` agregado | Dashboard (7d/30d/90d/custom) |
| **Ticket promedio** | Revenue / order_count | Dashboard |
| **Conteo de pedidos** | `Order.objects.count()` | Dashboard |
| **Productos top** | OrderItem agregados | Dashboard (top 5) |
| **Ventas diarias** | Order por created_at | Dashboard (gráfico) |
| **Funnel de conversión** | AnalyticsEvent | Analytics (view→click→cart→checkout→purchase) |
| **Product views/clicks** | AnalyticsEvent | Analytics |
| **Add-to-cart rate** | AnalyticsEvent | Analytics |
| **Revenue en riesgo** | Pedidos pending_payment | Dashboard |
| **Clientes recurrentes** | Customer con múltiples Orders | Calculable (no hay endpoint dedicado) |
| **Abandono del carrito** | Órdenes pending_payment | Parcial (admin/recuperación) |
| **Satisfacción** | No existe | No |
| **Consultas de soporte** | No existe | No |

### Analytics interno
- Modelo `AnalyticsEvent`: event, session_id, page, product_id, variant, quantity, price, step, raw (JSON), timestamp.
- Eventos: `product_view`, `product_click`, `add_to_cart`, `checkout_start`, `checkout_step`, `purchase_complete`, `home_visit`.
- Batching: KameTracker envía cada 5s + beacon on unload.
- Bridge: Mapea a GA4 (gtag) y Meta Pixel (fbq).

---

## 14. CALIDAD

| Área | Evaluación | Detalle |
|---|---|---|
| **Arquitectura** | A | Service layer, separación clara, models/services/views |
| **Tests backend** | B+ | 776 líneas, 10+ suites cubriendo pagos, stock, idempotencia, descuentos |
| **Tests E2E** | B+ | 7 specs Playwright + sandbox real Wompi |
| **CI/CD** | A- | Bandit SAST, pip-audit, Playwright, keep-alive (falta npm audit) |
| **Typing frontend** | B | TypeScript estricto, ~54 `any` residuales |
| **Error handling** | B+ | Normalización de errores, no stack traces en prod |
| **Observabilidad** | B+ | Sentry backend+frontend, analytics interno, GA4, Meta Pixel |
| **Mantenibilidad** | A- | Código bien estructurado, services testables, signals documentados |
| **Logging** | B | File + console por app, falta correlation ID |

---

## 15. SEGURIDAD

### Fortalezas

| Control | Implementación |
|---|---|
| **2FA admin** | django-otp + TOTP enforced en login y Django admin |
| **Firma de pagos** | SHA256 HMAC para widget y webhook Wompi |
| **Idempotencia pagos** | `select_for_update()` + `stock_deducted_at` |
| **Rate limiting** | Checkout: 5/min, Stock validate: 30/min, Anon: 60/min |
| **CSRF** | Middleware activo, exempt solo en APIs públicas |
| **IP restriction** | Middleware para /admin/ (configurable) |
| **PII en Sentry** | before_send filtra password, card_number, cvv, email, token |
| **Cookie security** | Secure + HttpOnly + SameSite=Lax en producción |
| **SAST** | Bandit en CI (Medium+ severity) |
| **Dependency audit** | pip-audit en CI |
| **No card data** | Wompi widget maneja datos de tarjeta (PCI compliant) |
| **Secrets** | Env vars, nunca hardcoded |

### Brechas identificadas

| Prioridad | Hallazgo |
|---|---|
| Alta | No hay CORS explícito (django-cors-headers no instalado) |
| Alta | npm audit deshabilitado (pending Next.js 16 upgrade) |
| Media | HSTS no configurado (SECURE_HSTS_SECONDS=0) |
| Media | CSP headers no configurados |
| Media | Admin IP allowlist vacío por defecto |
| Baja | No hay correlation ID en logs |
| Baja | No hay política de retención de datos |

---

## 16. OPORTUNIDADES PARA JARVIS

### Oportunidad 1: Agente de Atención al Cliente (WhatsApp)

| Aspecto | Detalle |
|---|---|
| **Necesidad** | No existe canal de soporte automatizado. WhatsApp es solo enlace. |
| **Datos requeridos** | Catálogo de productos, FAQ, políticas de envío/devolución |
| **APIs disponibles** | Catálogo público (8 endpoints), navegación, búsqueda |
| **Dependencias** | WhatsApp Business API (Meta Cloud API), LLM para NLU |
| **Riesgos** | Alucinaciones en precios/stock, promesas no cumplibles |
| **Complejidad** | Media-Alta |
| **Impacto** | **Muy Alto** — reduce carga manual, mejora tiempo de respuesta, 24/7 |

### Oportunidad 2: Agente de Consulta de Pedidos

| Aspecto | Detalle |
|---|---|
| **Necesidad** | Clientes no pueden consultar estado sin contactar al dueño |
| **Datos requeridos** | Order status, tracking_number, payment_reference |
| **APIs disponibles** | `GET /api/transaction-status/{ref}/` (público) |
| **Dependencias** | Autenticación del cliente (cedula+reference), WhatsApp API |
| **Riesgos** | Exposición de datos si no se valida identidad |
| **Complejidad** | Baja-Media |
| **Impacto** | **Alto** — autoservicio reduce consultas repetitivas |

### Oportunidad 3: Asistente de Ventas / Recomendaciones

| Aspecto | Detalle |
|---|---|
| **Necesidad** | No hay asesoría de tallas, combinaciones, ni recomendaciones |
| **Datos requeridos** | Catálogo, variantes, tallas, guía de medidas, stock, descuentos |
| **APIs disponibles** | Producto detalle, CategorySizeGuide, DiscountRule, navegación |
| **Dependencias** | LLM con contexto de catálogo, historial de compras (calculable) |
| **Riesgos** | Recomendaciones incorrectas, stock desactualizado |
| **Complejidad** | Media |
| **Impacto** | **Alto** — incrementa conversión, reduce devoluciones |

### Oportunidad 4: Automatización de Recordatorios de Pago

| Aspecto | Detalle |
|---|---|
| **Necesidad** | Recordatorios son manuales (admin envía 1/día por orden) |
| **Datos requeridos** | Órdenes pending_payment, tiempo transcurrido |
| **APIs disponibles** | `GET /api/admin/orders/pending-recovery/`, send-reminder |
| **Dependencias** | Cron/scheduler, reglas de negocio para timing |
| **Riesgos** | Spam, fatiga del cliente |
| **Complejidad** | Baja |
| **Impacto** | **Medio-Alto** — recupera revenue en riesgo |

### Oportunidad 5: Dashboard de Métricas Inteligente

| Aspecto | Detalle |
|---|---|
| **Necesidad** | Dashboard existe pero no tiene insights automáticos |
| **Datos requeridos** | AnalyticsEvent, Orders, funnel, productos top |
| **APIs disponibles** | Dashboard API, Analytics API, Orders API |
| **Dependencias** | LLM para análisis y resumen |
| **Riesgos** | Conclusiones erróneas sin contexto |
| **Complejidad** | Media |
| **Impacto** | **Medio** — ahorra tiempo de análisis al dueño |

### Oportunidad 6: Consulta de Inventario y Alertas

| Aspecto | Detalle |
|---|---|
| **Necesidad** | No hay alertas de stock bajo ni proyecciones |
| **Datos requeridos** | InventoryPool, velocidad de venta, historial de ajustes |
| **APIs disponibles** | Admin inventory endpoints, InventoryAdjustmentLog |
| **Dependencias** | Reglas de umbral, notificaciones (email/WhatsApp) |
| **Riesgos** | Falsos positivos en alertas |
| **Complejidad** | Baja-Media |
| **Impacto** | **Medio** — previene quiebres de stock |

### Oportunidad 7: Integración WhatsApp Nativa

| Aspecto | Detalle |
|---|---|
| **Necesidad** | WhatsApp es el canal principal de contacto pero no está automatizado |
| **Datos requeridos** | Mensajes entrantes, catálogo, pedidos |
| **APIs disponibles** | Todas las APIs públicas + WhatsApp Business Cloud API |
| **Dependencias** | Meta Business Suite, webhook receiver, message queue |
| **Riesgos** | Costo por mensaje, compliance Meta, latencia |
| **Complejidad** | Alta |
| **Impacto** | **Muy Alto** — canal preferido por clientes colombianos |

### Oportunidad 8: Análisis de Satisfacción Post-Compra

| Aspecto | Detalle |
|---|---|
| **Necesidad** | No existe medición de satisfacción |
| **Datos requeridos** | Pedidos enviados, feedback del cliente |
| **APIs disponibles** | Orders API (status=SHIPPED), email (Resend) |
| **Dependencias** | Encuesta post-compra, almacenamiento de respuestas |
| **Riesgos** | Baja tasa de respuesta |
| **Complejidad** | Baja |
| **Impacto** | **Medio** — insights para mejora continua |

---

## 17. DEPENDENCIAS CRÍTICAS

| Dependencia | Riesgo | Mitigación |
|---|---|---|
| **Wompi** | Único proveedor de pagos | Monitoreo de webhook, idempotencia implementada |
| **Resend** | Único proveedor de email | Fallback a consola, logs, best-effort |
| **Render** | Backend hosting | Keep-alive workflow, health checks |
| **Vercel** | Frontend hosting | Build automático, ISR caching |
| **Cloudflare R2** | Storage de medios | Cache headers inmutable (1 año) |
| **PostgreSQL (Render)** | Base de datos única | Backups managed, SSL auto |

---

## 18. RIESGOS

| Riesgo | Probabilidad | Impacto | Mitigación actual |
|---|---|---|---|
| Doble cobro por webhook duplicado | Baja | Alto | Idempotencia con `stock_deducted_at` |
| Race condition en stock | Baja | Alto | `select_for_update()` |
| Caída de Render (backend) | Media | Alto | Keep-alive cada 5 min, sin failover |
| Email no entregado | Media | Medio | Best-effort, sin retry |
| Falta de CORS | Baja | Medio | Proxy Next.js mitiga parcialmente |
| npm vulnerabilities | Media | Medio | Audit deshabilitado temporalmente |
| No hay backups explícitos | Media | Alto | Depende de backups managed de Render |
| Sin rate limit en admin API | Baja | Medio | 2FA mitiga acceso no autorizado |

---

## 19. LIMITACIONES DE ESTA AUDITORÍA

- **Solo lectura**: No se ejecutó código, migraciones, ni tests.
- **Sin acceso a producción**: No se verificaron configuraciones reales de env vars.
- **Sin datos reales**: No se consultaron clientes, órdenes, ni inventario.
- **Sin pruebas de penetración**: Solo análisis estático del código.
- **Punto en el tiempo**: Código evaluado al 2026-10-24, branch `main`.
- **Sin acceso a Render/Vercel dashboards**: Configuración de deploy inferida del código.

---

## 20. EVIDENCIAS VERIFICABLES

| Hallazgo | Archivo | Línea(s) |
|---|---|---|
| Django 5.2.17 | `requirements/base.txt` | 1 |
| Next.js 14.2.15 | `frontend/package.json` | dependencies |
| 2FA enforced | `config/urls.py` | 27 |
| Admin IP restriction | `config/middleware.py` | 1-29 |
| Wompi webhook validation | `apps/orders/services/wompi.py` | 28-73 |
| Stock atomic lock | `apps/orders/services/payments.py` | 61 |
| Idempotencia pagos | `apps/orders/services/payments.py` | 63-78 |
| InventoryPool como fuente de verdad | `apps/catalog/services/inventory.py` | 144-194 |
| Email post-commit | `apps/orders/services/payments.py` | 171-198 |
| Rate limiting checkout | `config/settings.py` | 354-358 |
| Sentry PII filtering | `config/settings.py` | 526-538 |
| Analytics interno | `apps/orders/models.py` | 300-321 |
| Variant sync signals | `apps/catalog/signals.py` | 89-133 |
| Carrito en Zustand | `frontend/store/cart.ts` | 1-130 |
| Stock validate debounce | `frontend/store/cart-stock-slice.ts` | 18 |
| Proxy API | `frontend/app/api/[...path]/route.ts` | 1-37 |
| Tests idempotencia | `apps/orders/tests.py` | 233-354 |
| Bandit CI | `.github/workflows/bandit.yml` | 1-30 |
| pip-audit CI | `.github/workflows/dependency-audit.yml` | 1-44 |

---

## MATRIZ: PROCESOS COMERCIALES x OPORTUNIDADES

| Proceso comercial | Implementación actual | Datos disponibles | Oportunidad de automatización | Evidencia |
|---|---|---|---|---|
| **Consulta de productos** | Catálogo web público | API completa (productos, variantes, stock, precios, imágenes) | Agente de ventas WhatsApp con búsqueda y recomendaciones | `apps/catalog/views_api.py`, `urls_api.py` |
| **Asesoría de tallas** | Guía de medidas estática | `CategorySizeGuide` con JSON de columnas/filas | Asistente que interpreta medidas y recomienda talla | `apps/catalog/models.py:156-233` |
| **Consulta de pedidos** | Solo admin panel | Status, tracking, reference (API pública por ref) | Self-service vía WhatsApp/web con validación de identidad | `GET /api/transaction-status/{ref}/` |
| **Pagos pendientes** | Recordatorio manual (1/día) | Órdenes pending_payment con timestamps | Recordatorios automáticos escalonados | `apps/admin_api/views_orders.py:220-298` |
| **Confirmación de pago** | Email automático (Resend) | Order + items + customer + totals | Notificación WhatsApp adicional al email | `apps/notifications/emails.py:170-227` |
| **Tracking de envío** | Campo manual sin API | `tracking_number` en Order | Notificación proactiva de estado, integración Servientrega API | `Order.tracking_number` |
| **Devoluciones** | No implementado | N/A | Sistema completo de RMA con agente | No existe |
| **Satisfacción** | No implementado | N/A | Encuesta post-compra automatizada + análisis | No existe |
| **Análisis de ventas** | Dashboard admin básico | Revenue, orders, top products, funnel | Resúmenes automáticos + alertas + insights | `apps/admin_api/views_dashboard.py` |
| **Inventario** | CRUD manual + bulk CSV | InventoryPool + adjustment logs | Alertas stock bajo + proyección de quiebre | `apps/admin_api/views_inventory.py` |
| **Abandono carrito** | Lista admin de pending orders | Orders pending + analytics events | Re-engagement automático multi-canal | `apps/admin_api/views_dashboard.py` |
| **Campañas** | GA4 + Meta Pixel | Analytics events, funnel data | Segmentación + triggers basados en comportamiento | `AnalyticsEvent`, `lib/analytics-bridge.ts` |

---

## RESPUESTA FINAL

### ¿Qué capacidades inteligentes podrían aportar mayor valor comercial a KameCol utilizando la infraestructura existente?

**Las tres de mayor impacto inmediato:**

1. **Agente WhatsApp de atención y ventas** — La infraestructura de APIs públicas (catálogo, stock, precios, descuentos, tallas) ya está lista para ser consumida por un agente. WhatsApp es el canal natural en Colombia. Un agente que responda consultas de productos, recomiende tallas, y comparta enlaces al checkout tendría impacto directo en conversión. Requiere: WhatsApp Business Cloud API + LLM + las APIs existentes.

2. **Self-service de pedidos** — El endpoint `GET /api/transaction-status/{ref}/` ya es público. Un agente que permita al cliente consultar su pedido por referencia + cédula (validación de identidad) eliminaría la consulta más frecuente en soporte. Requiere: mínima autenticación adicional + canal WhatsApp o web.

3. **Automatización de recuperación de pagos pendientes** — Los datos ya existen (`pending-recovery` endpoint), el mecanismo de envío ya existe (`send-reminder`), y el rate limit ya está implementado (1/24h). Solo falta un scheduler inteligente que envíe recordatorios escalonados (email a las 2h, WhatsApp a las 6h, último aviso a las 24h). Complejidad baja, impacto directo en revenue recovery.

**Estas tres oportunidades comparten una ventaja clave: no requieren modificar el backend existente.** Las APIs, los datos, y los mecanismos de acción ya están construidos. JARVIS sería un consumidor inteligente de la infraestructura actual.

---

*Auditoría generada el 2026-10-24. Código evaluado en branch `main`, commit `3bb5328`.*
