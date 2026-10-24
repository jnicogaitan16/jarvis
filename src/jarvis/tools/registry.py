"""Tool Registry — registro dinámico de herramientas."""

from __future__ import annotations

from jarvis.core.models import ProjectContext, ToolAction, ToolObservation
from jarvis.tools.base import BaseTool, ToolSpec


class ToolRegistry:
    """Registro central de herramientas disponibles."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registrar una herramienta."""
        self._tools[tool.tool_id] = tool

    def get(self, tool_id: str) -> BaseTool | None:
        """Obtener una herramienta por ID."""
        return self._tools.get(tool_id)

    def list_all(self) -> list[ToolSpec]:
        """Listar especificaciones de todas las herramientas."""
        return [t.spec() for t in self._tools.values()]

    def list_for_project(self, project: str) -> list[ToolSpec]:
        """Listar herramientas disponibles para un proyecto."""
        result = []
        for tool in self._tools.values():
            s = tool.spec()
            if not s.allowed_projects or project in s.allowed_projects:
                result.append(s)
        return result

    def execute(
        self, tool_id: str, action: ToolAction, context: ProjectContext
    ) -> ToolObservation:
        """Ejecutar una herramienta por ID."""
        tool = self._tools.get(tool_id)
        if not tool:
            return ToolObservation(
                tool_id=tool_id,
                success=False,
                error=f"Herramienta '{tool_id}' no encontrada",
                correlation_id=action.correlation_id,
            )

        spec = tool.spec()
        if spec.allowed_projects and context.project_id not in spec.allowed_projects:
            return ToolObservation(
                tool_id=tool_id,
                success=False,
                error=f"Herramienta '{tool_id}' no autorizada para proyecto '{context.project_id}'",
                correlation_id=action.correlation_id,
            )

        return tool.execute(action, context)

    @property
    def count(self) -> int:
        return len(self._tools)
