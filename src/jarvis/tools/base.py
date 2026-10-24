"""Tool Protocol — contrato base para herramientas de JARVIS."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from jarvis.core.models import ProjectContext, ToolAction, ToolObservation


@dataclass(frozen=True)
class ToolSpec:
    """Especificación declarativa de una herramienta."""
    id: str
    name: str
    description: str
    has_side_effects: bool = False
    requires_approval: bool = False
    allowed_projects: list[str] = field(default_factory=list)  # vacío = todos


class BaseTool(ABC):
    """Clase base para herramientas deterministas."""

    @abstractmethod
    def spec(self) -> ToolSpec:
        """Retornar la especificación de la herramienta."""
        ...

    @abstractmethod
    def _run(self, action: ToolAction, context: ProjectContext) -> dict:
        """Implementación de la herramienta. Retorna dict con resultados."""
        ...

    @property
    def tool_id(self) -> str:
        return self.spec().id

    def execute(self, action: ToolAction, context: ProjectContext) -> ToolObservation:
        """Ejecutar la herramienta con timing y manejo de errores."""
        start = time.monotonic()
        try:
            result = self._run(action, context)
            elapsed = int((time.monotonic() - start) * 1000)
            return ToolObservation(
                tool_id=self.tool_id,
                success=True,
                result=result,
                duration_ms=elapsed,
                correlation_id=action.correlation_id,
            )
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return ToolObservation(
                tool_id=self.tool_id,
                success=False,
                error=str(e),
                duration_ms=elapsed,
                correlation_id=action.correlation_id,
            )
