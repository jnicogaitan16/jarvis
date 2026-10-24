"""KameCol Agent — consultas de catálogo, pedidos y métricas comerciales."""

from __future__ import annotations

import time

from jarvis.agents.base import AgentRequest, AgentResult, AgentSpec, BaseAgent


class KameColAgent(BaseAgent):
    """Agente para operaciones comerciales de KameCol.

    Capacidades:
    - Buscar productos en el catálogo
    - Consultar estado de pedidos
    - Ver métricas del dashboard
    - Listar pedidos pendientes de recuperación
    """

    def spec(self) -> AgentSpec:
        return AgentSpec(
            id="biz.kamecol",
            name="KameCol Agent",
            description="Consultas de catálogo, pedidos y métricas comerciales de KameCol",
            skills=["catalog", "order_status", "dashboard", "recovery"],
            supported_projects=["kamecol"],
        )

    def execute(self, request: AgentRequest) -> AgentResult:
        start = time.monotonic()
        action = request.payload.get("action", self._detect_action(request))

        handlers = {
            "search_products": self._search_products,
            "product_detail": self._product_detail,
            "order_status": self._order_status,
            "dashboard": self._dashboard,
            "pending_recovery": self._pending_recovery,
            "navigation": self._navigation,
        }

        handler = handlers.get(action)
        if not handler:
            return AgentResult(
                success=True,
                content=f"KameCol Agent disponible. Acciones: {', '.join(handlers.keys())}",
                data={"available_actions": list(handlers.keys())},
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        try:
            result = handler(request)
            result.duration_ms = int((time.monotonic() - start) * 1000)
            return result
        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    def _detect_action(self, request: AgentRequest) -> str:
        text = (request.intent + " " + request.payload.get("question", "")).lower()
        if any(w in text for w in ("product", "catalog", "buscar", "talla", "precio")):
            return "search_products"
        if any(w in text for w in ("pedido", "orden", "order", "estado", "tracking")):
            return "order_status"
        if any(w in text for w in ("dashboard", "kpi", "ventas", "revenue", "métrica")):
            return "dashboard"
        if any(w in text for w in ("pendiente", "recovery", "recupera", "reminder")):
            return "pending_recovery"
        return "help"

    def _search_products(self, request: AgentRequest) -> AgentResult:
        from jarvis.integrations.kamecol import KameColPublicClient
        client = KameColPublicClient()
        if not client.is_configured:
            return AgentResult(success=False, error="KAMECOL_API_URL no configurada")

        query = request.payload.get("search", request.payload.get("question", ""))
        products = client.get_products(search=query)

        if not products:
            return AgentResult(success=True, content="No se encontraron productos.", data={"products": []})

        lines = [f"Encontrados {len(products)} productos:"]
        for p in products[:10]:
            price_str = f"${p.price:,.0f}"
            if p.discount_price:
                price_str = f"~~${p.price:,.0f}~~ ${p.discount_price:,.0f}"
            lines.append(f"- {p.name} — {price_str} COP ({p.category})")

        return AgentResult(
            success=True,
            content="\n".join(lines),
            data={"products": [{"slug": p.slug, "name": p.name, "price": p.price} for p in products[:10]]},
        )

    def _product_detail(self, request: AgentRequest) -> AgentResult:
        from jarvis.integrations.kamecol import KameColPublicClient
        client = KameColPublicClient()
        if not client.is_configured:
            return AgentResult(success=False, error="KAMECOL_API_URL no configurada")

        slug = request.payload.get("slug", "")
        if not slug:
            return AgentResult(success=False, error="Se requiere 'slug' del producto")

        product = client.get_product_detail(slug)
        if not product:
            return AgentResult(success=True, content=f"Producto '{slug}' no encontrado.")

        lines = [
            f"{product.name}",
            f"Precio: ${product.price:,.0f} COP",
            f"Categoría: {product.category}",
            f"Stock: {'Disponible' if product.in_stock else 'Agotado'}",
        ]
        if product.variants:
            lines.append(f"Variantes: {len(product.variants)} disponibles")

        return AgentResult(
            success=True,
            content="\n".join(lines),
            data={"product": {"slug": product.slug, "name": product.name, "price": product.price}},
        )

    def _order_status(self, request: AgentRequest) -> AgentResult:
        from jarvis.integrations.kamecol import KameColPublicClient
        client = KameColPublicClient()
        if not client.is_configured:
            return AgentResult(success=False, error="KAMECOL_API_URL no configurada")

        reference = request.payload.get("reference", "")
        if not reference:
            return AgentResult(success=False, error="Se requiere 'reference' del pedido")

        status = client.get_order_status(reference)
        if not status:
            return AgentResult(success=True, content=f"Pedido '{reference}' no encontrado.")

        lines = [
            f"Pedido: {status.reference}",
            f"Estado: {status.status}",
            f"Total: ${status.total:,.0f} COP",
        ]
        if status.tracking_number:
            lines.append(f"Tracking: {status.tracking_number}")

        return AgentResult(
            success=True,
            content="\n".join(lines),
            data={"order": {"reference": status.reference, "status": status.status}},
        )

    def _dashboard(self, request: AgentRequest) -> AgentResult:
        from jarvis.integrations.kamecol import KameColAdminClient
        client = KameColAdminClient()
        if not client.is_configured:
            return AgentResult(success=False, error="KameCol admin no configurado (KAMECOL_SESSION)")

        period = request.payload.get("period", "30d")
        kpis = client.get_dashboard(period=period)
        if not kpis:
            return AgentResult(success=False, error="No se pudieron obtener KPIs")

        lines = [
            f"Dashboard KameCol ({period}):",
            f"Revenue: ${kpis.revenue:,.0f} COP",
            f"Órdenes: {kpis.orders_count}",
            f"Ticket promedio: ${kpis.average_ticket:,.0f} COP",
            f"Pendientes: {kpis.pending_orders}",
        ]

        return AgentResult(
            success=True,
            content="\n".join(lines),
            data={"kpis": {"revenue": kpis.revenue, "orders": kpis.orders_count}},
        )

    def _pending_recovery(self, request: AgentRequest) -> AgentResult:
        from jarvis.integrations.kamecol import KameColAdminClient
        client = KameColAdminClient()
        if not client.is_configured:
            return AgentResult(success=False, error="KameCol admin no configurado (KAMECOL_SESSION)")

        pending = client.get_pending_recovery()
        if not pending:
            return AgentResult(success=True, content="No hay pedidos pendientes de recuperación.")

        lines = [f"{len(pending)} pedidos pendientes de pago:"]
        for order in pending[:10]:
            ref = order.get("reference", "?")
            total = order.get("total", 0)
            lines.append(f"- {ref} — ${total:,.0f} COP")

        return AgentResult(
            success=True,
            content="\n".join(lines),
            data={"pending_count": len(pending)},
        )

    def _navigation(self, request: AgentRequest) -> AgentResult:
        from jarvis.integrations.kamecol import KameColPublicClient
        client = KameColPublicClient()
        if not client.is_configured:
            return AgentResult(success=False, error="KAMECOL_API_URL no configurada")

        nav = client.get_navigation()
        if not nav:
            return AgentResult(success=True, content="No se pudo obtener la navegación.")

        lines = ["Categorías KameCol:"]
        for dept in nav:
            name = dept.get("name", "?")
            cats = dept.get("categories", [])
            cat_names = ", ".join(c.get("name", "") for c in cats) if cats else "—"
            lines.append(f"- {name}: {cat_names}")

        return AgentResult(success=True, content="\n".join(lines), data={"departments": len(nav)})
