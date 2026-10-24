"""Tests para sistema de agentes — registry, echo agent, orchestrator."""

import pytest

from jarvis.agents.base import AgentRequest, AgentResult, AgentSpec, BaseAgent
from jarvis.agents.echo import EchoAgent
from jarvis.agents.registry import AgentRegistry
from jarvis.core.orchestrator import Orchestrator, detect_intent


# ---------------------------------------------------------------------------
# Mock agent for testing
# ---------------------------------------------------------------------------

class QAMockAgent(BaseAgent):
    def spec(self) -> AgentSpec:
        return AgentSpec(
            id="qa.mock",
            name="QA Mock",
            description="Mock QA agent",
            skills=["analyze_pr", "qa"],
            supported_projects=["integratepie"],
        )

    def execute(self, request: AgentRequest) -> AgentResult:
        return AgentResult(success=True, content="QA analysis done")


# ---------------------------------------------------------------------------
# Tests Agent Registry
# ---------------------------------------------------------------------------

class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()
        echo = EchoAgent()
        registry.register(echo)

        assert registry.get("core.echo") is echo
        assert registry.get("nonexistent") is None

    def test_list_all(self):
        registry = AgentRegistry()
        registry.register(EchoAgent())
        registry.register(QAMockAgent())

        specs = registry.list_all()
        assert len(specs) == 2
        ids = {s.id for s in specs}
        assert "core.echo" in ids
        assert "qa.mock" in ids

    def test_find_for_project(self):
        registry = AgentRegistry()
        registry.register(EchoAgent())       # todos los proyectos
        registry.register(QAMockAgent())      # solo integratepie

        pie_agents = registry.find_for_project("integratepie")
        assert len(pie_agents) == 2

        personal_agents = registry.find_for_project("personal")
        assert len(personal_agents) == 1
        assert personal_agents[0].agent_id == "core.echo"

    def test_count(self):
        registry = AgentRegistry()
        assert registry.count == 0
        registry.register(EchoAgent())
        assert registry.count == 1


# ---------------------------------------------------------------------------
# Tests Echo Agent
# ---------------------------------------------------------------------------

class TestEchoAgent:
    def test_spec(self):
        agent = EchoAgent()
        s = agent.spec()
        assert s.id == "core.echo"
        assert "general" in s.skills

    def test_execute(self):
        agent = EchoAgent()
        req = AgentRequest(intent="help", project="personal", payload={"question": "hola"})
        result = agent.execute(req)
        assert result.success is True
        assert "Echo" in result.content
        assert "help" in result.content

    def test_can_handle_all_projects(self):
        agent = EchoAgent()
        assert agent.can_handle("general", "personal") is True
        assert agent.can_handle("general", "integratepie") is True
        assert agent.can_handle("general", "kamecol") is True


# ---------------------------------------------------------------------------
# Tests Intent Detection
# ---------------------------------------------------------------------------

class TestDetectIntent:
    def test_analyze_pr(self):
        assert detect_intent("analiza el PR 1234") == "analyze_pr"
        assert detect_intent("review the pull request") == "analyze_pr"

    def test_qa(self):
        assert detect_intent("genera casos de prueba") == "qa"
        assert detect_intent("escenarios gherkin") == "qa"

    def test_code(self):
        assert detect_intent("hay un bug en la función") == "code"
        assert detect_intent("refactor this class") == "code"

    def test_memory(self):
        assert detect_intent("qué sabes de IntegratePIE") == "memory"
        assert detect_intent("recuerda esto") == "memory"

    def test_help(self):
        assert detect_intent("qué puedes hacer") == "help"
        assert detect_intent("ayuda") == "help"

    def test_general_fallback(self):
        assert detect_intent("hola") == "general"
        assert detect_intent("buen día") == "general"


# ---------------------------------------------------------------------------
# Tests Orchestrator
# ---------------------------------------------------------------------------

class TestOrchestrator:
    def _make_orchestrator(self):
        registry = AgentRegistry()
        registry.register(EchoAgent())
        registry.register(QAMockAgent())
        return Orchestrator(agent_registry=registry)

    def test_route_to_echo(self):
        orch = self._make_orchestrator()
        req = AgentRequest(payload={"question": "hola"}, project="personal")
        result = orch.route(req)
        assert result.success is True
        assert result.agent_id == "core.echo"

    def test_route_qa_to_mock(self):
        orch = self._make_orchestrator()
        req = AgentRequest(payload={"question": "analiza el PR 100"}, project="integratepie")
        result = orch.route(req)
        assert result.success is True
        assert result.agent_id == "qa.mock"

    def test_route_no_agent_found(self):
        registry = AgentRegistry()
        # QA mock solo soporta integratepie
        registry.register(QAMockAgent())
        orch = Orchestrator(agent_registry=registry)

        req = AgentRequest(payload={"question": "hola"}, project="personal")
        result = orch.route(req)
        assert result.success is False
        assert "Sin agente" in result.error

    def test_route_sets_duration(self):
        orch = self._make_orchestrator()
        req = AgentRequest(payload={"question": "status"}, project="personal")
        result = orch.route(req)
        assert result.duration_ms >= 0

    def test_route_with_event_store(self, tmp_path):
        from jarvis.core.events import EventStore

        store = EventStore(db_path=str(tmp_path / "events.db"))
        registry = AgentRegistry()
        registry.register(EchoAgent())
        orch = Orchestrator(agent_registry=registry, event_store=store)

        req = AgentRequest(payload={"question": "test"}, project="personal")
        orch.route(req)

        events = store.query()
        assert len(events) >= 2  # action + observation
        store.close()
