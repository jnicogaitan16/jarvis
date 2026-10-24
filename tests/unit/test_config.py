"""Tests para sistema de configuración."""

from jarvis.config import list_projects, load_global_config, load_project_context


class TestConfig:
    def test_load_global_config(self):
        config = load_global_config()
        assert "jarvis" in config
        assert config["jarvis"]["version"] == "0.1.0"

    def test_load_project_context_personal(self):
        ctx = load_project_context("personal")
        assert ctx.project_id == "personal"
        assert ctx.display_name == "Personal"
        assert ctx.allow_cloud is True
        assert "ollama" in ctx.allowed_providers

    def test_load_project_context_integratepie(self):
        ctx = load_project_context("integratepie")
        assert ctx.project_id == "integratepie"
        assert ctx.display_name == "IntegratePIE"
        assert "rut" in ctx.sensitive_patterns

    def test_load_project_context_kamecol(self):
        ctx = load_project_context("kamecol")
        assert ctx.project_id == "kamecol"
        assert ctx.display_name == "KameCol"
        assert "cedula" in ctx.sensitive_patterns

    def test_load_nonexistent_project(self):
        ctx = load_project_context("nonexistent")
        assert ctx.project_id == "nonexistent"
        assert ctx.display_name == "nonexistent"  # fallback

    def test_list_projects(self):
        projects = list_projects()
        assert "personal" in projects
        assert "integratepie" in projects
        assert "kamecol" in projects


class TestMemoryNamespaceIsolation:
    def test_each_project_has_unique_namespace(self):
        personal = load_project_context("personal")
        pie = load_project_context("integratepie")
        kc = load_project_context("kamecol")

        namespaces = {personal.memory_namespace, pie.memory_namespace, kc.memory_namespace}
        assert len(namespaces) == 3  # all unique
