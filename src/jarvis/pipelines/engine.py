"""PipelineEngine — ejecuta pipelines multi-agente con paso de contexto."""

from __future__ import annotations

import logging
import time

from jarvis.agents.base import AgentRequest
from jarvis.agents.registry import AgentRegistry
from jarvis.pipelines.models import (
    PipelineDef,
    PipelineResult,
    PipelineStep,
    StepResult,
    StepStatus,
)

log = logging.getLogger(__name__)


class PipelineEngine:
    """Ejecuta pipelines multi-agente secuenciales con contexto compartido."""

    def __init__(self, agent_registry: AgentRegistry) -> None:
        self._agents = agent_registry

    def execute(
        self,
        pipeline: PipelineDef,
        initial_input: str,
        project: str = "personal",
    ) -> PipelineResult:
        """Ejecutar un pipeline completo."""
        start = time.monotonic()
        result = PipelineResult(
            pipeline_id=pipeline.id,
            pipeline_name=pipeline.name,
            success=True,
        )

        # Contexto compartido entre steps
        context: dict[str, object] = {
            "input": initial_input,
            "project": project,
        }

        log.info("Pipeline '%s' iniciado con %d pasos", pipeline.name, len(pipeline.steps))

        for i, step in enumerate(pipeline.steps):
            step_result = self._execute_step(step, context, project, i + 1, len(pipeline.steps))
            result.steps.append(step_result)

            if step_result.status == StepStatus.COMPLETED:
                # Alimentar el contexto con resultados de este step
                context[f"step_{i + 1}_content"] = step_result.content
                context[f"step_{i + 1}_data"] = step_result.data
                context[step.agent_id] = step_result.content
            elif step_result.status == StepStatus.FAILED and step.stop_on_fail:
                result.success = False
                # Marcar steps restantes como skipped
                for remaining in pipeline.steps[i + 1:]:
                    result.steps.append(StepResult(
                        step_name=remaining.name,
                        agent_id=remaining.agent_id,
                        status=StepStatus.SKIPPED,
                    ))
                break

        result.total_duration_ms = int((time.monotonic() - start) * 1000)
        log.info(
            "Pipeline '%s' finalizado: %s (%d/%d pasos, %dms)",
            pipeline.name,
            "OK" if result.success else "FAIL",
            result.completed_steps,
            len(result.steps),
            result.total_duration_ms,
        )
        return result

    def _execute_step(
        self,
        step: PipelineStep,
        context: dict[str, object],
        project: str,
        step_num: int,
        total_steps: int,
    ) -> StepResult:
        """Ejecutar un paso individual del pipeline."""
        start = time.monotonic()
        log.info("  [%d/%d] Ejecutando %s (%s)", step_num, total_steps, step.name, step.agent_id)

        # Buscar agente
        agent = self._agents.get(step.agent_id)
        if not agent:
            return StepResult(
                step_name=step.name,
                agent_id=step.agent_id,
                status=StepStatus.FAILED,
                error=f"Agente '{step.agent_id}' no encontrado",
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        # Construir payload para este step
        payload = self._build_payload(step, context)

        request = AgentRequest(
            intent=step.agent_id.split(".")[-1],
            payload=payload,
            project=project,
        )

        try:
            agent_result = agent.execute(request)
            elapsed = int((time.monotonic() - start) * 1000)

            if agent_result.success:
                return StepResult(
                    step_name=step.name,
                    agent_id=step.agent_id,
                    status=StepStatus.COMPLETED,
                    content=agent_result.content,
                    data=agent_result.data,
                    duration_ms=elapsed,
                )
            else:
                return StepResult(
                    step_name=step.name,
                    agent_id=step.agent_id,
                    status=StepStatus.FAILED,
                    error=agent_result.error,
                    duration_ms=elapsed,
                )

        except Exception as e:
            return StepResult(
                step_name=step.name,
                agent_id=step.agent_id,
                status=StepStatus.FAILED,
                error=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    def _build_payload(self, step: PipelineStep, context: dict[str, object]) -> dict:
        """Construir payload mapeando datos del contexto compartido."""
        payload: dict[str, object] = {}

        # Siempre pasar el input original como question
        payload["question"] = str(context.get("input", ""))

        # Aplicar input_map: mapea campos del contexto a campos del payload
        for payload_key, context_key in step.input_map.items():
            value = context.get(context_key)
            if value is not None:
                payload[payload_key] = value

        # Enriquecer question con contexto de steps previos
        previous_contents = []
        for key, value in context.items():
            if key.startswith("step_") and key.endswith("_content") and isinstance(value, str):
                previous_contents.append(value)

        if previous_contents:
            payload["previous_context"] = "\n\n---\n\n".join(previous_contents)

        return payload
