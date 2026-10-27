"""Descubrimiento automático de plugins y MCP servers."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

from jarvis.plugins.models import (
    PluginCategory,
    PluginHealth,
    PluginSource,
    PluginSpec,
    PluginStatus,
)

log = logging.getLogger(__name__)

# Mapeo de nombres de MCP server a categoría
_MCP_CATEGORIES: dict[str, PluginCategory] = {
    "mysql": PluginCategory.DATABASE,
    "postgres": PluginCategory.DATABASE,
    "sqlite": PluginCategory.DATABASE,
    "mixpanel": PluginCategory.ANALYTICS,
    "sentry": PluginCategory.DEVOPS,
    "google_drive": PluginCategory.DOCS,
    "claude_docs": PluginCategory.DOCS,
    "monday": PluginCategory.GENERAL,
    "jam": PluginCategory.QA,
    "playwright": PluginCategory.QA,
    "github": PluginCategory.DEVOPS,
    "sonarqube": PluginCategory.QA,
    "postman": PluginCategory.QA,
    "semgrep": PluginCategory.SECURITY,
}


def _categorize_mcp(server_name: str) -> PluginCategory:
    """Inferir categoría de un MCP server por su nombre."""
    name_lower = server_name.lower().replace("-", "_").replace(" ", "_")
    for key, cat in _MCP_CATEGORIES.items():
        if key in name_lower:
            return cat
    return PluginCategory.GENERAL


def _parse_mcp_list_output(output: str) -> list[dict]:
    """Parsear la salida de `claude mcp list`."""
    servers = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("Checking"):
            continue

        # Formato: "name: url/command - status"
        match = re.match(r"^(.+?):\s+(.+?)\s+-\s+(.+)$", line)
        if not match:
            continue

        name = match.group(1).strip()
        endpoint = match.group(2).strip()
        status_text = match.group(3).strip()

        healthy = "Connected" in status_text
        needs_auth = "authentication" in status_text.lower()

        servers.append({
            "name": name,
            "endpoint": endpoint,
            "healthy": healthy,
            "needs_auth": needs_auth,
            "status_text": status_text,
        })

    return servers


def discover_mcp_servers() -> list[tuple[PluginSpec, PluginHealth]]:
    """Descubrir MCP servers via `claude mcp list`."""
    cli = shutil.which("claude")
    if not cli:
        log.warning("Claude CLI no encontrado — no se pueden descubrir MCP servers")
        return []

    try:
        result = subprocess.run(
            [cli, "mcp", "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            log.warning("claude mcp list falló: %s", result.stderr[:200])
            return []

        servers = _parse_mcp_list_output(result.stdout)

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.warning("Error ejecutando claude mcp list: %s", e)
        return []

    results = []
    for srv in servers:
        server_id = _normalize_id(srv["name"])
        source = PluginSource.MCP_NPM if "npx" in srv["endpoint"] else PluginSource.MCP_BUILTIN

        spec = PluginSpec(
            id=f"mcp.{server_id}",
            name=srv["name"],
            source=source,
            category=_categorize_mcp(srv["name"]),
            description=srv["endpoint"],
        )

        if srv["healthy"]:
            status = PluginStatus.HEALTHY
            detail = "Connected"
        elif srv["needs_auth"]:
            status = PluginStatus.UNHEALTHY
            detail = "Needs authentication"
        else:
            status = PluginStatus.UNHEALTHY
            detail = srv["status_text"]

        health = PluginHealth(
            plugin_id=spec.id,
            status=status,
            detail=detail,
        )
        results.append((spec, health))

    return results


def discover_claude_plugins() -> list[tuple[PluginSpec, PluginHealth]]:
    """Descubrir plugins instalados de Claude Code."""
    plugins_file = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    settings_file = Path.home() / ".claude" / "settings.json"

    if not plugins_file.exists():
        return []

    try:
        data = json.loads(plugins_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Error leyendo installed_plugins.json: %s", e)
        return []

    if data.get("version") != 2:
        log.warning("Formato de installed_plugins.json no soportado: v%s", data.get("version"))
        return []

    # Leer qué plugins están habilitados
    enabled: dict[str, bool] = {}
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            enabled = settings.get("enabledPlugins", {})
        except (json.JSONDecodeError, OSError):
            pass

    results = []
    for plugin_key, installs in data.get("plugins", {}).items():
        if not installs:
            continue

        install = installs[0]  # Usar la primera instalación
        is_enabled = enabled.get(plugin_key, False)

        spec = PluginSpec(
            id=f"claude.{_normalize_id(plugin_key)}",
            name=plugin_key,
            source=PluginSource.CLAUDE_PLUGIN,
            category=PluginCategory.GENERAL,
            version=install.get("version", ""),
            install_path=install.get("installPath", ""),
        )

        status = PluginStatus.HEALTHY if is_enabled else PluginStatus.UNHEALTHY
        detail = f"v{spec.version}, enabled" if is_enabled else f"v{spec.version}, disabled"

        health = PluginHealth(
            plugin_id=spec.id,
            status=status,
            detail=detail,
        )
        results.append((spec, health))

    return results


def discover_mcp_from_permissions() -> list[str]:
    """Extraer nombres de MCP servers desde permisos locales del proyecto."""
    settings_path = Path.cwd() / ".claude" / "settings.local.json"
    if not settings_path.exists():
        return []

    try:
        data = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    permissions = data.get("permissions", {}).get("allow", [])
    servers: set[str] = set()

    for perm in permissions:
        if isinstance(perm, str) and perm.startswith("mcp__"):
            # mcp__server_name__tool_name → server_name
            parts = perm.split("__")
            if len(parts) >= 2:
                servers.add(parts[1])

    return sorted(servers)


def discover_all() -> list[tuple[PluginSpec, PluginHealth]]:
    """Descubrimiento completo de todos los plugins."""
    results = []
    results.extend(discover_mcp_servers())
    results.extend(discover_claude_plugins())
    return results


def _normalize_id(name: str) -> str:
    """Normalizar nombre a ID válido."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower().replace(" ", "_").replace("@", "_at_")).strip("_")
