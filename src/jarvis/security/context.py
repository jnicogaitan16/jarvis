"""Security Gate — verificación de permisos y sanitización."""

from __future__ import annotations

import re

from jarvis.core.models import ProjectContext

_CREDENTIAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(api[_-]?key|token|password|secret|pat)\s*[=:]\s*\S+"),
    re.compile(r"sk-ant-[a-zA-Z0-9-]+"),
    re.compile(r"AI[a-zA-Z0-9_-]{30,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"gho_[a-zA-Z0-9]{36}"),
    re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b"),  # RUT chileno
]

_REDACTED = "[REDACTED]"


class SecurityGate:
    """Verifica permisos y sanitiza información sensible."""

    def check_tool_access(self, tool_id: str, context: ProjectContext) -> bool:
        """Verificar si una herramienta está autorizada para el proyecto."""
        if not context.allowed_tools:
            return True  # Sin restricciones explícitas = todo permitido
        return tool_id in context.allowed_tools

    def check_provider_access(self, provider: str, context: ProjectContext) -> bool:
        """Verificar si un proveedor LLM está autorizado."""
        return provider in context.allowed_providers

    def check_memory_access(
        self, target_project: str, context: ProjectContext
    ) -> bool:
        """Verificar acceso a memoria de otro proyecto."""
        if target_project == context.memory_namespace:
            return True
        if target_project == "system":
            return True
        return False

    def sanitize_for_logging(self, text: str) -> str:
        """Redactar credenciales y datos sensibles antes de logging."""
        result = text
        for pattern in _CREDENTIAL_PATTERNS:
            result = pattern.sub(_REDACTED, result)
        return result

    def sanitize_for_cloud(
        self, text: str, context: ProjectContext
    ) -> str:
        """Redactar datos sensibles según la política del proyecto antes de enviar a cloud."""
        result = self.sanitize_for_logging(text)
        for pattern_str in context.sensitive_patterns:
            result = re.sub(pattern_str, _REDACTED, result, flags=re.IGNORECASE)
        return result
