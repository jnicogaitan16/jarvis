"""LLM Router — selecciona el proveedor adecuado según políticas y complejidad."""

from __future__ import annotations

import logging
import re

from jarvis.core.models import ProjectContext
from jarvis.llm.base import LLMProvider, LLMRequest, LLMResponse, ProviderStatus, TaskComplexity
from jarvis.llm.usage import UsageTracker
from jarvis.security.context import SecurityGate

logger = logging.getLogger(__name__)

# Providers que envían datos fuera de la red local
_CLOUD_PROVIDERS: frozenset[str] = frozenset({"gemini"})
# Providers que se ejecutan localmente
_LOCAL_PROVIDERS: frozenset[str] = frozenset({"ollama", "claude_code"})

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
        self._security_gate = SecurityGate()

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

        # 1. Para tareas simples, preferir local (rápido)
        if complexity == TaskComplexity.SIMPLE and "ollama" in allowed:
            ollama = self._providers.get("ollama")
            if ollama and ollama.is_available():
                return ollama

        # 2. Para tareas medio/complejas/código, preferir Claude Code si disponible
        if complexity in (TaskComplexity.MEDIUM, TaskComplexity.COMPLEX, TaskComplexity.CODE):
            claude = self._providers.get("claude_code")
            if claude and claude.is_available():
                return claude

        # 3. Fallback cloud: Gemini si permitido
        if complexity in (TaskComplexity.MEDIUM, TaskComplexity.COMPLEX) and context.allow_cloud:
            for pid in ("gemini",):
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

    def _sanitize_request(
        self,
        request: LLMRequest,
        provider_id: str,
        context: ProjectContext,
    ) -> LLMRequest:
        """Sanitizar prompt y system según el tipo de provider y políticas del proyecto.

        - Cloud providers (Gemini): aplica sanitize_for_cloud (más agresivo)
        - Local providers (Ollama, Claude Code): aplica sanitize_for_logging (menos agresivo)
        - Si allow_pii_to_cloud=True y el provider es cloud, solo sanitiza credenciales
        """
        is_cloud = provider_id in _CLOUD_PROVIDERS

        if is_cloud and not context.allow_pii_to_cloud:
            # Cloud + PII no permitido: sanitización completa
            sanitized_prompt = self._security_gate.sanitize_for_cloud(
                request.prompt, context,
            )
            sanitized_system = self._security_gate.sanitize_for_cloud(
                request.system, context,
            ) if request.system else ""
            level = "cloud"
        elif is_cloud:
            # Cloud + PII permitido: solo credenciales
            sanitized_prompt = self._security_gate.sanitize_for_logging(request.prompt)
            sanitized_system = self._security_gate.sanitize_for_logging(
                request.system,
            ) if request.system else ""
            level = "cloud-pii-allowed"
        else:
            # Local: solo credenciales
            sanitized_prompt = self._security_gate.sanitize_for_logging(request.prompt)
            sanitized_system = self._security_gate.sanitize_for_logging(
                request.system,
            ) if request.system else ""
            level = "local"

        # Log solo si hubo cambios (para auditoría)
        prompt_changed = sanitized_prompt != request.prompt
        system_changed = sanitized_system != request.system
        if prompt_changed or system_changed:
            fields = []
            if prompt_changed:
                fields.append("prompt")
            if system_changed:
                fields.append("system")
            logger.info(
                "SecurityGate sanitized [%s] for provider=%s project=%s level=%s",
                ", ".join(fields),
                provider_id,
                context.project_id,
                level,
            )

        # LLMRequest es frozen, crear nueva instancia con campos sanitizados
        return LLMRequest(
            prompt=sanitized_prompt,
            system=sanitized_system,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            project=request.project,
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
                # Sanitizar request según el provider y políticas del proyecto
                sanitized_request = self._sanitize_request(
                    request, provider.provider_id, context,
                )
                response = provider.generate(sanitized_request)
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
