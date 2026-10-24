"""Agent Registry — registro dinámico de agentes."""

from __future__ import annotations

from jarvis.agents.base import AgentSpec, BaseAgent


class AgentRegistry:
    """Registro central de agentes disponibles."""

    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Registrar un agente."""
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> BaseAgent | None:
        """Obtener un agente por ID."""
        return self._agents.get(agent_id)

    def list_all(self) -> list[AgentSpec]:
        """Listar especificaciones de todos los agentes registrados."""
        return [a.spec() for a in self._agents.values()]

    def find_for_project(self, project: str) -> list[BaseAgent]:
        """Encontrar agentes que soportan un proyecto."""
        return [
            a for a in self._agents.values()
            if not a.spec().supported_projects or project in a.spec().supported_projects
        ]

    def find_by_intent(self, intent: str, project: str) -> BaseAgent | None:
        """Encontrar el primer agente capaz de manejar la solicitud."""
        for agent in self._agents.values():
            if agent.can_handle(intent, project):
                return agent
        return None

    @property
    def count(self) -> int:
        return len(self._agents)
