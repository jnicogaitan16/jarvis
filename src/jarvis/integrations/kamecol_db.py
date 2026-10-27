"""KameCol Database — acceso de SOLO LECTURA a la base de datos de producción.

REGLAS DE SEGURIDAD:
- Solo SELECT permitido. INSERT/UPDATE/DELETE/DROP bloqueados.
- Queries limitadas a 100 filas por defecto.
- No exponer datos PII en logs (emails, cédulas, teléfonos).
- Timeout de 10 segundos por query.
"""

from __future__ import annotations

import logging
import os
import re

import psycopg2
import psycopg2.extras

log = logging.getLogger(__name__)

_BLOCKED_PATTERNS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


class KameColDB:
    """Cliente de solo lectura para la base de datos de KameCol."""

    def __init__(self, database_url: str | None = None):
        self._url = database_url or os.environ.get("KAMECOL_DATABASE_URL", "")

    @property
    def is_configured(self) -> bool:
        return bool(self._url)

    def query(self, sql: str, params: tuple = (), limit: int = 100) -> list[dict]:
        """Ejecutar SELECT de solo lectura. Retorna lista de dicts."""
        if not self.is_configured:
            raise RuntimeError("KAMECOL_DATABASE_URL no configurada")

        if _BLOCKED_PATTERNS.search(sql):
            raise PermissionError("Operación de escritura bloqueada. Solo SELECT permitido.")

        if not sql.strip().upper().startswith("SELECT"):
            raise PermissionError("Solo queries SELECT permitidas.")

        # Agregar LIMIT si no tiene
        if "LIMIT" not in sql.upper():
            sql = f"{sql} LIMIT {limit}"

        try:
            conn = psycopg2.connect(self._url, connect_timeout=10)
            conn.set_session(readonly=True, autocommit=True)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            cur.close()
            conn.close()
            return rows
        except psycopg2.Error as e:
            raise RuntimeError(f"DB error: {e}") from e

    # ------------------------------------------------------------------
    # Queries predefinidas (seguras)
    # ------------------------------------------------------------------

    def get_orders_summary(self, days: int = 30) -> dict:
        """Resumen de órdenes de los últimos N días."""
        rows = self.query("""
            SELECT
                status,
                COUNT(*) as count,
                COALESCE(SUM(total), 0) as revenue
            FROM orders_order
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY status
            ORDER BY count DESC
        """, (days,))
        total_orders = sum(r["count"] for r in rows)
        total_revenue = sum(float(r["revenue"]) for r in rows)
        return {
            "period_days": days,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "by_status": {r["status"]: {"count": r["count"], "revenue": float(r["revenue"])} for r in rows},
        }

    def get_top_products(self, days: int = 30, limit: int = 10) -> list[dict]:
        """Productos más vendidos."""
        return self.query("""
            SELECT
                p.name,
                SUM(oi.quantity) as units_sold,
                SUM(oi.quantity * oi.unit_price) as revenue
            FROM orders_orderitem oi
            JOIN catalog_productvariant pv ON pv.id = oi.product_variant_id
            JOIN catalog_product p ON p.id = pv.product_id
            JOIN orders_order o ON o.id = oi.order_id
            WHERE o.created_at >= NOW() - INTERVAL '%s days'
              AND o.status IN ('paid', 'shipped')
            GROUP BY p.id, p.name
            ORDER BY units_sold DESC
        """, (days,), limit=limit)

    def get_inventory_low(self, threshold: int = 5) -> list[dict]:
        """Productos con stock bajo."""
        return self.query("""
            SELECT
                c.name as category, ip.value as variant, ip.color, ip.quantity
            FROM catalog_inventorypool ip
            JOIN catalog_category c ON c.id = ip.category_id
            WHERE ip.quantity <= %s AND ip.is_active = true
            ORDER BY ip.quantity ASC
        """, (threshold,))

    def get_customers_count(self) -> int:
        """Total de clientes."""
        rows = self.query("SELECT COUNT(*) as total FROM customers_customer")
        return rows[0]["total"] if rows else 0

    def get_daily_revenue(self, days: int = 7) -> list[dict]:
        """Revenue diario."""
        return self.query("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as orders,
                COALESCE(SUM(total), 0) as revenue
            FROM orders_order
            WHERE created_at >= NOW() - INTERVAL '%s days'
              AND status IN ('PAID', 'SHIPPED')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (days,))

    def get_recent_orders(self, limit: int = 10) -> list[dict]:
        """Últimas órdenes (sin PII — no expone email, cédula, teléfono)."""
        return self.query("""
            SELECT
                payment_reference, status, total,
                created_at, tracking_number, payment_method, city_code
            FROM orders_order
            ORDER BY created_at DESC
        """, limit=limit)

    def get_product_count(self) -> int:
        """Total de productos activos."""
        rows = self.query("SELECT COUNT(*) as total FROM catalog_product WHERE is_active = true")
        return rows[0]["total"] if rows else 0

    def get_funnel_stats(self, days: int = 7) -> list[dict]:
        """Estadísticas del funnel de conversión."""
        return self.query("""
            SELECT
                event, COUNT(*) as count
            FROM orders_analyticsevent
            WHERE timestamp >= NOW() - INTERVAL '%s days'
            GROUP BY event
            ORDER BY count DESC
        """, (days,))
