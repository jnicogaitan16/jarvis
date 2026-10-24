"""Tests para modelos Pydantic core."""

import pytest
from pydantic import ValidationError

from jarvis.core.models import (
    Event,
    EventType,
    JobStatus,
    MemoryRecord,
    MemoryType,
    OperationType,
    ProjectContext,
    SystemStatus,
    ToolAction,
    ToolObservation,
)


class TestEvent:
    def test_create_event(self):
        event = Event(event_type=EventType.ACTION, payload={"test": True})
        assert event.event_type == EventType.ACTION
        assert event.payload == {"test": True}
        assert event.id  # auto-generated
        assert event.timestamp  # auto-generated

    def test_event_is_frozen(self):
        event = Event(event_type=EventType.SYSTEM)
        with pytest.raises(ValidationError):
            event.event_type = EventType.ERROR

    def test_event_with_all_fields(self):
        event = Event(
            event_type=EventType.OBSERVATION,
            agent_id="qa.analyzer",
            project="integratepie",
            payload={"findings": 3},
            parent_event_id="abc123",
        )
        assert event.agent_id == "qa.analyzer"
        assert event.project == "integratepie"
        assert event.parent_event_id == "abc123"


class TestProjectContext:
    def test_create_minimal(self):
        ctx = ProjectContext(project_id="test", display_name="Test")
        assert ctx.project_id == "test"
        assert ctx.memory_namespace == "test"  # auto-set from project_id
        assert "ollama" in ctx.allowed_providers

    def test_frozen(self):
        ctx = ProjectContext(project_id="test", display_name="Test")
        with pytest.raises(ValidationError):
            ctx.project_id = "other"

    def test_custom_namespace(self):
        ctx = ProjectContext(
            project_id="test",
            display_name="Test",
            memory_namespace="custom_ns",
        )
        assert ctx.memory_namespace == "custom_ns"

    def test_sensitive_patterns(self):
        ctx = ProjectContext(
            project_id="pie",
            display_name="PIE",
            sensitive_patterns=frozenset({"rut", "run"}),
        )
        assert "rut" in ctx.sensitive_patterns
        assert "run" in ctx.sensitive_patterns


class TestToolAction:
    def test_create(self):
        action = ToolAction(tool_id="git.diff", parameters={"file": "test.py"})
        assert action.tool_id == "git.diff"
        assert action.correlation_id  # auto-generated

    def test_frozen(self):
        action = ToolAction(tool_id="test")
        with pytest.raises(ValidationError):
            action.tool_id = "other"


class TestToolObservation:
    def test_success(self):
        obs = ToolObservation(tool_id="git.diff", success=True, result={"lines": 42})
        assert obs.success is True

    def test_failure(self):
        obs = ToolObservation(tool_id="git.diff", success=False, error="not found")
        assert obs.success is False
        assert obs.error == "not found"


class TestMemoryRecord:
    def test_create(self):
        rec = MemoryRecord(
            project="integratepie",
            memory_type=MemoryType.SEMANTIC,
            source="audit",
            content="IntegratePIE usa PHP 8.4",
        )
        assert rec.project == "integratepie"
        assert rec.confidence == 1.0
        assert rec.status == "active"
        assert rec.version == 1

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            MemoryRecord(
                project="t", memory_type=MemoryType.SEMANTIC,
                source="t", content="t", confidence=1.5,
            )
        with pytest.raises(ValidationError):
            MemoryRecord(
                project="t", memory_type=MemoryType.SEMANTIC,
                source="t", content="t", confidence=-0.1,
            )


class TestEnums:
    def test_event_type_values(self):
        assert EventType.ACTION == "action"
        assert EventType.OBSERVATION == "observation"

    def test_job_status_values(self):
        assert JobStatus.CREATED == "created"
        assert JobStatus.SUCCEEDED == "succeeded"

    def test_memory_type_values(self):
        assert MemoryType.SEMANTIC == "semantic"
        assert MemoryType.EPISODIC == "episodic"

    def test_operation_type_values(self):
        assert OperationType.READ == "read"
        assert OperationType.PUBLISH == "publish"


class TestSystemStatus:
    def test_create(self):
        status = SystemStatus(version="0.1.0", environment="test")
        assert status.version == "0.1.0"
        assert status.events_count == 0
