"""Registro central de plugins detectados."""

from __future__ import annotations

import logging

from jarvis.plugins.models import PluginHealth, PluginSpec, PluginStatus

log = logging.getLogger(__name__)


class PluginRegistry:
    """Registro en memoria de plugins descubiertos y su estado."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginSpec] = {}
        self._health: dict[str, PluginHealth] = {}

    def register(self, spec: PluginSpec) -> None:
        """Registrar un plugin descubierto."""
        self._plugins[spec.id] = spec
        log.debug("Plugin registrado: %s (%s)", spec.id, spec.source)

    def get(self, plugin_id: str) -> PluginSpec | None:
        return self._plugins.get(plugin_id)

    def list_all(self) -> list[PluginSpec]:
        return list(self._plugins.values())

    def list_by_category(self, category: str) -> list[PluginSpec]:
        return [p for p in self._plugins.values() if p.category == category]

    def list_by_source(self, source: str) -> list[PluginSpec]:
        return [p for p in self._plugins.values() if p.source == source]

    @property
    def count(self) -> int:
        return len(self._plugins)

    def set_health(self, health: PluginHealth) -> None:
        """Actualizar estado de salud de un plugin."""
        self._health[health.plugin_id] = health

    def get_health(self, plugin_id: str) -> PluginHealth | None:
        return self._health.get(plugin_id)

    def all_health(self) -> list[PluginHealth]:
        return list(self._health.values())

    def healthy_count(self) -> int:
        return sum(1 for h in self._health.values() if h.status == PluginStatus.HEALTHY)

    def unhealthy_plugins(self) -> list[PluginHealth]:
        return [h for h in self._health.values() if h.status == PluginStatus.UNHEALTHY]
