"""KameCol Integration — clientes API para e-commerce.

APIs públicas (sin auth): catálogo, productos, estado de pedidos.
APIs admin (requieren sesión): dashboard, órdenes, inventario.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx


@dataclass(frozen=True)
class Product:
    slug: str
    name: str
    price: float
    discount_price: float | None = None
    department: str = ""
    category: str = ""
    in_stock: bool = True
    variants: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class OrderStatus:
    reference: str
    status: str
    total: float = 0.0
    customer_name: str = ""
    created_at: str = ""
    tracking_number: str = ""


@dataclass(frozen=True)
class DashboardKPIs:
    revenue: float = 0.0
    orders_count: int = 0
    average_ticket: float = 0.0
    pending_orders: int = 0
    top_products: list[dict] = field(default_factory=list)


class KameColPublicClient:
    """Cliente para APIs públicas de KameCol (sin autenticación)."""

    def __init__(self, base_url: str | None = None, timeout: int = 10):
        self._base_url = (base_url or os.environ.get("KAMECOL_API_URL", "")).rstrip("/")
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self._base_url)

    def get_products(
        self,
        search: str | None = None,
        category: str | None = None,
        department: str | None = None,
        limit: int = 20,
    ) -> list[Product]:
        """Buscar productos en el catálogo."""
        if not self.is_configured:
            return []

        params: dict = {}
        if search:
            params["search"] = search
        if category:
            params["category"] = category
        if department:
            params["department"] = department

        try:
            resp = httpx.get(
                f"{self._base_url}/api/products/",
                params=params,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            items = data if isinstance(data, list) else data.get("results", data.get("products", []))
            return [self._parse_product(p) for p in items[:limit]]
        except httpx.HTTPError:
            return []

    def get_product_detail(self, slug: str) -> Product | None:
        """Obtener detalle de un producto con variantes y stock."""
        if not self.is_configured:
            return None

        try:
            resp = httpx.get(
                f"{self._base_url}/api/products/{slug}/",
                timeout=self._timeout,
            )
            resp.raise_for_status()
            return self._parse_product(resp.json())
        except httpx.HTTPError:
            return None

    def get_navigation(self) -> list[dict]:
        """Obtener árbol de departamentos y categorías."""
        if not self.is_configured:
            return []

        try:
            resp = httpx.get(f"{self._base_url}/api/navigation/", timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            return []

    def get_order_status(self, reference: str) -> OrderStatus | None:
        """Consultar estado de un pedido por referencia."""
        if not self.is_configured:
            return None

        try:
            resp = httpx.get(
                f"{self._base_url}/api/transaction-status/{reference}/",
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return OrderStatus(
                reference=reference,
                status=data.get("status", "unknown"),
                total=data.get("total", 0),
                customer_name=data.get("customer_name", ""),
                created_at=data.get("created_at", ""),
                tracking_number=data.get("tracking_number", ""),
            )
        except httpx.HTTPError:
            return None

    def _parse_product(self, data: dict) -> Product:
        return Product(
            slug=data.get("slug", ""),
            name=data.get("name", ""),
            price=float(data.get("price", 0)),
            discount_price=data.get("discount_price"),
            department=data.get("department", {}).get("name", "") if isinstance(data.get("department"), dict) else str(data.get("department", "")),
            category=data.get("category", {}).get("name", "") if isinstance(data.get("category"), dict) else str(data.get("category", "")),
            in_stock=data.get("in_stock", True),
            variants=data.get("variants", []),
        )


class KameColAdminClient:
    """Cliente para APIs admin de KameCol (requiere sesión autenticada)."""

    def __init__(
        self,
        base_url: str | None = None,
        session_cookie: str | None = None,
        timeout: int = 10,
    ):
        self._base_url = (base_url or os.environ.get("KAMECOL_API_URL", "")).rstrip("/")
        self._session_cookie = session_cookie or os.environ.get("KAMECOL_SESSION", "")
        self._timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self._base_url and self._session_cookie)

    def _headers(self) -> dict:
        return {"Cookie": f"sessionid={self._session_cookie}"}

    def get_dashboard(self, period: str = "30d") -> DashboardKPIs | None:
        """Obtener KPIs del dashboard."""
        if not self.is_configured:
            return None

        try:
            resp = httpx.get(
                f"{self._base_url}/api/admin/dashboard/",
                params={"period": period},
                headers=self._headers(),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return DashboardKPIs(
                revenue=data.get("revenue", 0),
                orders_count=data.get("orders_count", 0),
                average_ticket=data.get("average_ticket", 0),
                pending_orders=data.get("pending_orders", 0),
                top_products=data.get("top_products", []),
            )
        except httpx.HTTPError:
            return None

    def get_pending_recovery(self) -> list[dict]:
        """Obtener órdenes pendientes de recuperación de pago."""
        if not self.is_configured:
            return []

        try:
            resp = httpx.get(
                f"{self._base_url}/api/admin/orders/pending-recovery/",
                headers=self._headers(),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("results", [])
        except httpx.HTTPError:
            return []

    def send_reminder(self, reference: str) -> bool:
        """Enviar recordatorio de pago para una orden."""
        if not self.is_configured:
            return False

        try:
            resp = httpx.post(
                f"{self._base_url}/api/admin/orders/{reference}/send-reminder/",
                headers=self._headers(),
                timeout=self._timeout,
            )
            return resp.status_code in (200, 201, 204)
        except httpx.HTTPError:
            return False

    def get_inventory(self) -> list[dict]:
        """Obtener pools de inventario."""
        if not self.is_configured:
            return []

        try:
            resp = httpx.get(
                f"{self._base_url}/api/admin/inventory/",
                headers=self._headers(),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else data.get("results", [])
        except httpx.HTTPError:
            return []
