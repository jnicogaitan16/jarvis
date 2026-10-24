"""Tests para Tool Registry y BaseTool."""

import pytest

from jarvis.core.models import ProjectContext, ToolAction
from jarvis.tools.base import BaseTool, ToolSpec
from jarvis.tools.registry import ToolRegistry


class EchoTool(BaseTool):
    def spec(self) -> ToolSpec:
        return ToolSpec(id="test.echo", name="Echo Tool", description="Echoes input")

    def _run(self, action, context):
        return {"echo": action.parameters.get("text", "")}


class FailTool(BaseTool):
    def spec(self) -> ToolSpec:
        return ToolSpec(id="test.fail", name="Fail Tool", description="Always fails")

    def _run(self, action, context):
        raise ValueError("Intentional failure")


class RestrictedTool(BaseTool):
    def spec(self) -> ToolSpec:
        return ToolSpec(
            id="test.restricted", name="Restricted",
            description="Only for PIE",
            allowed_projects=["integratepie"],
        )

    def _run(self, action, context):
        return {"status": "ok"}


def _ctx(project_id="personal"):
    return ProjectContext(project_id=project_id, display_name=project_id)


class TestBaseTool:
    def test_execute_success(self):
        tool = EchoTool()
        action = ToolAction(tool_id="test.echo", parameters={"text": "hello"})
        obs = tool.execute(action, _ctx())
        assert obs.success is True
        assert obs.result["echo"] == "hello"
        assert obs.duration_ms >= 0

    def test_execute_failure(self):
        tool = FailTool()
        action = ToolAction(tool_id="test.fail")
        obs = tool.execute(action, _ctx())
        assert obs.success is False
        assert "Intentional failure" in obs.error

    def test_tool_id(self):
        assert EchoTool().tool_id == "test.echo"


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        assert reg.get("test.echo") is not None
        assert reg.get("nope") is None

    def test_list_all(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        reg.register(FailTool())
        specs = reg.list_all()
        assert len(specs) == 2

    def test_list_for_project(self):
        reg = ToolRegistry()
        reg.register(EchoTool())         # all projects
        reg.register(RestrictedTool())   # only integratepie

        all_tools = reg.list_for_project("personal")
        assert len(all_tools) == 1  # only echo

        pie_tools = reg.list_for_project("integratepie")
        assert len(pie_tools) == 2  # echo + restricted

    def test_execute_tool(self):
        reg = ToolRegistry()
        reg.register(EchoTool())
        action = ToolAction(tool_id="test.echo", parameters={"text": "hi"})
        obs = reg.execute("test.echo", action, _ctx())
        assert obs.success is True

    def test_execute_not_found(self):
        reg = ToolRegistry()
        action = ToolAction(tool_id="nope")
        obs = reg.execute("nope", action, _ctx())
        assert obs.success is False
        assert "no encontrada" in obs.error

    def test_execute_unauthorized_project(self):
        reg = ToolRegistry()
        reg.register(RestrictedTool())
        action = ToolAction(tool_id="test.restricted")
        obs = reg.execute("test.restricted", action, _ctx("personal"))
        assert obs.success is False
        assert "no autorizada" in obs.error

    def test_count(self):
        reg = ToolRegistry()
        assert reg.count == 0
        reg.register(EchoTool())
        assert reg.count == 1
