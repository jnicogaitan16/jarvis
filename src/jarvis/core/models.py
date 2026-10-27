"""Modelos core de JARVIS — contratos Pydantic para todo el sistema."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EventType(StrEnum):
    ACTION = "action"
    OBSERVATION = "observation"
    SYSTEM = "system"
    ERROR = "error"


class JobStatus(StrEnum):
    CREATED = "created"
    PLANNED = "planned"
    PENDING_APPROVAL = "pending_approval"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class MemoryType(StrEnum):
    CONVERSATIONAL = "conversational"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROJECT = "project"
    EVIDENCE = "evidence"


class OperationType(StrEnum):
    READ = "read"
    ANALYZE = "analyze"
    PROPOSE = "propose"
    EXECUTE = "execute"
    MODIFY = "modify"
    PUBLISH = "publish"
    DELETE = "delete"


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(UTC)


class Event(BaseModel):
    """Evento inmutable del event stream."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=_new_id)
    timestamp: datetime = Field(default_factory=_now)
    event_type: EventType
    agent_id: str | None = None
    project: str | None = None
    payload: dict = Field(default_factory=dict)
    parent_event_id: str | None = None


class ProjectContext(BaseModel):
    """Contexto de proyecto — define permisos y políticas."""
    model_config = ConfigDict(frozen=True)

    project_id: str
    display_name: str
    allowed_tools: frozenset[str] = frozenset()
    allowed_providers: frozenset[str] = frozenset({"ollama"})
    allow_cloud: bool = False
    allow_pii_to_cloud: bool = False
    sensitive_patterns: frozenset[str] = frozenset()
    autonomy_level: int = 0
    memory_namespace: str = ""

    def __init__(self, **data):
        if "memory_namespace" not in data or not data["memory_namespace"]:
            data["memory_namespace"] = data.get("project_id", "")
        super().__init__(**data)


class ToolAction(BaseModel):
    """Input tipado para una herramienta."""
    model_config = ConfigDict(frozen=True)

    tool_id: str
    parameters: dict = Field(default_factory=dict)
    project: str | None = None
    correlation_id: str = Field(default_factory=_new_id)


class ToolObservation(BaseModel):
    """Output tipado de una herramienta."""
    model_config = ConfigDict(frozen=True)

    tool_id: str
    success: bool
    result: dict = Field(default_factory=dict)
    error: str | None = None
    duration_ms: int = 0
    correlation_id: str = ""


class MemoryRecord(BaseModel):
    """Registro de memoria persistente."""

    id: str = Field(default_factory=_new_id)
    project: str
    memory_type: MemoryType
    source: str
    content: str
    metadata: dict = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: str = "active"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    version: int = 1
    tags: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


class SystemStatus(BaseModel):
    """Estado actual del sistema."""

    version: str
    environment: str
    events_count: int = 0
    memory_records: int = 0
    uptime_info: str = ""
    providers_available: list[str] = Field(default_factory=list)
