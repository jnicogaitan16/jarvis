"""Modelos del sistema de pipelines multi-agente."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class StepStatus(StrEnum):
    """Estado de un paso del pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class PipelineStep:
    """Definición de un paso en el pipeline."""

    agent_id: str
    name: str
    description: str = ""
    input_map: dict[str, str] = field(default_factory=dict)
    stop_on_fail: bool = True


@dataclass(frozen=True)
class PipelineDef:
    """Definición de un pipeline multi-agente."""

    id: str
    name: str
    description: str
    steps: list[PipelineStep]
    tags: list[str] = field(default_factory=list)


@dataclass
class StepResult:
    """Resultado de un paso ejecutado."""

    step_name: str
    agent_id: str
    status: StepStatus
    content: str = ""
    data: dict = field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0


@dataclass
class PipelineResult:
    """Resultado completo de la ejecución de un pipeline."""

    pipeline_id: str
    pipeline_name: str
    success: bool
    steps: list[StepResult] = field(default_factory=list)
    total_duration_ms: int = 0
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)

    @property
    def failed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.FAILED)

    def summary(self) -> str:
        """Generar resumen markdown del pipeline."""
        lines = [
            f"## Pipeline: {self.pipeline_name}",
            f"**Estado:** {'Exitoso' if self.success else 'Fallido'} "
            f"| **Pasos:** {self.completed_steps}/{len(self.steps)} "
            f"| **Duración:** {self.total_duration_ms}ms\n",
        ]

        for i, step in enumerate(self.steps, 1):
            if step.status == StepStatus.COMPLETED:
                icon = "[OK]"
            elif step.status == StepStatus.FAILED:
                icon = "[FAIL]"
            elif step.status == StepStatus.SKIPPED:
                icon = "[SKIP]"
            else:
                icon = "[?]"

            lines.append(f"### {i}. {icon} {step.step_name} ({step.agent_id})")
            if step.content:
                # Mostrar primeras líneas del contenido
                preview = "\n".join(step.content.splitlines()[:15])
                lines.append(preview)
            if step.error:
                lines.append(f"\n**Error:** {step.error}")
            lines.append(f"\n_({step.duration_ms}ms)_\n")

        return "\n".join(lines)
