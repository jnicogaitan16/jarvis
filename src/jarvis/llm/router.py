"""LLM Router — selecciona el proveedor adecuado según políticas y complejidad."""

from __future__ import annotations

import re

from jarvis.core.models import ProjectContext
from jarvis.llm.base import LLMProvider, LLMRequest, LLMResponse, ProviderStatus, TaskComplexity
from jarvis.llm.usage import UsageTracker


# Heurísticas simples para clasificar complejidad
_CODE_PATTERNS = re.compile(
    r"(código|code|función|function|bug|error|debug|refactor|test|class|def |import )",
    re.IGNORECASE,
)
_COMPLEX_PATTERNS = re.compile(
    r"(analiz|compar|diseñ|architect|explain why|por qué|evalúa|trade.?off|pros.?cons)",
    re.IGNORECASE,
)


def classify_complexity(text: str) -> TaskComplexity:
    """Clasificar la complejidad de una solicitud por heurísticas."""
    if _CODE_PATTERNS.search(text):
        return TaskComplexity.CODE
    if _COMPLEX_PATTERNS.search(text):
        return TaskComplexity.COMPLEX
    if len(text) > 500:
        return TaskComplexity.MEDIUM
    return TaskComplexity.SIMPLE


class LLMRouter:
    """Selecciona y ejecuta el proveedor LLM adecuado."""

    def __init__(
        self,
        providers: dict[str, LLMProvider] | None = None,
        usage_tracker: UsageTracker | None = None,
    ):
        self._providers: dict[str, LLMProvider] = providers or {}
        self._usage = usage_tracker

    def register(self, provider: LLMProvider) -> None:
        """Registrar un proveedor."""
        self._providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> LLMProvider | None:
        return self._providers.get(provider_id)

    def available_providers(self) -> list[ProviderStatus]:
        """Listar estado de todos los proveedores registrados."""
        return [p.status() for p in self._providers.values()]

    def select_provider(
        self,
        request: LLMRequest,
        context: ProjectContext,
    ) -> LLMProvider:
        """Seleccionar el mejor proveedor según políticas y complejidad."""
        allowed = context.allowed_providers
        complexity = classify_complexity(request.prompt)

        # 1. Para tareas simples o de código, preferir local
        if complexity in (TaskComplexity.SIMPLE, TaskComplexity.CODE):
            if "ollama" in allowed:
                ollama = self._providers.get("ollama")
                if ollama and ollama.is_available():
                    return ollama

        # 2. Para tareas medio/complejas, intentar cloud si permitido
        if complexity in (TaskComplexity.MEDIUM, TaskComplexity.COMPLEX):
            if context.allow_cloud:
                for pid in ("gemini",):  # Extensible a otros providers
                    if pid in allowed:
                        provider = self._providers.get(pid)
                        if provider and provider.is_available():
                            return provider

        # 3. Fallback: intentar cualquier provider disponible (respetando políticas)
        for pid, provider in self._providers.items():
            if pid in allowed and provider.is_available():
                return provider

        raise RuntimeError(
            f"Sin proveedores disponibles. Registrados: {list(self._providers.keys())}, "
            f"Permitidos: {list(allowed)}"
        )

    def generate(
        self,
        request: LLMRequest,
        context: ProjectContext,
    ) -> LLMResponse:
        """Seleccionar proveedor y generar respuesta con fallback y tracking."""
        allowed = context.allowed_providers
        tried: list[str] = []
        last_error: Exception | None = None

        # Obtener orden de preferencia
        primary = self.select_provider(request, context)
        candidates = [primary]
        # Agregar fallbacks
        for pid, provider in self._providers.items():
            if provider is not primary and pid in allowed:
                candidates.append(provider)

        for provider in candidates:
            if not provider.is_available():
                continue
            tried.append(provider.provider_id)
            try:
                response = provider.generate(request)
                if self._usage:
                    self._usage.record(
                        response,
                        project=request.project,
                        task_type=classify_complexity(request.prompt).value,
                    )
                return response
            except RuntimeError as e:
                last_error = e
                if self._usage:
                    self._usage.record_error(
                        provider.provider_id,
                        provider.model_name,
                        str(e),
                        project=request.project,
                    )
                continue

        error_msg = f"Todos los proveedores fallaron. Intentados: {tried}"
        if last_error:
            error_msg += f". Último error: {last_error}"
        raise RuntimeError(error_msg)
