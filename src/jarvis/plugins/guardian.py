"""Plugin Guardian — orquesta descubrimiento, validación y monitoreo."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from jarvis.plugins.discovery import discover_all, discover_mcp_from_permissions
from jarvis.plugins.models import PluginHealth, PluginStatus
from jarvis.plugins.registry import PluginRegistry

log = logging.getLogger(__name__)


@dataclass
class GuardianReport:
    """Reporte de una ejecución del Guardian."""

    total_discovered: int = 0
    healthy: int = 0
    unhealthy: int = 0
    unknown: int = 0
    new_plugins: list[str] = field(default_factory=list)
    lost_plugins: list[str] = field(default_factory=list)
    permission_servers: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class PluginGuardian:
    """Guardián central que descubre, valida y monitorea plugins."""

    def __init__(self) -> None:
        self._registry = PluginRegistry()
        self._last_scan: datetime | None = None

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    @property
    def last_scan(self) -> datetime | None:
        return self._last_scan

    def scan(self) -> GuardianReport:
        """Ejecutar escaneo completo de plugins."""
        previous_ids = {s.id for s in self._registry.list_all()}

        discovered = discover_all()
        permission_servers = discover_mcp_from_permissions()

        current_ids: set[str] = set()
        for spec, health in discovered:
            self._registry.register(spec)
            self._registry.set_health(health)
            current_ids.add(spec.id)

        new_plugins = sorted(current_ids - previous_ids)
        lost_plugins = sorted(previous_ids - current_ids)

        # Marcar plugins perdidos
        for pid in lost_plugins:
            self._registry.set_health(
                PluginHealth(plugin_id=pid, status=PluginStatus.NOT_INSTALLED, detail="No detectado en último scan")
            )

        self._last_scan = datetime.now(UTC)

        report = GuardianReport(
            total_discovered=len(discovered),
            healthy=self._registry.healthy_count(),
            unhealthy=len(self._registry.unhealthy_plugins()),
            unknown=sum(1 for h in self._registry.all_health() if h.status == PluginStatus.UNKNOWN),
            new_plugins=new_plugins,
            lost_plugins=lost_plugins,
            permission_servers=permission_servers,
        )

        if new_plugins:
            log.info("Nuevos plugins detectados: %s", ", ".join(new_plugins))
        if lost_plugins:
            log.warning("Plugins perdidos: %s", ", ".join(lost_plugins))

        return report

    def validate(self) -> list[str]:
        """Validar consistencia entre plugins registrados y permisos del proyecto."""
        issues: list[str] = []

        permission_servers = discover_mcp_from_permissions()
        registered_mcp = {
            s.id.removeprefix("mcp."): s
            for s in self._registry.list_all()
            if s.id.startswith("mcp.")
        }

        # Permisos sin plugin registrado
        for srv in permission_servers:
            normalized = srv.lower().replace("-", "_").replace(" ", "_")
            if normalized not in registered_mcp:
                issues.append(f"Permiso MCP '{srv}' sin plugin registrado — posible server no conectado")

        # Plugins unhealthy
        for health in self._registry.unhealthy_plugins():
            issues.append(f"Plugin '{health.plugin_id}' no saludable: {health.detail}")

        return issues
