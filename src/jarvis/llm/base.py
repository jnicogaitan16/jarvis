"""LLM Provider Protocol — contrato base para todos los proveedores."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable


class TaskComplexity(StrEnum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    CODE = "code"


@dataclass(frozen=True)
class LLMRequest:
    """Solicitud a un proveedor LLM."""
    prompt: str
    system: str = ""
    max_tokens: int = 2048
    temperature: float = 0.7
    project: str = "personal"


@dataclass(frozen=True)
class LLMResponse:
    """Respuesta de un proveedor LLM."""
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderStatus:
    """Estado de un proveedor."""
    provider: str
    available: bool
    model: str = ""
    error: str = ""


@runtime_checkable
class LLMProvider(Protocol):
    """Contrato que todo proveedor LLM debe cumplir."""

    @property
    def provider_id(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def is_available(self) -> bool:
        """Verificar si el proveedor está accesible."""
        ...

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generar respuesta. Lanza RuntimeError si falla."""
        ...

    def status(self) -> ProviderStatus:
        """Obtener estado del proveedor."""
        ...
