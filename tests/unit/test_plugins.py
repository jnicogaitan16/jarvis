"""Tests del sistema Plugin Guardian."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.plugins.discovery import (
    _categorize_mcp,
    _normalize_id,
    _parse_mcp_list_output,
    discover_mcp_from_permissions,
)
from jarvis.plugins.guardian import PluginGuardian
from jarvis.plugins.models import (
    PluginCategory,
    PluginHealth,
    PluginSource,
    PluginSpec,
    PluginStatus,
)
from jarvis.plugins.registry import PluginRegistry


class TestPluginModels(unittest.TestCase):
    """Tests de modelos de datos."""

    def test_plugin_source_enum(self):
        assert PluginSource.MCP_BUILTIN == "mcp_builtin"
        assert PluginSource.MCP_NPM == "mcp_npm"
        assert PluginSource.CLAUDE_PLUGIN == "claude_plugin"

    def test_plugin_status_enum(self):
        assert PluginStatus.HEALTHY == "healthy"
        assert PluginStatus.UNHEALTHY == "unhealthy"
        assert PluginStatus.NOT_INSTALLED == "not_installed"

    def test_plugin_category_enum(self):
        assert PluginCategory.QA == "qa"
        assert PluginCategory.DATABASE == "database"
        assert PluginCategory.DEVOPS == "devops"

    def test_plugin_spec_frozen(self):
        spec = PluginSpec(id="test.plugin", name="Test", source=PluginSource.MCP_BUILTIN)
        with self.assertRaises(AttributeError):
            spec.id = "other"

    def test_plugin_spec_defaults(self):
        spec = PluginSpec(id="x", name="X", source=PluginSource.INTERNAL)
        assert spec.category == PluginCategory.GENERAL
        assert spec.version == ""
        assert spec.tools == []

    def test_plugin_health_mutable(self):
        health = PluginHealth(plugin_id="x", status=PluginStatus.HEALTHY)
        health.detail = "updated"
        assert health.detail == "updated"

    def test_plugin_health_has_timestamp(self):
        health = PluginHealth(plugin_id="x", status=PluginStatus.UNKNOWN)
        assert health.checked_at is not None


class TestPluginRegistry(unittest.TestCase):
    """Tests del registro de plugins."""

    def _make_spec(self, id: str = "test.a", name: str = "A") -> PluginSpec:
        return PluginSpec(id=id, name=name, source=PluginSource.MCP_BUILTIN)

    def test_register_and_get(self):
        reg = PluginRegistry()
        spec = self._make_spec()
        reg.register(spec)
        assert reg.get("test.a") is spec

    def test_get_nonexistent(self):
        reg = PluginRegistry()
        assert reg.get("nope") is None

    def test_list_all(self):
        reg = PluginRegistry()
        reg.register(self._make_spec("a", "A"))
        reg.register(self._make_spec("b", "B"))
        assert len(reg.list_all()) == 2

    def test_count(self):
        reg = PluginRegistry()
        assert reg.count == 0
        reg.register(self._make_spec())
        assert reg.count == 1

    def test_list_by_category(self):
        reg = PluginRegistry()
        reg.register(PluginSpec(id="db.1", name="DB", source=PluginSource.MCP_NPM, category=PluginCategory.DATABASE))
        reg.register(PluginSpec(id="qa.1", name="QA", source=PluginSource.MCP_NPM, category=PluginCategory.QA))
        assert len(reg.list_by_category("database")) == 1
        assert len(reg.list_by_category("qa")) == 1

    def test_list_by_source(self):
        reg = PluginRegistry()
        reg.register(PluginSpec(id="a", name="A", source=PluginSource.MCP_BUILTIN))
        reg.register(PluginSpec(id="b", name="B", source=PluginSource.CLAUDE_PLUGIN))
        assert len(reg.list_by_source("mcp_builtin")) == 1

    def test_health_workflow(self):
        reg = PluginRegistry()
        reg.register(self._make_spec())
        health = PluginHealth(plugin_id="test.a", status=PluginStatus.HEALTHY, detail="OK")
        reg.set_health(health)
        assert reg.get_health("test.a") is health
        assert reg.healthy_count() == 1
        assert reg.unhealthy_plugins() == []

    def test_unhealthy_plugins(self):
        reg = PluginRegistry()
        reg.set_health(PluginHealth(plugin_id="a", status=PluginStatus.UNHEALTHY, detail="down"))
        reg.set_health(PluginHealth(plugin_id="b", status=PluginStatus.HEALTHY))
        assert len(reg.unhealthy_plugins()) == 1
        assert reg.unhealthy_plugins()[0].plugin_id == "a"


class TestDiscovery(unittest.TestCase):
    """Tests del descubrimiento de plugins."""

    def test_normalize_id(self):
        assert _normalize_id("mysql-prod") == "mysql_prod"
        assert _normalize_id("claude.ai Claude Docs") == "claude_ai_claude_docs"
        assert _normalize_id("warp@claude-code-warp") == "warp_at_claude_code_warp"

    def test_categorize_mcp(self):
        assert _categorize_mcp("mysql-prod") == PluginCategory.DATABASE
        assert _categorize_mcp("claude.ai Mixpanel") == PluginCategory.ANALYTICS
        assert _categorize_mcp("claude.ai Google Drive") == PluginCategory.DOCS
        assert _categorize_mcp("unknown-server") == PluginCategory.GENERAL

    def test_parse_mcp_list_output(self):
        output = """Checking MCP server health...

claude.ai Claude Docs: https://api.anthropic.com/v1/pages/mcp - ✓ Connected
mysql-qa: npx -y @benborla29/mcp-server-mysql - ✓ Connected
Jam: https://mcp.jam.dev/mcp (HTTP) - ! Needs authentication
"""
        servers = _parse_mcp_list_output(output)
        assert len(servers) == 3
        assert servers[0]["name"] == "claude.ai Claude Docs"
        assert servers[0]["healthy"] is True
        assert servers[1]["name"] == "mysql-qa"
        assert servers[2]["needs_auth"] is True

    def test_parse_mcp_empty_output(self):
        assert _parse_mcp_list_output("") == []
        assert _parse_mcp_list_output("Checking MCP server health...\n") == []

    def test_discover_mcp_from_permissions(self, tmp_path=None):
        """Test extracción de MCP servers desde permisos."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            settings_dir = Path(tmp) / ".claude"
            settings_dir.mkdir()
            settings_file = settings_dir / "settings.local.json"
            settings_file.write_text(json.dumps({
                "permissions": {
                    "allow": [
                        "mcp__mysql-prod__mysql_query",
                        "mcp__mysql-qa__mysql_query",
                        "mcp__claude_ai_Mixpanel__Run-Query",
                        "Bash(git status)",
                    ]
                }
            }))

            with patch("jarvis.plugins.discovery.Path.cwd", return_value=Path(tmp)):
                servers = discover_mcp_from_permissions()
                assert "mysql-prod" in servers
                assert "mysql-qa" in servers
                assert "claude_ai_Mixpanel" in servers
                assert len(servers) == 3


class TestPluginGuardian(unittest.TestCase):
    """Tests del Guardian."""

    @patch("jarvis.plugins.guardian.discover_all")
    @patch("jarvis.plugins.guardian.discover_mcp_from_permissions")
    def test_scan_populates_registry(self, mock_perms, mock_discover):
        mock_discover.return_value = [
            (
                PluginSpec(id="mcp.test", name="Test", source=PluginSource.MCP_BUILTIN),
                PluginHealth(plugin_id="mcp.test", status=PluginStatus.HEALTHY, detail="OK"),
            )
        ]
        mock_perms.return_value = []

        guardian = PluginGuardian()
        report = guardian.scan()

        assert report.total_discovered == 1
        assert report.healthy == 1
        assert guardian.registry.count == 1
        assert guardian.last_scan is not None

    @patch("jarvis.plugins.guardian.discover_all")
    @patch("jarvis.plugins.guardian.discover_mcp_from_permissions")
    def test_scan_detects_new_plugins(self, mock_perms, mock_discover):
        mock_perms.return_value = []
        spec = PluginSpec(id="mcp.new", name="New", source=PluginSource.MCP_NPM)
        health = PluginHealth(plugin_id="mcp.new", status=PluginStatus.HEALTHY)
        mock_discover.return_value = [(spec, health)]

        guardian = PluginGuardian()
        report = guardian.scan()

        assert "mcp.new" in report.new_plugins

    @patch("jarvis.plugins.guardian.discover_all")
    @patch("jarvis.plugins.guardian.discover_mcp_from_permissions")
    def test_scan_detects_lost_plugins(self, mock_perms, mock_discover):
        mock_perms.return_value = []

        # Primer scan con plugin
        spec = PluginSpec(id="mcp.old", name="Old", source=PluginSource.MCP_BUILTIN)
        health = PluginHealth(plugin_id="mcp.old", status=PluginStatus.HEALTHY)
        mock_discover.return_value = [(spec, health)]

        guardian = PluginGuardian()
        guardian.scan()

        # Segundo scan sin el plugin
        mock_discover.return_value = []
        report = guardian.scan()

        assert "mcp.old" in report.lost_plugins

    @patch("jarvis.plugins.guardian.discover_all")
    @patch("jarvis.plugins.guardian.discover_mcp_from_permissions")
    def test_validate_detects_orphan_permissions(self, mock_perms, mock_discover):
        mock_discover.return_value = []
        mock_perms.return_value = ["orphan_server"]

        guardian = PluginGuardian()
        guardian.scan()
        issues = guardian.validate()

        assert any("orphan_server" in i for i in issues)

    @patch("jarvis.plugins.guardian.discover_all")
    @patch("jarvis.plugins.guardian.discover_mcp_from_permissions")
    def test_validate_reports_unhealthy(self, mock_perms, mock_discover):
        spec = PluginSpec(id="mcp.sick", name="Sick", source=PluginSource.MCP_BUILTIN)
        health = PluginHealth(plugin_id="mcp.sick", status=PluginStatus.UNHEALTHY, detail="down")
        mock_discover.return_value = [(spec, health)]
        mock_perms.return_value = []

        guardian = PluginGuardian()
        guardian.scan()
        issues = guardian.validate()

        assert any("mcp.sick" in i for i in issues)

    @patch("jarvis.plugins.guardian.discover_all")
    @patch("jarvis.plugins.guardian.discover_mcp_from_permissions")
    def test_empty_scan(self, mock_perms, mock_discover):
        mock_discover.return_value = []
        mock_perms.return_value = []

        guardian = PluginGuardian()
        report = guardian.scan()

        assert report.total_discovered == 0
        assert report.healthy == 0
        assert guardian.registry.count == 0


if __name__ == "__main__":
    unittest.main()
