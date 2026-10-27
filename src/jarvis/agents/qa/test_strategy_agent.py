"""TestStrategyAgent — planificación inteligente de testing y evaluación de automatización."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from jarvis.agents.base import AgentRequest, AgentResult, AgentSpec, BaseAgent


class TestType:
    """Tipos de testing con criterios de selección."""

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    API = "api"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    SMOKE = "smoke"
    REGRESSION = "regression"


@dataclass
class TestRecommendation:
    """Recomendación de un tipo de test."""

    test_type: str
    priority: str  # alta, media, baja
    automate: bool
    rationale: str
    effort: str  # bajo, medio, alto
    tools: list[str] = field(default_factory=list)


@dataclass
class AutomationAssessment:
    """Evaluación de si vale la pena automatizar."""

    should_automate: bool
    confidence: float  # 0.0 - 1.0
    reasons_for: list[str] = field(default_factory=list)
    reasons_against: list[str] = field(default_factory=list)
    roi_estimate: str = ""  # bajo, medio, alto


class TestStrategyAgent(BaseAgent):
    """Agente de planificación de testing y evaluación de automatización."""

    def spec(self) -> AgentSpec:
        return AgentSpec(
            id="qa.strategy",
            name="Test Strategy Planner",
            description="Planifica estrategia de testing, recomienda tipos de prueba y evalúa si automatizar",
            skills=["test_strategy", "automation"],
            supported_projects=[],
        )

    def execute(self, request: AgentRequest) -> AgentResult:
        start = time.monotonic()
        try:
            question = request.payload.get("question", request.intent)
            action = request.payload.get("action", self._detect_action(question))

            if action == "assess_automation":
                return self._assess_automation(question, start)
            if action == "help":
                return self._show_help(start)

            return self._plan_strategy(question, request.project, start)

        except Exception as e:
            return AgentResult(
                success=False,
                error=str(e),
                duration_ms=int((time.monotonic() - start) * 1000),
            )

    def _detect_action(self, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"(automa|vale.+la.+pena|conviene|roi|deber[ií]a.+autom)", text_lower):
            return "assess_automation"
        if re.search(r"(ayuda|help)", text_lower):
            return "help"
        return "plan"

    def _plan_strategy(self, text: str, project: str, start: float) -> AgentResult:
        """Generar estrategia de testing completa."""
        recommendations = self._generate_recommendations(text)
        assessment = self._evaluate_automation(text, recommendations)

        # Renderizar
        lines = ["## Estrategia de Testing\n"]
        lines.append(f"**Funcionalidad:** {self._extract_feature(text)}")
        lines.append(f"**Proyecto:** {project}\n")

        # Tabla de recomendaciones
        lines.append("### Recomendaciones de Testing\n")
        lines.append("| Tipo | Prioridad | Automatizar | Esfuerzo | Herramientas |")
        lines.append("|------|-----------|-------------|----------|--------------|")

        for rec in recommendations:
            auto = "Si" if rec.automate else "No"
            tools = ", ".join(rec.tools) if rec.tools else "—"
            lines.append(f"| {rec.test_type} | {rec.priority} | {auto} | {rec.effort} | {tools} |")

        # Detalle por tipo
        lines.append("\n### Detalle\n")
        for rec in recommendations:
            auto_label = "Automatizar" if rec.automate else "Manual"
            lines.append(f"**{rec.test_type}** ({auto_label}) — {rec.rationale}")

        # Evaluación de automatización
        lines.append("\n### Evaluación de Automatización\n")
        verdict = "AUTOMATIZAR" if assessment.should_automate else "MANUAL"
        lines.append(f"**Veredicto:** {verdict} (confianza: {assessment.confidence:.0%})")
        lines.append(f"**ROI estimado:** {assessment.roi_estimate}\n")

        if assessment.reasons_for:
            lines.append("**A favor de automatizar:**")
            for r in assessment.reasons_for:
                lines.append(f"- {r}")

        if assessment.reasons_against:
            lines.append("\n**En contra de automatizar:**")
            for r in assessment.reasons_against:
                lines.append(f"- {r}")

        content = "\n".join(lines)

        return AgentResult(
            success=True,
            content=content,
            data={
                "recommendations": [
                    {"type": r.test_type, "priority": r.priority, "automate": r.automate}
                    for r in recommendations
                ],
                "should_automate": assessment.should_automate,
                "automation_confidence": assessment.confidence,
            },
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    def _generate_recommendations(self, text: str) -> list[TestRecommendation]:
        """Generar recomendaciones basadas en el contexto."""
        recs = []
        text_lower = text.lower()

        # Siempre recomendar smoke test
        recs.append(TestRecommendation(
            test_type=TestType.SMOKE,
            priority="alta",
            automate=True,
            rationale="Verificación rápida de que la funcionalidad básica no está rota",
            effort="bajo",
            tools=["Playwright"],
        ))

        # API testing si hay endpoints
        if any(w in text_lower for w in ("api", "endpoint", "rest", "request", "response", "json")):
            recs.append(TestRecommendation(
                test_type=TestType.API,
                priority="alta",
                automate=True,
                rationale="Los tests de API son estables, rápidos y con alto ROI",
                effort="bajo",
                tools=["Postman", "httpx", "pytest"],
            ))

        # E2E si hay UI
        if any(w in text_lower for w in ("ui", "pantalla", "formulario", "botón", "click", "login",
                                          "carrito", "checkout", "navegación", "página")):
            recs.append(TestRecommendation(
                test_type=TestType.E2E,
                priority="alta",
                automate=True,
                rationale="Flujos críticos de usuario deben tener cobertura E2E",
                effort="medio",
                tools=["Playwright MCP"],
            ))

        # Unit testing si hay lógica
        if any(w in text_lower for w in ("cálculo", "lógica", "validación", "algoritmo", "función",
                                          "class", "método", "parser", "transformación")):
            recs.append(TestRecommendation(
                test_type=TestType.UNIT,
                priority="alta",
                automate=True,
                rationale="Lógica de negocio debe estar cubierta con unit tests",
                effort="bajo",
                tools=["pytest", "unittest"],
            ))

        # Integration
        if any(w in text_lower for w in ("base de datos", "db", "sql", "integración", "servicio",
                                          "microservicio", "queue", "evento")):
            recs.append(TestRecommendation(
                test_type=TestType.INTEGRATION,
                priority="media",
                automate=True,
                rationale="Interacciones entre componentes requieren testing de integración",
                effort="medio",
                tools=["pytest", "testcontainers"],
            ))

        # Performance
        if any(w in text_lower for w in ("rendimiento", "performance", "carga", "load", "velocidad",
                                          "concurrencia", "latencia", "timeout")):
            recs.append(TestRecommendation(
                test_type=TestType.PERFORMANCE,
                priority="media",
                automate=True,
                rationale="Validar rendimiento bajo carga para evitar degradación",
                effort="alto",
                tools=["k6", "locust", "artillery"],
            ))

        # Security
        if any(w in text_lower for w in ("seguridad", "security", "auth", "token", "inyección",
                                          "xss", "csrf", "sql injection", "owasp")):
            recs.append(TestRecommendation(
                test_type=TestType.SECURITY,
                priority="alta",
                automate=True,
                rationale="Vulnerabilidades de seguridad son de alto impacto",
                effort="medio",
                tools=["Semgrep", "OWASP ZAP"],
            ))

        # Regression siempre
        recs.append(TestRecommendation(
            test_type=TestType.REGRESSION,
            priority="media",
            automate=True,
            rationale="Suite de regresión para detectar efectos secundarios",
            effort="medio",
            tools=["Playwright MCP", "pytest"],
        ))

        return recs

    def _evaluate_automation(self, text: str, recs: list[TestRecommendation]) -> AutomationAssessment:
        """Evaluar si la automatización vale la pena."""
        reasons_for = []
        reasons_against = []
        score = 0.5  # neutral start

        text_lower = text.lower()

        # Factores a favor
        if any(w in text_lower for w in ("repetitivo", "regresión", "frecuente", "ci/cd", "deploy")):
            reasons_for.append("Se ejecuta frecuentemente — alto retorno en automatización")
            score += 0.15

        if any(w in text_lower for w in ("api", "endpoint", "rest")):
            reasons_for.append("Tests de API son estables y con bajo mantenimiento")
            score += 0.1

        if any(w in text_lower for w in ("crítico", "core", "pago", "login", "checkout")):
            reasons_for.append("Funcionalidad crítica — el costo del fallo justifica la inversión")
            score += 0.15

        if any(w in text_lower for w in ("datos", "combinaciones", "escenarios", "parámetros")):
            reasons_for.append("Muchas combinaciones de datos — difícil cubrir manualmente")
            score += 0.1

        # Factores en contra
        if any(w in text_lower for w in ("visual", "diseño", "css", "layout", "estético")):
            reasons_against.append("Validación visual es difícil de automatizar de forma confiable")
            score -= 0.15

        if any(w in text_lower for w in ("exploratorio", "ad-hoc", "usabilidad", "ux")):
            reasons_against.append("Testing exploratorio/UX requiere juicio humano")
            score -= 0.2

        if any(w in text_lower for w in ("una vez", "migración", "one-time", "temporal")):
            reasons_against.append("Ejecución única — el costo de automatizar no se recupera")
            score -= 0.2

        if any(w in text_lower for w in ("cambia mucho", "inestable", "prototipo", "mvp")):
            reasons_against.append("UI/requisitos inestables — alto costo de mantenimiento")
            score -= 0.15

        # Bonus por tener herramientas
        automate_count = sum(1 for r in recs if r.automate)
        if automate_count > len(recs) * 0.6:
            reasons_for.append(f"{automate_count}/{len(recs)} tipos de test son automatizables")
            score += 0.05

        score = max(0.0, min(1.0, score))
        should_automate = score >= 0.5

        roi = "alto" if score > 0.7 else "medio" if score > 0.4 else "bajo"

        return AutomationAssessment(
            should_automate=should_automate,
            confidence=score,
            reasons_for=reasons_for or ["La mayoría de los tests recomendados son automatizables"],
            reasons_against=reasons_against or ["Sin factores en contra identificados"],
            roi_estimate=roi,
        )

    def _assess_automation(self, text: str, start: float) -> AgentResult:
        """Evaluación dedicada de automatización."""
        recs = self._generate_recommendations(text)
        assessment = self._evaluate_automation(text, recs)

        verdict = "SI, AUTOMATIZAR" if assessment.should_automate else "NO, MANUAL"
        lines = [
            "## Evaluación de Automatización\n",
            f"**Veredicto:** {verdict}",
            f"**Confianza:** {assessment.confidence:.0%}",
            f"**ROI estimado:** {assessment.roi_estimate}\n",
        ]

        lines.append("### A favor")
        for r in assessment.reasons_for:
            lines.append(f"- {r}")

        lines.append("\n### En contra")
        for r in assessment.reasons_against:
            lines.append(f"- {r}")

        lines.append("\n### Recomendación de herramientas")
        for rec in recs:
            if rec.automate and rec.tools:
                lines.append(f"- **{rec.test_type}:** {', '.join(rec.tools)}")

        return AgentResult(
            success=True,
            content="\n".join(lines),
            data={
                "should_automate": assessment.should_automate,
                "confidence": assessment.confidence,
                "roi": assessment.roi_estimate,
            },
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    def _extract_feature(self, text: str) -> str:
        words = text.split()[:12]
        return " ".join(words) if words else "Funcionalidad bajo análisis"

    def _show_help(self, start: float) -> AgentResult:
        content = (
            "**Test Strategy Planner**\n\n"
            "Planifica tu estrategia de testing y evalúa si vale la pena automatizar.\n\n"
            "Ejemplos:\n"
            "- `estrategia de testing para el checkout de KameCol`\n"
            "- `¿vale la pena automatizar los tests del formulario de login?`\n"
            "- `plan de pruebas para el endpoint API de órdenes`\n"
            "- `¿debería automatizar las pruebas de regresión del dashboard?`\n\n"
            "Genera:\n"
            "- Recomendaciones por tipo de test (smoke, API, E2E, unit, etc.)\n"
            "- Evaluación de automatización con ROI estimado\n"
            "- Herramientas sugeridas\n"
        )
        return AgentResult(
            success=True,
            content=content,
            duration_ms=int((time.monotonic() - start) * 1000),
        )
