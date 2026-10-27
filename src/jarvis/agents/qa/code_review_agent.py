"""CodeReviewAgent — análisis de código estático y revisión de calidad."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from jarvis.agents.base import AgentRequest, AgentResult, AgentSpec, BaseAgent


class FindingSeverity:
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory:
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    RELIABILITY = "reliability"
    CODE_SMELL = "code_smell"
    BEST_PRACTICE = "best_practice"
    COMPLEXITY = "complexity"


@dataclass
class CodeFinding:
    """Un hallazgo de revisión de código."""

    title: str
    category: str
    severity: str
    description: str
    recommendation: str
    file_pattern: str = ""
    line_ref: str = ""


# Patrones de detección estática (no requieren AST ni LLM)
_STATIC_PATTERNS: list[tuple[str, str, str, str, str]] = [
    # (regex, title, category, severity, recommendation)
    (
        r"(password|passwd|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
        "Credencial hardcodeada detectada",
        FindingCategory.SECURITY, FindingSeverity.CRITICAL,
        "Mover a variables de entorno o secrets manager",
    ),
    (
        r"eval\s*\(",
        "Uso de eval() detectado",
        FindingCategory.SECURITY, FindingSeverity.HIGH,
        "Reemplazar eval() por alternativas seguras",
    ),
    (
        r"(exec|system|popen|subprocess\.call)\s*\(",
        "Ejecución de comandos del sistema",
        FindingCategory.SECURITY, FindingSeverity.HIGH,
        "Validar y sanitizar inputs antes de ejecutar comandos",
    ),
    (
        r"except\s*:",
        "Bare except sin tipo de excepción",
        FindingCategory.RELIABILITY, FindingSeverity.MEDIUM,
        "Especificar el tipo de excepción (ej: except ValueError)",
    ),
    (
        r"# ?(TODO|FIXME|HACK|XXX|TEMP)",
        "TODO/FIXME pendiente en código",
        FindingCategory.MAINTAINABILITY, FindingSeverity.LOW,
        "Resolver o crear ticket para tracking",
    ),
    (
        r"print\s*\(",
        "print() en código (posible debug residual)",
        FindingCategory.CODE_SMELL, FindingSeverity.LOW,
        "Reemplazar con logging apropiado",
    ),
    (
        r"import \*",
        "Import wildcard (import *)",
        FindingCategory.MAINTAINABILITY, FindingSeverity.MEDIUM,
        "Importar módulos/funciones específicos",
    ),
    (
        r"\.format\s*\(.*\)|%s|%d",
        "String formatting legacy (usar f-strings)",
        FindingCategory.BEST_PRACTICE, FindingSeverity.INFO,
        "Preferir f-strings para mejor legibilidad",
    ),
    (
        r"time\.sleep\s*\(\s*\d{2,}",
        "Sleep largo detectado (posible polling)",
        FindingCategory.PERFORMANCE, FindingSeverity.MEDIUM,
        "Considerar async/await, eventos o backoff exponencial",
    ),
    (
        r"SELECT\s+\*\s+FROM",
        "SELECT * detectado (anti-pattern SQL)",
        FindingCategory.PERFORMANCE, FindingSeverity.MEDIUM,
        "Especificar columnas explícitamente",
    ),
    (
        r"(?:password|token|secret).*(?:log|print|logger)",
        "Posible log de información sensible",
        FindingCategory.SECURITY, FindingSeverity.HIGH,
        "No loguear credenciales ni tokens",
    ),
    (
        r"(disable|skip|ignore).*(?:ssl|cert|verify)",
        "Verificación SSL/certificado deshabilitada",
        FindingCategory.SECURITY, FindingSeverity.HIGH,
        "Habilitar verificación SSL en producción",
    ),
]


class CodeReviewAgent(BaseAgent):
    """Agente de análisis estático y revisión de calidad de código."""

    def spec(self) -> AgentSpec:
        return AgentSpec(
            id="qa.code_review",
            name="Code Review Agent",
            description="Análisis estático de código: seguridad, code smells, complejidad, mejores prácticas",
            skills=["code_review", "code"],
            supported_projects=[],
        )

    def execute(self, request: AgentRequest) -> AgentResult:
        start = time.monotonic()
        try:
            question = request.payload.get("question", request.intent)
            code = request.payload.get("code", "")
            diff = request.payload.get("diff", "")

            # Si hay código o diff explícito, analizar eso
            content_to_analyze = code or diff or question

            if request.payload.get("action") == "help" or re.search(r"(ayuda|help)", question, re.I):
                return self._show_help(start)

            findings = self._analyze(content_to_analyze)
            content = self._render_findings(findings, content_to_analyze)

            return AgentResult(
                success=True,
                content=content,
                data={
                    "findings_count": len(findings),
                    "by_severity": self._count_by_field(findings, "severity"),
                    "by_category": self._count_by_field(findings, "category"),
                },
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    def _analyze(self, content: str) -> list[CodeFinding]:
        """Ejecutar análisis estático sobre el contenido."""
        findings = []
        lines = content.splitlines()

        for pattern, title, category, severity, recommendation in _STATIC_PATTERNS:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.I):
                    findings.append(CodeFinding(
                        title=title,
                        category=category,
                        severity=severity,
                        description=f"Línea {i}: `{line.strip()[:100]}`",
                        recommendation=recommendation,
                        line_ref=str(i),
                    ))

        # Análisis de complejidad
        complexity_findings = self._check_complexity(content, lines)
        findings.extend(complexity_findings)

        # Deduplicar por título + línea
        seen = set()
        unique = []
        for f in findings:
            key = (f.title, f.line_ref)
            if key not in seen:
                seen.add(key)
                unique.append(f)

        # Ordenar por severidad
        severity_order = {
            FindingSeverity.CRITICAL: 0,
            FindingSeverity.HIGH: 1,
            FindingSeverity.MEDIUM: 2,
            FindingSeverity.LOW: 3,
            FindingSeverity.INFO: 4,
        }
        unique.sort(key=lambda f: severity_order.get(f.severity, 5))

        return unique

    def _check_complexity(self, content: str, lines: list[str]) -> list[CodeFinding]:
        """Verificar indicadores de complejidad."""
        findings = []

        # Funciones muy largas
        func_start = None
        func_name = ""
        for i, line in enumerate(lines, 1):
            match = re.match(r"\s*(def|function|async def)\s+(\w+)", line)
            if match:
                if func_start and (i - func_start) > 50:
                    findings.append(CodeFinding(
                        title=f"Función larga: {func_name} ({i - func_start} líneas)",
                        category=FindingCategory.COMPLEXITY,
                        severity=FindingSeverity.MEDIUM,
                        description=f"La función `{func_name}` tiene más de 50 líneas",
                        recommendation="Considerar refactorizar en funciones más pequeñas",
                        line_ref=str(func_start),
                    ))
                func_start = i
                func_name = match.group(2)

        # Anidamiento profundo
        for i, line in enumerate(lines, 1):
            indent = len(line) - len(line.lstrip())
            spaces_per_level = 4
            depth = indent // spaces_per_level if spaces_per_level else 0
            if depth >= 5 and line.strip():
                findings.append(CodeFinding(
                    title=f"Anidamiento profundo (nivel {depth})",
                    category=FindingCategory.COMPLEXITY,
                    severity=FindingSeverity.MEDIUM,
                    description=f"Línea {i}: anidamiento nivel {depth}",
                    recommendation="Extraer lógica a funciones auxiliares o usar early returns",
                    line_ref=str(i),
                ))

        # Archivo muy largo
        if len(lines) > 500:
            findings.append(CodeFinding(
                title=f"Archivo largo ({len(lines)} líneas)",
                category=FindingCategory.MAINTAINABILITY,
                severity=FindingSeverity.LOW,
                description=f"El archivo tiene {len(lines)} líneas",
                recommendation="Considerar dividir en módulos más pequeños",
            ))

        return findings

    def _render_findings(self, findings: list[CodeFinding], analyzed_content: str) -> str:
        """Renderizar hallazgos como markdown."""
        if not findings:
            lines_count = len(analyzed_content.splitlines())
            return (
                f"## Code Review — Sin hallazgos\n\n"
                f"Análisis de {lines_count} líneas completado. No se detectaron problemas.\n"
            )

        lines = [f"## Code Review — {len(findings)} hallazgos\n"]

        # Resumen
        by_severity = self._count_by_field(findings, "severity")
        severity_parts = []
        for sev in ("critical", "high", "medium", "low", "info"):
            count = by_severity.get(sev, 0)
            if count:
                severity_parts.append(f"{sev}: {count}")
        lines.append("**Resumen:** " + " | ".join(severity_parts) + "\n")

        # Tabla
        lines.append("| # | Severidad | Categoría | Hallazgo | Línea |")
        lines.append("|---|-----------|-----------|----------|-------|")

        for i, f in enumerate(findings, 1):
            sev_icon = _SEVERITY_ICONS.get(f.severity, "")
            lines.append(
                f"| {i} | {sev_icon} {f.severity} | {f.category} | {f.title} | {f.line_ref or '—'} |"
            )

        # Detalle
        lines.append("\n### Detalle\n")
        for i, f in enumerate(findings, 1):
            lines.append(f"**{i}. {f.title}**")
            lines.append(f"- {f.description}")
            lines.append(f"- Recomendación: {f.recommendation}\n")

        return "\n".join(lines)

    def _count_by_field(self, findings: list[CodeFinding], field_name: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in findings:
            val = getattr(f, field_name, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts

    def _show_help(self, start: float) -> AgentResult:
        content = (
            "**Code Review Agent — Análisis estático**\n\n"
            "Analiza código buscando:\n"
            "- Vulnerabilidades de seguridad (credenciales, eval, SQL injection)\n"
            "- Code smells (print residual, import *, bare except)\n"
            "- Complejidad (funciones largas, anidamiento profundo)\n"
            "- Mejores prácticas (f-strings, logging, SSL)\n\n"
            "Uso:\n"
            "- `jarvis run 'revisa este código: [pegar código]'`\n"
            "- `jarvis run 'code review del diff: [pegar diff]'`\n"
            "- Pasa código en `payload.code` o `payload.diff` para análisis directo\n"
        )
        return AgentResult(
            success=True,
            content=content,
            duration_ms=int((time.monotonic() - start) * 1000),
        )


_SEVERITY_ICONS: dict[str, str] = {
    FindingSeverity.CRITICAL: "!!",
    FindingSeverity.HIGH: "!",
    FindingSeverity.MEDIUM: "~",
    FindingSeverity.LOW: "-",
    FindingSeverity.INFO: "i",
}
