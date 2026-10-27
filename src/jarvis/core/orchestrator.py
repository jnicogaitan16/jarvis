"""Orchestrator — enruta solicitudes a agentes por reglas deterministas."""

from __future__ import annotations

import re
import time

from jarvis.agents.base import AgentRequest, AgentResult, BaseAgent
from jarvis.agents.registry import AgentRegistry
from jarvis.core.events import EventStore
from jarvis.core.models import EventType
from jarvis.memory.manager import MemoryManager

# Patrones para detección de intención
_INTENT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("analyze_pr", re.compile(r"(analiz|review|revis).*(pr|pull.?request|merge)", re.I)),
    ("gherkin", re.compile(r"(gherkin|bdd|scenario|escenario.*prueba|feature.*test)", re.I)),
    ("write", re.compile(r"(escrib|redact|bug.?report|notific|comentario|report.*bug)", re.I)),
    ("test_strategy", re.compile(r"(estrategia.*test|plan.*prueba|automa.*test|vale.*pena.*autom|conviene.*autom)", re.I)),
    ("code_review", re.compile(r"(code.?review|revis.*código|análisis.*estático|static.*analy|code.?smell)", re.I)),
    ("qa", re.compile(r"(test|prueba|qa|quality|calidad|caso.?de.?prueba)", re.I)),
    ("code", re.compile(r"(código|code|función|class|bug|debug|refactor)", re.I)),
    ("memory", re.compile(r"(recuerd|memori|qué sab|what.*know|histori)", re.I)),
    ("status", re.compile(r"(status|estado|cómo va|health)", re.I)),
    ("help", re.compile(r"(ayuda|help|qué puedes|capacidad)", re.I)),
]


def detect_intent(text: str) -> str:
    """Detectar intención de la solicitud por regex."""
    for intent, pattern in _INTENT_PATTERNS:
        if pattern.search(text):
            return intent
    return "general"


class Orchestrator:
    """Coordina la ejecución de agentes según la solicitud."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        event_store: EventStore | None = None,
        memory_manager: MemoryManager | None = None,
    ):
        self._agents = agent_registry
        self._events = event_store
        self._memory = memory_manager

    def route(self, request: AgentRequest) -> AgentResult:
        """Enrutar solicitud al agente apropiado y ejecutar."""
        start = time.monotonic()

        intent = detect_intent(request.intent or request.payload.get("question", ""))
        request.intent = intent

        # Inyectar contexto de memoria
        if self._memory and not request.memory_context:
            query = request.payload.get("question", request.intent)
            request.memory_context = self._memory.get_context_for_prompt(
                query, project=request.project
            )

        # Buscar agente capaz
        agent = self._find_agent(intent, request.project)
        if not agent:
            elapsed = int((time.monotonic() - start) * 1000)
            return AgentResult(
                request_id=request.id,
                success=False,
                error=f"Sin agente disponible para intent='{intent}' en proyecto='{request.project}'",
                duration_ms=elapsed,
            )

        # Emitir evento de inicio
        if self._events:
            self._events.emit(
                EventType.ACTION,
                payload={
                    "orchestrator": "route",
                    "intent": intent,
                    "agent": agent.agent_id,
                    "project": request.project,
                },
                agent_id="core.orchestrator",
                project=request.project,
            )

        # Ejecutar
        result = agent.execute(request)
        result.request_id = request.id
        result.agent_id = agent.agent_id
        result.duration_ms = int((time.monotonic() - start) * 1000)

        # Emitir evento de resultado
        if self._events:
            self._events.emit(
                EventType.OBSERVATION,
                payload={
                    "orchestrator": "result",
                    "agent": agent.agent_id,
                    "success": result.success,
                    "duration_ms": result.duration_ms,
                },
                agent_id="core.orchestrator",
                project=request.project,
            )

        return result

    def _find_agent(self, intent: str, project: str) -> BaseAgent | None:
        """Buscar agente por intent y proyecto.

        Prioridad: match específico de skill > skill 'general' > fallback.
        """
        candidates = self._agents.find_for_project(project)
        if not candidates:
            return None

        # 1. Match exacto de intent en skills
        for agent in candidates:
            if intent in agent.spec().skills and intent != "general":
                return agent

        # 2. Agente con skill "general"
        for agent in candidates:
            if "general" in agent.spec().skills:
                return agent

        # 3. Fallback: primer agente disponible
        return candidates[0]
