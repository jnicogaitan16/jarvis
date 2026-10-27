"""Tests del sistema de pipelines multi-agente."""

from __future__ import annotations

import unittest

from jarvis.agents.base import AgentRequest, AgentResult, AgentSpec, BaseAgent
from jarvis.agents.registry import AgentRegistry
from jarvis.pipelines.engine import PipelineEngine
from jarvis.pipelines.models import (
    PipelineDef,
    PipelineResult,
    PipelineStep,
    StepResult,
    StepStatus,
)
from jarvis.pipelines.workflows import (
    WORKFLOWS,
    get_workflow,
    list_workflows,
)


# ---------------------------------------------------------------------------
# Agentes mock para tests
# ---------------------------------------------------------------------------

class MockAgentA(BaseAgent):
    def spec(self) -> AgentSpec:
        return AgentSpec(id="mock.a", name="Mock A", description="Agent A")

    def execute(self, request: AgentRequest) -> AgentResult:
        return AgentResult(
            success=True,
            content=f"Result from A: {request.payload.get('question', '')}",
            data={"source": "a"},
        )


class MockAgentB(BaseAgent):
    def spec(self) -> AgentSpec:
        return AgentSpec(id="mock.b", name="Mock B", description="Agent B")

    def execute(self, request: AgentRequest) -> AgentResult:
        prev = request.payload.get("previous_context", "")
        return AgentResult(
            success=True,
            content=f"Result from B (prev: {bool(prev)})",
            data={"source": "b", "has_previous": bool(prev)},
        )


class MockFailAgent(BaseAgent):
    def spec(self) -> AgentSpec:
        return AgentSpec(id="mock.fail", name="Mock Fail", description="Fails")

    def execute(self, request: AgentRequest) -> AgentResult:
        return AgentResult(success=False, error="Deliberate failure")


class MockExceptionAgent(BaseAgent):
    def spec(self) -> AgentSpec:
        return AgentSpec(id="mock.exception", name="Mock Exception", description="Raises")

    def execute(self, request: AgentRequest) -> AgentResult:
        raise RuntimeError("Boom")


# ---------------------------------------------------------------------------
# Test Models
# ---------------------------------------------------------------------------

class TestPipelineModels(unittest.TestCase):

    def test_step_status_enum(self):
        assert StepStatus.COMPLETED == "completed"
        assert StepStatus.FAILED == "failed"
        assert StepStatus.SKIPPED == "skipped"

    def test_pipeline_step_frozen(self):
        step = PipelineStep(agent_id="x", name="X")
        with self.assertRaises(AttributeError):
            step.agent_id = "y"

    def test_pipeline_def_frozen(self):
        pipe = PipelineDef(id="x", name="X", description="D", steps=[])
        with self.assertRaises(AttributeError):
            pipe.id = "y"

    def test_pipeline_result_properties(self):
        result = PipelineResult(
            pipeline_id="test",
            pipeline_name="Test",
            success=True,
            steps=[
                StepResult(step_name="A", agent_id="a", status=StepStatus.COMPLETED),
                StepResult(step_name="B", agent_id="b", status=StepStatus.FAILED),
                StepResult(step_name="C", agent_id="c", status=StepStatus.SKIPPED),
            ],
        )
        assert result.completed_steps == 1
        assert result.failed_steps == 1

    def test_pipeline_result_summary(self):
        result = PipelineResult(
            pipeline_id="test",
            pipeline_name="Test Pipeline",
            success=True,
            steps=[
                StepResult(step_name="Step 1", agent_id="a", status=StepStatus.COMPLETED, content="Hello"),
            ],
            total_duration_ms=100,
        )
        summary = result.summary()
        assert "Test Pipeline" in summary
        assert "Exitoso" in summary
        assert "Hello" in summary


# ---------------------------------------------------------------------------
# Test Engine
# ---------------------------------------------------------------------------

class TestPipelineEngine(unittest.TestCase):

    def _make_engine(self, agents: list[BaseAgent]) -> PipelineEngine:
        registry = AgentRegistry()
        for agent in agents:
            registry.register(agent)
        return PipelineEngine(agent_registry=registry)

    def test_simple_pipeline(self):
        engine = self._make_engine([MockAgentA()])
        pipeline = PipelineDef(
            id="simple", name="Simple", description="One step",
            steps=[PipelineStep(agent_id="mock.a", name="Step A")],
        )
        result = engine.execute(pipeline, "hello")
        assert result.success
        assert result.completed_steps == 1
        assert "Result from A" in result.steps[0].content

    def test_multi_step_pipeline(self):
        engine = self._make_engine([MockAgentA(), MockAgentB()])
        pipeline = PipelineDef(
            id="multi", name="Multi", description="Two steps",
            steps=[
                PipelineStep(agent_id="mock.a", name="Step A"),
                PipelineStep(agent_id="mock.b", name="Step B"),
            ],
        )
        result = engine.execute(pipeline, "hello")
        assert result.success
        assert result.completed_steps == 2
        # Step B should have received previous context from Step A
        assert result.steps[1].data.get("has_previous") is True

    def test_context_passes_between_steps(self):
        engine = self._make_engine([MockAgentA(), MockAgentB()])
        pipeline = PipelineDef(
            id="ctx", name="Context", description="Context passing",
            steps=[
                PipelineStep(agent_id="mock.a", name="Step A"),
                PipelineStep(agent_id="mock.b", name="Step B"),
            ],
        )
        result = engine.execute(pipeline, "test input")
        assert result.success
        # Step B should report it has previous context
        assert result.steps[1].data["has_previous"] is True

    def test_stop_on_fail(self):
        engine = self._make_engine([MockFailAgent(), MockAgentA()])
        pipeline = PipelineDef(
            id="fail", name="Fail", description="Fails on step 1",
            steps=[
                PipelineStep(agent_id="mock.fail", name="Failing step", stop_on_fail=True),
                PipelineStep(agent_id="mock.a", name="Should be skipped"),
            ],
        )
        result = engine.execute(pipeline, "hello")
        assert not result.success
        assert result.steps[0].status == StepStatus.FAILED
        assert result.steps[1].status == StepStatus.SKIPPED

    def test_continue_on_fail(self):
        engine = self._make_engine([MockFailAgent(), MockAgentA()])
        pipeline = PipelineDef(
            id="continue", name="Continue", description="Continues after fail",
            steps=[
                PipelineStep(agent_id="mock.fail", name="Failing step", stop_on_fail=False),
                PipelineStep(agent_id="mock.a", name="Should run"),
            ],
        )
        result = engine.execute(pipeline, "hello")
        # Pipeline still succeeds overall since we didn't stop
        assert result.steps[0].status == StepStatus.FAILED
        assert result.steps[1].status == StepStatus.COMPLETED

    def test_agent_not_found(self):
        engine = self._make_engine([])
        pipeline = PipelineDef(
            id="missing", name="Missing", description="Agent missing",
            steps=[PipelineStep(agent_id="nonexistent", name="Missing agent")],
        )
        result = engine.execute(pipeline, "hello")
        assert not result.success
        assert "no encontrado" in result.steps[0].error

    def test_agent_exception(self):
        engine = self._make_engine([MockExceptionAgent()])
        pipeline = PipelineDef(
            id="exc", name="Exception", description="Agent raises",
            steps=[PipelineStep(agent_id="mock.exception", name="Boom step")],
        )
        result = engine.execute(pipeline, "hello")
        assert not result.success
        assert "Boom" in result.steps[0].error

    def test_input_map(self):
        engine = self._make_engine([MockAgentA(), MockAgentB()])
        pipeline = PipelineDef(
            id="map", name="Map", description="Input mapping",
            steps=[
                PipelineStep(agent_id="mock.a", name="Step A"),
                PipelineStep(
                    agent_id="mock.b",
                    name="Step B",
                    input_map={"code": "step_1_content"},
                ),
            ],
        )
        result = engine.execute(pipeline, "input")
        assert result.success
        assert result.completed_steps == 2

    def test_duration_tracked(self):
        engine = self._make_engine([MockAgentA()])
        pipeline = PipelineDef(
            id="dur", name="Duration", description="Tracks time",
            steps=[PipelineStep(agent_id="mock.a", name="Step A")],
        )
        result = engine.execute(pipeline, "hello")
        assert result.total_duration_ms >= 0
        assert result.steps[0].duration_ms >= 0

    def test_empty_pipeline(self):
        engine = self._make_engine([])
        pipeline = PipelineDef(id="empty", name="Empty", description="No steps", steps=[])
        result = engine.execute(pipeline, "hello")
        assert result.success
        assert len(result.steps) == 0


# ---------------------------------------------------------------------------
# Test Workflows
# ---------------------------------------------------------------------------

class TestWorkflows(unittest.TestCase):

    def test_all_workflows_defined(self):
        assert len(WORKFLOWS) >= 4

    def test_get_workflow(self):
        wf = get_workflow("full_qa_review")
        assert wf is not None
        assert wf.id == "full_qa_review"
        assert len(wf.steps) == 4

    def test_get_workflow_nonexistent(self):
        assert get_workflow("nope") is None

    def test_list_workflows(self):
        wfs = list_workflows()
        assert len(wfs) >= 4
        ids = {w.id for w in wfs}
        assert "full_qa_review" in ids
        assert "feature_planning" in ids
        assert "security_audit" in ids
        assert "bug_triage" in ids

    def test_all_steps_reference_real_agents(self):
        """Verificar que todos los workflows referencian agentes que existen."""
        known_agents = {
            "qa.code_review", "qa.gherkin", "qa.strategy", "qa.writer",
            "qa.analyzer", "core.echo", "biz.kamecol",
        }
        for wf in list_workflows():
            for step in wf.steps:
                assert step.agent_id in known_agents, (
                    f"Workflow '{wf.id}' referencia agente desconocido: '{step.agent_id}'"
                )

    def test_feature_planning_steps(self):
        wf = get_workflow("feature_planning")
        assert len(wf.steps) == 2
        assert wf.steps[0].agent_id == "qa.gherkin"
        assert wf.steps[1].agent_id == "qa.strategy"

    def test_bug_triage_has_soft_fail(self):
        wf = get_workflow("bug_triage")
        code_review_step = next(s for s in wf.steps if s.agent_id == "qa.code_review")
        assert code_review_step.stop_on_fail is False


class TestWorkflowsWithRealAgents(unittest.TestCase):
    """Tests de integración ligeros con agentes reales."""

    def _make_real_engine(self) -> PipelineEngine:
        from jarvis.agents.echo import EchoAgent
        from jarvis.agents.qa.code_review_agent import CodeReviewAgent
        from jarvis.agents.qa.gherkin_agent import GherkinAgent
        from jarvis.agents.qa.test_strategy_agent import TestStrategyAgent
        from jarvis.agents.qa.writer_agent import WriterAgent

        registry = AgentRegistry()
        registry.register(EchoAgent())
        registry.register(WriterAgent())
        registry.register(GherkinAgent())
        registry.register(TestStrategyAgent())
        registry.register(CodeReviewAgent())
        return PipelineEngine(agent_registry=registry)

    def test_feature_planning_real(self):
        engine = self._make_real_engine()
        wf = get_workflow("feature_planning")
        result = engine.execute(wf, "login de usuarios con email y contraseña")
        assert result.success
        assert result.completed_steps == 2
        assert "Feature:" in result.steps[0].content
        assert "Estrategia" in result.steps[1].content or "Recomendaciones" in result.steps[1].content

    def test_full_qa_review_real(self):
        engine = self._make_real_engine()
        wf = get_workflow("full_qa_review")
        result = engine.execute(wf, "endpoint API de pagos con validación de tarjeta")
        assert result.success
        assert result.completed_steps == 4

    def test_bug_triage_real(self):
        engine = self._make_real_engine()
        wf = get_workflow("bug_triage")
        result = engine.execute(wf, "el checkout falla cuando el usuario usa tarjeta de crédito expirada")
        assert result.success or result.completed_steps >= 2


if __name__ == "__main__":
    unittest.main()
