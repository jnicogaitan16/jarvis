"""Echo Agent — agente de prueba que demuestra el flujo completo."""

from __future__ import annotations

from jarvis.agents.base import AgentRequest, AgentResult, AgentSpec, BaseAgent


class EchoAgent(BaseAgent):
    """Agente de prueba que repite la solicitud con metadata del sistema."""

    def spec(self) -> AgentSpec:
        return AgentSpec(
            id="core.echo",
            name="Echo Agent",
            description="Agente de prueba que repite la solicitud con información del sistema",
            skills=["general", "help", "status"],
        )

    def execute(self, request: AgentRequest) -> AgentResult:
        question = request.payload.get("question", request.intent)
        lines = [
            f"Echo desde {self.name}:",
            f"  Intent: {request.intent}",
            f"  Proyecto: {request.project}",
            f"  Pregunta: {question}",
        ]
        if request.memory_context:
            lines.append(f"  Memoria: {len(request.memory_context)} chars de contexto")

        return AgentResult(
            success=True,
            content="\n".join(lines),
            data={"intent": request.intent, "project": request.project},
        )
