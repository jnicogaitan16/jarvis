"""Tests para SecurityGate."""

from jarvis.core.models import ProjectContext
from jarvis.security.context import SecurityGate


class TestSecurityGate:
    def setup_method(self):
        self.gate = SecurityGate()

    def test_check_tool_access_no_restrictions(self, personal_context):
        assert self.gate.check_tool_access("any_tool", personal_context) is True

    def test_check_tool_access_with_allowlist(self):
        ctx = ProjectContext(
            project_id="restricted",
            display_name="Restricted",
            allowed_tools=frozenset({"git.diff", "git.log"}),
        )
        assert self.gate.check_tool_access("git.diff", ctx) is True
        assert self.gate.check_tool_access("git.log", ctx) is True
        assert self.gate.check_tool_access("azdo.publish", ctx) is False

    def test_check_provider_access(self, integratepie_context):
        assert self.gate.check_provider_access("ollama", integratepie_context) is True
        assert self.gate.check_provider_access("gemini", integratepie_context) is True
        assert self.gate.check_provider_access("openai", integratepie_context) is False

    def test_check_memory_access_same_project(self, integratepie_context):
        assert self.gate.check_memory_access("integratepie", integratepie_context) is True

    def test_check_memory_access_system(self, integratepie_context):
        assert self.gate.check_memory_access("system", integratepie_context) is True

    def test_check_memory_access_cross_project_denied(self, integratepie_context):
        assert self.gate.check_memory_access("kamecol", integratepie_context) is False

    def test_sanitize_api_keys(self):
        text = "la clave es ANTHROPIC_API_KEY=sk-ant-abc123def456"
        result = self.gate.sanitize_for_logging(text)
        assert "sk-ant-" not in result
        assert "[REDACTED]" in result

    def test_sanitize_gemini_key(self):
        text = "GEMINI_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrst"
        result = self.gate.sanitize_for_logging(text)
        assert "AIzaSy" not in result

    def test_sanitize_rut(self):
        text = "El alumno con RUT 12.345.678-9 tiene diagnóstico"
        result = self.gate.sanitize_for_logging(text)
        assert "12.345.678-9" not in result

    def test_sanitize_for_cloud_with_sensitive_patterns(self, integratepie_context):
        text = "Datos del alumno: run 12345, nombre_alumno Juan, rut 12.345.678-k"
        result = self.gate.sanitize_for_cloud(text, integratepie_context)
        assert "run" not in result.lower() or "[REDACTED]" in result
        assert "nombre_alumno" not in result.lower() or "[REDACTED]" in result

    def test_sanitize_preserves_normal_text(self):
        text = "Este es un análisis normal sin datos sensibles"
        result = self.gate.sanitize_for_logging(text)
        assert result == text

    def test_sanitize_github_token(self):
        text = "token: ghp_abcdefghijklmnopqrstuvwxyz1234567890"
        result = self.gate.sanitize_for_logging(text)
        assert "ghp_" not in result
