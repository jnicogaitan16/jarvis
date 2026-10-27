"""Tests de los agentes QA profesionales."""

from __future__ import annotations

import unittest

from jarvis.agents.base import AgentRequest
from jarvis.agents.qa.code_review_agent import CodeReviewAgent
from jarvis.agents.qa.gherkin_agent import GherkinAgent, GherkinFeature, GherkinScenario
from jarvis.agents.qa.templates import (
    CommentType,
    get_template,
    list_templates,
    render_template,
)
from jarvis.agents.qa.test_strategy_agent import TestStrategyAgent
from jarvis.agents.qa.writer_agent import WriterAgent

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

class TestTemplates(unittest.TestCase):

    def test_list_templates(self):
        templates = list_templates()
        assert len(templates) == 5

    def test_get_template(self):
        tmpl = get_template(CommentType.BUG_REPORT)
        assert tmpl.comment_type == CommentType.BUG_REPORT
        assert "resumen" in tmpl.sections

    def test_render_bug_report(self):
        result = render_template(
            CommentType.BUG_REPORT,
            title="Login falla",
            summary="El login no funciona con contraseña vacía",
        )
        assert "Bug Report" in result
        assert "Login falla" in result

    def test_render_with_missing_fields(self):
        result = render_template(CommentType.DEV_QUESTION, title="Test")
        assert "Test" in result
        assert "_[" in result  # campos faltantes usan placeholder _[field_name]_

    def test_all_comment_types(self):
        for ct in CommentType:
            tmpl = get_template(ct)
            assert tmpl is not None
            assert len(tmpl.sections) > 0


# ---------------------------------------------------------------------------
# WriterAgent
# ---------------------------------------------------------------------------

class TestWriterAgent(unittest.TestCase):

    def setUp(self):
        self.agent = WriterAgent()

    def test_spec(self):
        spec = self.agent.spec()
        assert spec.id == "qa.writer"
        assert "write" in spec.skills

    def test_detect_bug_report(self):
        req = AgentRequest(intent="write", payload={"question": "bug: el login se cae con contraseña vacía"})
        result = self.agent.execute(req)
        assert result.success
        assert "Bug Report" in result.content

    def test_detect_dev_question(self):
        req = AgentRequest(intent="write", payload={"question": "pregunta para dev: por qué el endpoint retorna 500"})
        result = self.agent.execute(req)
        assert result.success
        assert "Pregunta" in result.content

    def test_detect_team_notification(self):
        req = AgentRequest(intent="write", payload={"question": "notifica al equipo: deploy hotfix v2.3"})
        result = self.agent.execute(req)
        assert result.success
        assert "Notificación" in result.content or "equipo" in result.content.lower()

    def test_list_templates_action(self):
        req = AgentRequest(intent="write", payload={"question": "lista de templates disponibles"})
        result = self.agent.execute(req)
        assert result.success
        assert "bug_report" in result.content

    def test_help_action(self):
        req = AgentRequest(intent="write", payload={"question": "ayuda con el writer"})
        result = self.agent.execute(req)
        assert result.success
        assert "Ejemplos" in result.content or "ejemplo" in result.content.lower()

    def test_severity_detection(self):
        req = AgentRequest(intent="write", payload={"question": "bug crítico: crash en producción"})
        result = self.agent.execute(req)
        assert result.success
        assert "Crítica" in result.content

    def test_general_comment(self):
        req = AgentRequest(intent="write", payload={"question": "algo genérico sin keywords específicos xyz"})
        result = self.agent.execute(req)
        assert result.success
        assert "Comentario QA" in result.content


# ---------------------------------------------------------------------------
# GherkinAgent
# ---------------------------------------------------------------------------

class TestGherkinAgent(unittest.TestCase):

    def setUp(self):
        self.agent = GherkinAgent()

    def test_spec(self):
        spec = self.agent.spec()
        assert spec.id == "qa.gherkin"
        assert "gherkin" in spec.skills

    def test_generate_login_feature(self):
        req = AgentRequest(intent="gherkin", payload={"question": "gherkin para login de usuarios con email"})
        result = self.agent.execute(req)
        assert result.success
        assert "Feature:" in result.content
        assert "Scenario:" in result.content
        assert "Given" in result.content
        assert "When" in result.content
        assert "Then" in result.content

    def test_generates_security_scenario_for_auth(self):
        req = AgentRequest(intent="gherkin", payload={"question": "escenarios para login con password"})
        result = self.agent.execute(req)
        assert result.success
        assert "security" in result.content.lower() or "autorizado" in result.content.lower()

    def test_generates_validation_scenarios(self):
        req = AgentRequest(intent="gherkin", payload={"question": "gherkin para formulario con campos obligatorios y email"})
        result = self.agent.execute(req)
        assert result.success
        assert "obligatorio" in result.content.lower() or "validation" in result.content.lower()

    def test_tags_extraction(self):
        req = AgentRequest(intent="gherkin", payload={"question": "gherkin para endpoint API de pagos"})
        result = self.agent.execute(req)
        assert result.success
        assert "@api" in result.content or "@payment" in result.content

    def test_help(self):
        req = AgentRequest(intent="gherkin", payload={"question": "ayuda"})
        result = self.agent.execute(req)
        assert result.success
        assert "Gherkin" in result.content

    def test_scenario_render(self):
        scenario = GherkinScenario(
            name="Test scenario",
            given=["a precondition"],
            when=["an action"],
            then=["a result"],
            tags=["smoke"],
        )
        rendered = scenario.render()
        assert "Scenario: Test scenario" in rendered
        assert "Given a precondition" in rendered
        assert "@smoke" in rendered

    def test_feature_render(self):
        feature = GherkinFeature(
            name="Test Feature",
            description="A test description",
            scenarios=[
                GherkinScenario(name="S1", given=["X"], when=["Y"], then=["Z"]),
            ],
            tags=["regression"],
        )
        rendered = feature.render()
        assert "Feature: Test Feature" in rendered
        assert "@regression" in rendered


# ---------------------------------------------------------------------------
# TestStrategyAgent
# ---------------------------------------------------------------------------

class TestTestStrategyAgent(unittest.TestCase):

    def setUp(self):
        self.agent = TestStrategyAgent()

    def test_spec(self):
        spec = self.agent.spec()
        assert spec.id == "qa.strategy"
        assert "test_strategy" in spec.skills

    def test_plan_api_testing(self):
        req = AgentRequest(intent="test_strategy", payload={"question": "estrategia de testing para el endpoint API de órdenes"})
        result = self.agent.execute(req)
        assert result.success
        assert "API" in result.content or "api" in result.content
        assert "Recomendaciones" in result.content

    def test_plan_includes_smoke(self):
        req = AgentRequest(intent="test_strategy", payload={"question": "plan de pruebas para el login"})
        result = self.agent.execute(req)
        assert result.success
        assert "smoke" in result.content.lower()

    def test_automation_assessment_api(self):
        req = AgentRequest(
            intent="test_strategy",
            payload={"question": "vale la pena automatizar los tests del API de pagos crítico"}
        )
        result = self.agent.execute(req)
        assert result.success
        assert result.data.get("should_automate") is True

    def test_automation_against_exploratory(self):
        req = AgentRequest(
            intent="test_strategy",
            payload={"question": "¿debería automatizar testing exploratorio de usabilidad UX?"}
        )
        result = self.agent.execute(req)
        assert result.success
        # Exploratory/UX should have lower confidence
        assert result.data.get("confidence", 1.0) < 0.6

    def test_help(self):
        req = AgentRequest(intent="test_strategy", payload={"question": "ayuda"})
        result = self.agent.execute(req)
        assert result.success
        assert "Planner" in result.content or "estrategia" in result.content.lower()

    def test_data_structure(self):
        req = AgentRequest(intent="test_strategy", payload={"question": "estrategia para checkout e-commerce"})
        result = self.agent.execute(req)
        assert "recommendations" in result.data
        assert "should_automate" in result.data


# ---------------------------------------------------------------------------
# CodeReviewAgent
# ---------------------------------------------------------------------------

class TestCodeReviewAgent(unittest.TestCase):

    def setUp(self):
        self.agent = CodeReviewAgent()

    def test_spec(self):
        spec = self.agent.spec()
        assert spec.id == "qa.code_review"
        assert "code_review" in spec.skills

    def test_detect_hardcoded_secret(self):
        code = 'password = "super_secret_123"'
        req = AgentRequest(intent="code_review", payload={"code": code})
        result = self.agent.execute(req)
        assert result.success
        assert result.data["findings_count"] >= 1
        assert "critical" in result.data.get("by_severity", {}) or "Credencial" in result.content

    def test_detect_eval(self):
        code = 'result = eval(user_input)'
        req = AgentRequest(intent="code_review", payload={"code": code})
        result = self.agent.execute(req)
        assert result.success
        assert "eval" in result.content.lower()

    def test_detect_bare_except(self):
        code = """try:
    something()
except:
    pass"""
        req = AgentRequest(intent="code_review", payload={"code": code})
        result = self.agent.execute(req)
        assert result.success
        assert result.data["findings_count"] >= 1

    def test_detect_print_debug(self):
        code = 'print("debugging here")'
        req = AgentRequest(intent="code_review", payload={"code": code})
        result = self.agent.execute(req)
        assert result.success
        assert "print" in result.content.lower()

    def test_clean_code(self):
        code = """def add(a: int, b: int) -> int:
    return a + b"""
        req = AgentRequest(intent="code_review", payload={"code": code})
        result = self.agent.execute(req)
        assert result.success
        assert result.data["findings_count"] == 0 or "Sin hallazgos" in result.content

    def test_complexity_long_function(self):
        lines = ["def very_long_function():"]
        for i in range(55):
            lines.append(f"    x_{i} = {i}")
        lines.append("def another():")
        lines.append("    pass")
        code = "\n".join(lines)
        req = AgentRequest(intent="code_review", payload={"code": code})
        result = self.agent.execute(req)
        assert result.success
        assert "larga" in result.content.lower() or "long" in result.content.lower()

    def test_help(self):
        req = AgentRequest(intent="code_review", payload={"question": "ayuda"})
        result = self.agent.execute(req)
        assert result.success
        assert "Code Review" in result.content

    def test_question_fallback(self):
        req = AgentRequest(
            intent="code_review",
            payload={"question": 'revisa: api_key = "abc123"'}
        )
        result = self.agent.execute(req)
        assert result.success
        assert result.data["findings_count"] >= 1


# ---------------------------------------------------------------------------
# Intent detection (orchestrator)
# ---------------------------------------------------------------------------

class TestNewIntents(unittest.TestCase):
    """Verificar que los nuevos intents se detectan correctamente."""

    def test_gherkin_intent(self):
        from jarvis.core.orchestrator import detect_intent
        assert detect_intent("genera gherkin para login") == "gherkin"
        assert detect_intent("escenarios BDD para el checkout") == "gherkin"

    def test_write_intent(self):
        from jarvis.core.orchestrator import detect_intent
        assert detect_intent("escribe un bug report del login") == "write"
        assert detect_intent("redacta una notificación para el equipo") == "write"

    def test_test_strategy_intent(self):
        from jarvis.core.orchestrator import detect_intent
        assert detect_intent("estrategia de testing para la API") == "test_strategy"
        assert detect_intent("¿vale la pena automatizar estos tests?") == "test_strategy"

    def test_code_review_intent(self):
        from jarvis.core.orchestrator import detect_intent
        assert detect_intent("code review del módulo de pagos") == "code_review"
        assert detect_intent("análisis estático del código") == "code_review"

    def test_existing_intents_preserved(self):
        from jarvis.core.orchestrator import detect_intent
        assert detect_intent("analiza el PR #123") == "analyze_pr"
        assert detect_intent("status del sistema") == "status"
        assert detect_intent("ayuda") == "help"


if __name__ == "__main__":
    unittest.main()
