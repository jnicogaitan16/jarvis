"""KameCol Knowledge Base — conocimiento del proyecto e-commerce."""

from __future__ import annotations

from jarvis.core.models import MemoryType
from jarvis.memory.manager import MemoryManager

_PROJECT = "kamecol"
_SOURCE = "audit:kamecol"

_KNOWLEDGE_ENTRIES = [
    # Proyecto
    {
        "content": "KameCol es una tienda de streetwear colombiana en producción. Flujo comercial completo: catálogo → carrito → checkout → pago → confirmación → envío. Pagos en COP con Wompi.",
        "tags": ["overview", "negocio"],
    },
    {
        "content": "Stack: Django 5.2 + DRF 3.15.2 (backend, Render.com), Next.js 14 + React 18 (frontend, Vercel), PostgreSQL 16 (Render), Cloudflare R2 (storage), Zustand (estado cliente).",
        "tags": ["stack", "tecnologia"],
    },
    {
        "content": "Pagos via Wompi: tarjeta, Nequi, PSE, Daviplata, QR, Puntos Colombia. Firma SHA256 HMAC para widget y webhook. Stock se descuenta solo cuando Wompi confirma pago (APPROVED), no al crear orden.",
        "tags": ["pagos", "wompi", "negocio"],
    },
    {
        "content": "Ciclo de vida de orden: PENDING_PAYMENT → PAID → SHIPPED / CANCELLED. Campo stock_deducted_at previene doble deducción si webhook llega dos veces (idempotencia).",
        "tags": ["ordenes", "estados", "negocio"],
    },
    {
        "content": "Taxonomía de productos: Department → Category (árbol auto-referencial) → Product. Productos solo en categorías hoja. Variantes: size_color, jean_size, shoe_size, no_variant.",
        "tags": ["productos", "categorias", "modelo"],
    },
    {
        "content": "Descuentos con jerarquía de prioridad: Producto(40) > Categoría(30) > Departamento(20) > Tienda(10). Soporte porcentual o monto fijo COP con ventana temporal.",
        "tags": ["descuentos", "precios", "negocio"],
    },
    {
        "content": "Inventario: InventoryPool como fuente de verdad con select_for_update() para concurrencia. Signals de Django sincronizan ProductVariant automáticamente cuando se modifica InventoryPool.",
        "tags": ["inventario", "concurrencia", "modelo"],
    },
    {
        "content": "Frontend: Next.js 14 App Router. Proxy API en /app/api/[...path]/route.ts — browser nunca llama directamente a Render. Zustand + localStorage para carrito. React Hook Form + Zod para checkout.",
        "tags": ["frontend", "nextjs", "arquitectura"],
    },
    {
        "content": "Analytics: KameTracker envía eventos en batches cada 5s + beacon on unload. Mapea a GA4 (gtag) y Meta Pixel (fbq). Modelo AnalyticsEvent con funnel: view→click→cart→checkout→purchase.",
        "tags": ["analytics", "tracking", "funnel"],
    },
    {
        "content": "Seguridad: 2FA TOTP enforced para admin. Rate limiting: checkout 5/min, stock-validate 30/min, anónimo 60/min. Filtrado PII en Sentry. Backend recalcula precios (ignora los del frontend).",
        "tags": ["seguridad", "admin", "rate-limit"],
    },
    {
        "content": "Emails transaccionales via Resend: orden creada, confirmada, declinada, recordatorio de pago. WhatsApp solo como enlaces wa.me/ (sin API, sin bot).",
        "tags": ["emails", "notificaciones", "whatsapp"],
    },
    {
        "content": "Envío: tarifas estáticas Bogotá/Nacional, gratis ≥170,000 COP. Tracking solo campo manual tracking_number, sin integración API Servientrega. Devoluciones/RMA no implementadas.",
        "tags": ["envios", "shipping", "faltante"],
    },
    {
        "content": "Brechas: sin CORS explícito (django-cors-headers no instalado), HSTS no configurado, npm audit deshabilitado, sin sistema de atención al cliente, sin self-service de pedidos.",
        "tags": ["brechas", "seguridad", "deuda-tecnica"],
    },
    {
        "content": "CI/CD: 4 workflows GitHub Actions. Tests: 776 líneas backend, 7 specs Playwright con sandbox Wompi real. SAST con Bandit + pip-audit.",
        "tags": ["cicd", "tests", "github-actions"],
    },
    {
        "content": "APIs públicas sin auth: /api/products/, /api/products/{slug}/, /api/navigation/, /api/transaction-status/{ref}/. APIs admin requieren sesión Django + 2FA.",
        "tags": ["api", "endpoints", "auth"],
    },
]


def seed_knowledge(manager: MemoryManager) -> int:
    """Cargar conocimiento de KameCol en memoria."""
    existing = manager.search_by_project(_PROJECT, limit=100)
    existing_contents = {r.content[:80] for r in existing}

    added = 0
    for entry in _KNOWLEDGE_ENTRIES:
        if entry["content"][:80] in existing_contents:
            continue
        manager.add(
            content=entry["content"],
            project=_PROJECT,
            source=_SOURCE,
            memory_type=MemoryType.PROJECT,
            confidence=0.9,
            tags=entry["tags"],
        )
        added += 1
    return added
