"""WriterAgent — redacción profesional QA con comentarios estructurados."""

from __future__ import annotations

import re
import time

from jarvis.agents.base import AgentRequest, AgentResult, AgentSpec, BaseAgent
from jarvis.agents.qa.templates import (
    CommentType,
    list_templates,
    render_template,
)


class WriterAgent(BaseAgent):
    """Agente de redacción profesional para comunicación QA."""

    def spec(self) -> AgentSpec:
        return AgentSpec(
            id="qa.writer",
            name="QA Writer",
            description="Redacción profesional de comentarios QA: bugs, preguntas a DEV, notificaciones al equipo",
            skills=["write", "comment", "report"],
            supported_projects=[],
        )

    def execute(self, request: AgentRequest) -> AgentResult:
        start = time.monotonic()
        try:
            comment_type = self._detect_comment_type(request)
            question = request.payload.get("question", request.intent)

            if comment_type == "list":
                return self._list_templates(start)

            if comment_type == "help":
                return self._show_help(start)

            template_type = _COMMENT_TYPE_MAP.get(comment_type)
            if not template_type:
                return AgentResult(
                    success=True,
                    content=self._generate_general_comment(question),
                    data={"type": "general"},
                    duration_ms=int((time.monotonic() - start) * 1000),
                )

            # Extraer campos del texto del usuario
            fields = self._extract_fields(question, template_type)
            rendered = render_template(template_type, **fields)

            return AgentResult(
                success=True,
                content=rendered,
                data={"type": comment_type, "fields": fields},
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    def _detect_comment_type(self, request: AgentRequest) -> str:
        """Detectar qué tipo de comentario pide el usuario."""
        action = request.payload.get("action", "")
        if action:
            return action

        text = request.payload.get("question", request.intent).lower()

        for pattern, ctype in _DETECTION_PATTERNS:
            if re.search(pattern, text, re.I):
                return ctype

        return "general"

    def _extract_fields(self, text: str, comment_type: CommentType) -> dict:
        """Extraer campos del texto libre del usuario."""
        fields: dict[str, str] = {}

        if comment_type == CommentType.BUG_REPORT:
            fields["title"] = _extract_after(text, ("bug", "defecto", "error", "falla"))
            fields["summary"] = text
            fields["severity"] = _detect_severity(text)
            fields["priority"] = _detect_priority(text)
            fields["component"] = _extract_after(text, ("en", "componente", "módulo", "pantalla"))
            fields["environment"] = _detect_environment(text)
            fields["frequency"] = "Por determinar"
            fields["workaround"] = "No identificado"
            fields["reporter"] = "QA — JARVIS"

        elif comment_type == CommentType.DEV_QUESTION:
            fields["title"] = _extract_after(text, ("pregunta", "duda", "consulta", "por qué"))
            fields["context"] = text
            fields["question"] = text
            fields["urgency"] = "Normal"
            fields["context_area"] = "General"

        elif comment_type == CommentType.TEAM_NOTIFICATION:
            fields["title"] = _extract_after(text, ("notificar", "avisar", "comunicar", "informar"))
            fields["what_happened"] = text
            fields["status"] = "En investigación"
            fields["impact_level"] = "Por evaluar"

        elif comment_type == CommentType.REVIEW_FINDING:
            fields["title"] = _extract_after(text, ("hallazgo", "encontré", "detecté", "veo que"))
            fields["finding"] = text
            fields["finding_type"] = "Observación"
            fields["risk_level"] = "Medio"

        elif comment_type == CommentType.TEST_RESULT:
            fields["suite_name"] = _extract_after(text, ("suite", "prueba", "test", "resultado"))
            fields["observations"] = text

        from datetime import datetime, timezone
        fields["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        fields["execution_date"] = fields["date"]

        return fields

    def _list_templates(self, start: float) -> AgentResult:
        templates = list_templates()
        lines = ["**Templates de comentarios QA disponibles:**\n"]
        for tmpl in templates:
            sections = ", ".join(tmpl.sections)
            lines.append(f"- **{tmpl.comment_type.value}** — {tmpl.title}")
            lines.append(f"  Secciones: {sections}")
        lines.append("\nUsa: `jarvis run 'escribe un bug report sobre [descripción]'`")
        return AgentResult(
            success=True,
            content="\n".join(lines),
            data={"templates": [t.comment_type.value for t in templates]},
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    def _show_help(self, start: float) -> AgentResult:
        content = (
            "**QA Writer — Redacción profesional**\n\n"
            "Ejemplos de uso:\n"
            "- `escribe un bug report: el login falla con contraseña vacía`\n"
            "- `pregunta para dev: ¿por qué el endpoint /api/users retorna 500?`\n"
            "- `notifica al equipo: deploy de hotfix v2.3.1 programado para las 18:00`\n"
            "- `hallazgo en PR: SQL injection en el parámetro user_id`\n"
            "- `resultado de pruebas: suite de regresión pasó 45/50`\n"
        )
        return AgentResult(
            success=True,
            content=content,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    def _generate_general_comment(self, text: str) -> str:
        return (
            f"**Comentario QA:**\n\n{text}\n\n"
            "_Tip: Para usar un template estructurado, incluye palabras clave como "
            "'bug report', 'pregunta para dev', 'notifica al equipo', 'hallazgo' o 'resultado de pruebas'._"
        )


# Patrones de detección de tipo de comentario
_DETECTION_PATTERNS: list[tuple[str, str]] = [
    (r"(bug|defecto|error|falla|crash|no funciona|se cae|roto)", "bug_report"),
    (r"(pregunta|duda|consulta|por\s*qu[eé]|c[oó]mo|dev)", "dev_question"),
    (r"(notifi|avisa|comunica|informa|equipo|stakeholder)", "team_notification"),
    (r"(hallazgo|review|revis[ió]|encontr[eé]|detect[eé])", "review_finding"),
    (r"(resultado|suite|ejecuci[oó]n|pass|fail|report.*test)", "test_result"),
    (r"(template|plantilla|lista.*template)", "list"),
    (r"(ayuda|help|c[oó]mo.*uso|qu[eé].*puedo)", "help"),
]

_COMMENT_TYPE_MAP: dict[str, CommentType] = {
    "bug_report": CommentType.BUG_REPORT,
    "dev_question": CommentType.DEV_QUESTION,
    "team_notification": CommentType.TEAM_NOTIFICATION,
    "review_finding": CommentType.REVIEW_FINDING,
    "test_result": CommentType.TEST_RESULT,
}


def _extract_after(text: str, keywords: tuple[str, ...]) -> str:
    """Extraer texto después de una keyword."""
    text_lower = text.lower()
    for kw in keywords:
        idx = text_lower.find(kw)
        if idx >= 0:
            after = text[idx + len(kw):].strip().lstrip(":").strip()
            if after:
                # Tomar primera oración o hasta 120 chars
                end = min(len(after), 120)
                for sep in (".", "\n", ","):
                    pos = after.find(sep)
                    if 10 < pos < end:
                        end = pos
                return after[:end].strip()
    # Fallback: primeras palabras del texto
    words = text.split()[:10]
    return " ".join(words)


def _detect_severity(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ("crítico", "critical", "crash", "data loss", "seguridad")):
        return "Crítica"
    if any(w in text_lower for w in ("alto", "high", "bloqueante", "blocker")):
        return "Alta"
    if any(w in text_lower for w in ("bajo", "low", "menor", "cosmético")):
        return "Baja"
    return "Media"


def _detect_priority(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ("urgente", "urgent", "ahora", "inmediato", "blocker")):
        return "Urgente"
    if any(w in text_lower for w in ("alta", "high", "pronto")):
        return "Alta"
    return "Normal"


def _detect_environment(text: str) -> str:
    text_lower = text.lower()
    if "prod" in text_lower:
        return "Producción"
    if any(w in text_lower for w in ("staging", "stage", "pre")):
        return "Staging"
    if any(w in text_lower for w in ("qa", "test")):
        return "QA"
    if any(w in text_lower for w in ("local", "dev")):
        return "Desarrollo"
    return "Por confirmar"
