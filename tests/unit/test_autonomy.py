"""Tests para framework de autonomía y model selector."""

import pytest

from jarvis.core.models import OperationType, ProjectContext
from jarvis.llm.base import TaskComplexity
from jarvis.llm.model_selector import ModelSelector, ModelProfile, ModelSelection
from jarvis.security.autonomy import (
    ApprovalPolicy,
    ApprovalResult,
    AutonomyLevel,
    AutonomyManager,
)


class TestAutonomyLevels:
    def test_levels(self):
        assert AutonomyLevel.CONSULT == 0
        assert AutonomyLevel.PROPOSE == 1
        assert AutonomyLevel.EXECUTE == 2
        assert AutonomyLevel.COORDINATE == 3
        assert AutonomyLevel.DELEGATE == 4


class TestAutonomyManager:
    def _ctx(self, level: int = 0):
        return ProjectContext(project_id="test", display_name="Test", autonomy_level=level)

    def test_read_always_allowed(self):
        mgr = AutonomyManager()
        result = mgr.check_permission(OperationType.READ, self._ctx(0))
        assert result.approved is True

    def test_analyze_always_allowed(self):
        mgr = AutonomyManager()
        result = mgr.check_permission(OperationType.ANALYZE, self._ctx(0))
        assert result.approved is True

    def test_propose_requires_level_1(self):
        mgr = AutonomyManager()
        assert mgr.check_permission(OperationType.PROPOSE, self._ctx(0)).approved is False
        assert mgr.check_permission(OperationType.PROPOSE, self._ctx(1)).approved is True

    def test_execute_requires_level_2(self):
        mgr = AutonomyManager()
        assert mgr.check_permission(OperationType.EXECUTE, self._ctx(1)).approved is False
        assert mgr.check_permission(OperationType.EXECUTE, self._ctx(2)).approved is True

    def test_publish_always_requires_approval(self):
        mgr = AutonomyManager()
        result = mgr.check_permission(OperationType.PUBLISH, self._ctx(4))
        assert result.approved is False
        assert "aprobación humana" in result.reason

    def test_delete_always_requires_approval(self):
        mgr = AutonomyManager()
        result = mgr.check_permission(OperationType.DELETE, self._ctx(4))
        assert result.approved is False

    def test_request_and_approve(self):
        mgr = AutonomyManager()
        req = mgr.request_approval(OperationType.PUBLISH, "qa.analyzer", "pie", "Publicar reporte")
        assert req.status == "pending"
        assert len(mgr.list_pending()) == 1

        mgr.approve(req.id)
        assert len(mgr.list_pending()) == 0
        assert len(mgr.list_history()) == 1
        assert mgr.list_history()[0].status == "approved"

    def test_request_and_reject(self):
        mgr = AutonomyManager()
        req = mgr.request_approval(OperationType.DELETE, "x", "y", "Delete something")
        mgr.reject(req.id, "Not now")
        assert mgr.list_history()[0].status == "rejected"

    def test_approve_nonexistent(self):
        mgr = AutonomyManager()
        assert mgr.approve("fake") is False

    def test_is_safe_operation(self):
        mgr = AutonomyManager()
        assert mgr.is_safe_operation(OperationType.READ) is True
        assert mgr.is_safe_operation(OperationType.ANALYZE) is True
        assert mgr.is_safe_operation(OperationType.PUBLISH) is False
        assert mgr.is_safe_operation(OperationType.DELETE) is False


class TestModelSelector:
    def test_select_simple_prefers_local(self):
        selector = ModelSelector()
        result = selector.select(TaskComplexity.SIMPLE, {"ollama", "gemini"})
        assert result.provider == "ollama"

    def test_select_complex_with_cloud(self):
        selector = ModelSelector()
        result = selector.select(TaskComplexity.COMPLEX, {"ollama", "gemini"}, prefer_local=False)
        assert result.provider == "gemini"

    def test_select_code_task(self):
        selector = ModelSelector()
        result = selector.select(TaskComplexity.CODE, {"ollama"})
        assert "code" in result.model_id.lower() or result.provider == "ollama"

    def test_select_only_local(self):
        selector = ModelSelector()
        result = selector.select(TaskComplexity.COMPLEX, {"ollama"})
        assert result.provider == "ollama"

    def test_select_fallback(self):
        selector = ModelSelector(profiles=[])
        result = selector.select(TaskComplexity.SIMPLE, {"ollama"})
        assert result.model_id == "qwen2.5:7b"  # Default fallback

    def test_list_profiles(self):
        selector = ModelSelector()
        profiles = selector.list_profiles()
        assert len(profiles) >= 4

    def test_get_profile(self):
        selector = ModelSelector()
        p = selector.get_profile("qwen2.5:7b")
        assert p is not None
        assert p.provider == "ollama"

    def test_custom_profile(self):
        custom = ModelProfile(
            id="custom:3b", provider="ollama", name="Custom",
            recommended_for=["simple"],
        )
        selector = ModelSelector(profiles=[custom])
        result = selector.select(TaskComplexity.SIMPLE, {"ollama"})
        assert result.model_id == "custom:3b"
