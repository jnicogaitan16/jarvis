"""Modelos del sistema Plugin Guardian."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class PluginSource(StrEnum):
    """Origen del plugin descubierto."""

    MCP_BUILTIN = "mcp_builtin"
    MCP_NPM = "mcp_npm"
    MCP_PIP = "mcp_pip"
    CLAUDE_PLUGIN = "claude_plugin"
    INTERNAL = "internal"


class PluginStatus(StrEnum):
    """Estado de salud del plugin."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    NOT_INSTALLED = "not_installed"


class PluginCategory(StrEnum):
    """Categoría funcional del plugin."""

    QA = "qa"
    SECURITY = "security"
    DEVOPS = "devops"
    DATABASE = "database"
    ANALYTICS = "analytics"
    DOCS = "docs"
    ECOMMERCE = "ecommerce"
    GENERAL = "general"


@dataclass(frozen=True)
class PluginSpec:
    """Especificación inmutable de un plugin."""

    id: str
    name: str
    source: PluginSource
    category: PluginCategory = PluginCategory.GENERAL
    version: str = ""
    description: str = ""
    tools: list[str] = field(default_factory=list)
    install_path: str = ""
    config_ref: str = ""


@dataclass
class PluginHealth:
    """Resultado de validación de un plugin."""

    plugin_id: str
    status: PluginStatus
    detail: str = ""
    tools_count: int = 0
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
