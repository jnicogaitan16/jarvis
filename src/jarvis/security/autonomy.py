"""Autonomy Framework — políticas de aprobación y niveles de autonomía.

Niveles:
  0 - Consulta: solo responde y analiza
  1 - Propuesta: genera planes y recomendaciones
  2 - Ejecución controlada: ejecuta herramientas seguras
  3 - Coordinación: coordina acciones, pide aprobación cuando corresponde
  4 - Delegada: ejecuta tareas recurrentes dentro de límites
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from jarvis.core.models import OperationType, ProjectContext


class AutonomyLevel(IntEnum):
    CONSULT = 0
    PROPOSE = 1
    EXECUTE = 2
    COORDINATE = 3
    DELEGATE = 4


@dataclass(frozen=True)
class ApprovalPolicy:
    """Política de aprobación para una operación."""
    operation: OperationType
    min_autonomy_level: int
    requires_human_approval: bool
    description: str = ""


# Políticas por defecto
DEFAULT_POLICIES: list[ApprovalPolicy] = [
    ApprovalPolicy(OperationType.READ, 0, False, "Lectura siempre permitida"),
    ApprovalPolicy(OperationType.ANALYZE, 0, False, "Análisis siempre permitido"),
    ApprovalPolicy(OperationType.PROPOSE, 1, False, "Propuestas desde nivel 1"),
    ApprovalPolicy(OperationType.EXECUTE, 2, False, "Ejecución local desde nivel 2"),
    ApprovalPolicy(OperationType.MODIFY, 3, True, "Modificaciones requieren aprobación"),
    ApprovalPolicy(OperationType.PUBLISH, 3, True, "Publicaciones siempre requieren aprobación"),
    ApprovalPolicy(OperationType.DELETE, 3, True, "Eliminaciones siempre requieren aprobación"),
]


@dataclass
class ApprovalRequest:
    """Solicitud de aprobación pendiente."""
    id: str
    operation: OperationType
    agent_id: str
    project: str
    description: str
    details: dict = field(default_factory=dict)
    status: str = "pending"  # pending, approved, rejected


@dataclass
class ApprovalResult:
    approved: bool
    reason: str = ""


class AutonomyManager:
    """Gestiona niveles de autonomía y aprobaciones."""

    def __init__(self, policies: list[ApprovalPolicy] | None = None):
        self._policies = {p.operation: p for p in (policies or DEFAULT_POLICIES)}
        self._pending: dict[str, ApprovalRequest] = {}
        self._history: list[ApprovalRequest] = []

    def check_permission(
        self,
        operation: OperationType,
        context: ProjectContext,
    ) -> ApprovalResult:
        """Verificar si una operación está permitida dado el nivel de autonomía."""
        policy = self._policies.get(operation)
        if not policy:
            return ApprovalResult(approved=False, reason=f"Sin política para {operation}")

        if context.autonomy_level < policy.min_autonomy_level:
            return ApprovalResult(
                approved=False,
                reason=f"Nivel de autonomía insuficiente: {context.autonomy_level} < {policy.min_autonomy_level}",
            )

        if policy.requires_human_approval:
            return ApprovalResult(
                approved=False,
                reason=f"Operación {operation} requiere aprobación humana",
            )

        return ApprovalResult(approved=True)

    def request_approval(
        self,
        operation: OperationType,
        agent_id: str,
        project: str,
        description: str,
        details: dict | None = None,
    ) -> ApprovalRequest:
        """Crear una solicitud de aprobación."""
        from jarvis.core.models import _new_id

        req = ApprovalRequest(
            id=_new_id(),
            operation=operation,
            agent_id=agent_id,
            project=project,
            description=description,
            details=details or {},
        )
        self._pending[req.id] = req
        return req

    def approve(self, request_id: str) -> bool:
        """Aprobar una solicitud pendiente."""
        req = self._pending.pop(request_id, None)
        if not req:
            return False
        req.status = "approved"
        self._history.append(req)
        return True

    def reject(self, request_id: str, reason: str = "") -> bool:
        """Rechazar una solicitud pendiente."""
        req = self._pending.pop(request_id, None)
        if not req:
            return False
        req.status = "rejected"
        self._history.append(req)
        return True

    def list_pending(self) -> list[ApprovalRequest]:
        return list(self._pending.values())

    def list_history(self, limit: int = 20) -> list[ApprovalRequest]:
        return self._history[-limit:]

    def is_safe_operation(self, operation: OperationType) -> bool:
        """Verificar si una operación es segura (no requiere aprobación en ningún nivel)."""
        policy = self._policies.get(operation)
        return policy is not None and not policy.requires_human_approval
