"""Templates de comentarios estructurados para comunicación QA profesional."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CommentType(StrEnum):
    """Tipos de comentario estructurado."""

    BUG_REPORT = "bug_report"
    DEV_QUESTION = "dev_question"
    TEAM_NOTIFICATION = "team_notification"
    REVIEW_FINDING = "review_finding"
    TEST_RESULT = "test_result"


@dataclass(frozen=True)
class CommentTemplate:
    """Template de comentario con secciones requeridas."""

    comment_type: CommentType
    title: str
    sections: list[str]
    template: str


# ---------------------------------------------------------------------------
# Bug Report — para reportar defectos encontrados
# ---------------------------------------------------------------------------
BUG_REPORT = CommentTemplate(
    comment_type=CommentType.BUG_REPORT,
    title="Bug Report",
    sections=["resumen", "pasos", "esperado", "actual", "evidencia", "severidad", "entorno"],
    template="""\
## 🐛 Bug Report: {title}

**Severidad:** {severity} | **Prioridad:** {priority}
**Componente:** {component} | **Entorno:** {environment}

### Resumen
{summary}

### Pasos para reproducir
{steps}

### Resultado esperado
{expected}

### Resultado actual
{actual}

### Evidencia
{evidence}

### Información adicional
- **Frecuencia:** {frequency}
- **Workaround:** {workaround}
- **Reportado por:** {reporter}
- **Fecha:** {date}
""",
)

# ---------------------------------------------------------------------------
# Dev Question — para hacer preguntas técnicas a desarrollo
# ---------------------------------------------------------------------------
DEV_QUESTION = CommentTemplate(
    comment_type=CommentType.DEV_QUESTION,
    title="Pregunta a Desarrollo",
    sections=["contexto", "pregunta", "impacto", "sugerencia"],
    template="""\
## ❓ Pregunta para DEV: {title}

**Contexto:** {context_area} | **Urgencia:** {urgency}

### Contexto
{context}

### Pregunta
{question}

### ¿Por qué es relevante para QA?
{qa_impact}

### Sugerencia / Hipótesis
{suggestion}

### Archivos / Endpoints relacionados
{references}
""",
)

# ---------------------------------------------------------------------------
# Team Notification — para comunicar al equipo no-técnico
# ---------------------------------------------------------------------------
TEAM_NOTIFICATION = CommentTemplate(
    comment_type=CommentType.TEAM_NOTIFICATION,
    title="Notificación al Equipo",
    sections=["que_paso", "impacto", "accion", "timeline"],
    template="""\
## 📢 {title}

**Estado:** {status} | **Impacto:** {impact_level}

### ¿Qué pasó?
{what_happened}

### ¿A quién afecta?
{who_affected}

### ¿Qué estamos haciendo?
{action_taken}

### ¿Cuándo se resuelve?
{timeline}

### ¿Qué necesitamos del equipo?
{team_action}
""",
)

# ---------------------------------------------------------------------------
# Review Finding — para hallazgos en revisión de código/PR
# ---------------------------------------------------------------------------
REVIEW_FINDING = CommentTemplate(
    comment_type=CommentType.REVIEW_FINDING,
    title="Hallazgo en Revisión",
    sections=["hallazgo", "ubicacion", "riesgo", "recomendacion"],
    template="""\
## 🔍 {finding_type}: {title}

**Archivo:** `{file_path}` | **Línea:** {line_ref}
**Riesgo:** {risk_level} | **Categoría:** {category}

### Hallazgo
{finding}

### Impacto potencial
{impact}

### Recomendación
{recommendation}

### Referencia
{reference}
""",
)

# ---------------------------------------------------------------------------
# Test Result — para reportar resultados de ejecución de pruebas
# ---------------------------------------------------------------------------
TEST_RESULT = CommentTemplate(
    comment_type=CommentType.TEST_RESULT,
    title="Resultado de Pruebas",
    sections=["resumen", "passed", "failed", "blocked", "observaciones"],
    template="""\
## 🧪 Resultado: {suite_name}

**Ejecutado:** {execution_date} | **Duración:** {duration}
**Entorno:** {environment}

### Resumen
| Métrica | Valor |
|---------|-------|
| Total | {total} |
| Passed | {passed} |
| Failed | {failed} |
| Blocked | {blocked} |
| Pass Rate | {pass_rate} |

### Casos fallidos
{failed_details}

### Casos bloqueados
{blocked_details}

### Observaciones
{observations}

### Siguiente paso
{next_steps}
""",
)


TEMPLATES: dict[CommentType, CommentTemplate] = {
    CommentType.BUG_REPORT: BUG_REPORT,
    CommentType.DEV_QUESTION: DEV_QUESTION,
    CommentType.TEAM_NOTIFICATION: TEAM_NOTIFICATION,
    CommentType.REVIEW_FINDING: REVIEW_FINDING,
    CommentType.TEST_RESULT: TEST_RESULT,
}


def get_template(comment_type: CommentType) -> CommentTemplate:
    """Obtener template por tipo de comentario."""
    return TEMPLATES[comment_type]


def list_templates() -> list[CommentTemplate]:
    """Listar todos los templates disponibles."""
    return list(TEMPLATES.values())


def render_template(comment_type: CommentType, **kwargs) -> str:
    """Renderizar un template con los valores proporcionados."""
    tmpl = TEMPLATES[comment_type]
    # Rellenar campos faltantes con placeholder
    for section in tmpl.sections:
        kwargs.setdefault(section, f"_[Pendiente: {section}]_")
    return tmpl.template.format_map(_SafeDict(kwargs))


class _SafeDict(dict):
    """Dict que retorna placeholder para keys faltantes en format_map."""

    def __missing__(self, key: str) -> str:
        return f"_[{key}]_"
