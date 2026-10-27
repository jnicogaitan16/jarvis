"""Workflows pre-configurados — pipelines listos para usar."""

from __future__ import annotations

from jarvis.pipelines.models import PipelineDef, PipelineStep


# ---------------------------------------------------------------------------
# Full QA Review: análisis completo de calidad
# ---------------------------------------------------------------------------
FULL_QA_REVIEW = PipelineDef(
    id="full_qa_review",
    name="Full QA Review",
    description=(
        "Revisión completa de calidad: análisis estático del código, "
        "generación de escenarios Gherkin, planificación de estrategia de testing "
        "y reporte estructurado de hallazgos"
    ),
    steps=[
        PipelineStep(
            agent_id="qa.code_review",
            name="Análisis de código",
            description="Análisis estático buscando vulnerabilidades, code smells y complejidad",
        ),
        PipelineStep(
            agent_id="qa.gherkin",
            name="Escenarios Gherkin",
            description="Generación de escenarios BDD basados en la funcionalidad",
        ),
        PipelineStep(
            agent_id="qa.strategy",
            name="Estrategia de testing",
            description="Plan de testing con recomendaciones y evaluación de automatización",
        ),
        PipelineStep(
            agent_id="qa.writer",
            name="Reporte de hallazgos",
            description="Documentación estructurada de los hallazgos encontrados",
            input_map={"question": "step_1_content"},
        ),
    ],
    tags=["qa", "review", "complete"],
)


# ---------------------------------------------------------------------------
# Feature Planning: planificación de nueva funcionalidad
# ---------------------------------------------------------------------------
FEATURE_PLANNING = PipelineDef(
    id="feature_planning",
    name="Feature Planning",
    description=(
        "Planificación de testing para nueva funcionalidad: "
        "escenarios BDD, estrategia de testing y evaluación de automatización"
    ),
    steps=[
        PipelineStep(
            agent_id="qa.gherkin",
            name="Escenarios BDD",
            description="Generar escenarios Gherkin para la feature",
        ),
        PipelineStep(
            agent_id="qa.strategy",
            name="Plan de testing",
            description="Definir tipos de test y evaluar automatización",
        ),
    ],
    tags=["qa", "planning", "feature"],
)


# ---------------------------------------------------------------------------
# Security Audit: auditoría de seguridad
# ---------------------------------------------------------------------------
SECURITY_AUDIT = PipelineDef(
    id="security_audit",
    name="Security Audit",
    description=(
        "Auditoría de seguridad: análisis estático enfocado en vulnerabilidades "
        "y generación de reporte de hallazgos de seguridad"
    ),
    steps=[
        PipelineStep(
            agent_id="qa.code_review",
            name="Análisis de seguridad",
            description="Escaneo de vulnerabilidades y patrones inseguros",
        ),
        PipelineStep(
            agent_id="qa.writer",
            name="Reporte de seguridad",
            description="Documentar hallazgos de seguridad como review findings",
            input_map={"question": "step_1_content", "action": ""},
        ),
    ],
    tags=["security", "audit"],
)


# ---------------------------------------------------------------------------
# Bug Triage: triaje de un bug reportado
# ---------------------------------------------------------------------------
BUG_TRIAGE = PipelineDef(
    id="bug_triage",
    name="Bug Triage",
    description=(
        "Triaje de un bug: genera bug report estructurado, "
        "analiza el código relacionado y propone estrategia de testing"
    ),
    steps=[
        PipelineStep(
            agent_id="qa.writer",
            name="Bug report",
            description="Generar reporte de bug estructurado",
        ),
        PipelineStep(
            agent_id="qa.code_review",
            name="Revisión de código",
            description="Analizar código relacionado al bug",
            stop_on_fail=False,
        ),
        PipelineStep(
            agent_id="qa.strategy",
            name="Plan de testing",
            description="Definir pruebas para verificar el fix",
        ),
    ],
    tags=["qa", "bug", "triage"],
)


# ---------------------------------------------------------------------------
# Registro de todos los workflows
# ---------------------------------------------------------------------------
WORKFLOWS: dict[str, PipelineDef] = {
    "full_qa_review": FULL_QA_REVIEW,
    "feature_planning": FEATURE_PLANNING,
    "security_audit": SECURITY_AUDIT,
    "bug_triage": BUG_TRIAGE,
}


def get_workflow(workflow_id: str) -> PipelineDef | None:
    """Obtener un workflow por ID."""
    return WORKFLOWS.get(workflow_id)


def list_workflows() -> list[PipelineDef]:
    """Listar todos los workflows disponibles."""
    return list(WORKFLOWS.values())
