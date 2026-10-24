"""Agent Protocol — contrato base para todos los agentes de JARVIS."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from jarvis.core.models import ProjectContext, _new_id


@dataclass(frozen=True)
class AgentSpec:
    """Especificación declarativa de un agente."""
    id: str
    name: str
    description: str
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    supported_projects: list[str] = field(default_factory=list)  # vacío = todos
    autonomy_level: int = 0


@dataclass
class AgentRequest:
    """Solicitud para un agente."""
    id: str = field(default_factory=_new_id)
    intent: str = ""
    payload: dict = field(default_factory=dict)
    project: str = "personal"
    context: ProjectContext | None = None
    memory_context: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentResult:
    """Resultado de ejecución de un agente."""
    request_id: str = ""
    agent_id: str = ""
    success: bool = True
    content: str = ""
    data: dict = field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0
    evidence: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Clase base que todo agente de JARVIS debe extender."""

    @abstractmethod
    def spec(self) -> AgentSpec:
        """Retornar la especificación del agente."""
        ...

    @abstractmethod
    def execute(self, request: AgentRequest) -> AgentResult:
        """Ejecutar una solicitud. Debe ser idempotente cuando sea posible."""
        ...

    @property
    def agent_id(self) -> str:
        return self.spec().id

    @property
    def name(self) -> str:
        return self.spec().name

    def can_handle(self, intent: str, project: str) -> bool:
        """Verificar si este agente puede manejar la solicitud."""
        s = self.spec()
        if s.supported_projects and project not in s.supported_projects:
            return False
        return True
