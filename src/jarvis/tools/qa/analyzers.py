"""QA Analyzer Tools — wrappers de los analyzers de IAAgent como JARVIS Tools.

API de IAAgent:
- DiffAnalyzer().analyze(pr_context) -> DiffAnalysisResult
- SecurityAnalyzer().analyze(pr_context) -> list[Finding]
- StaticAnalyzer().analyze(pr_context) -> list[Finding]
- RiskEngine().compute(pr_context, findings, impact_areas) -> RiskScore
- TestCaseGenerator().generate(pr_context, diff_result, findings, impact_areas, risk_score) -> list[TestCase]
"""

from __future__ import annotations

from jarvis.core.models import ProjectContext, ToolAction
from jarvis.tools.base import BaseTool, ToolSpec


def _build_pr_context(params: dict):
    """Construir PRContext mínimo desde parámetros del tool."""
    from jarvis.integrations.iaagent_bridge import get_pr_context_models
    models = get_pr_context_models()

    diffs = [
        models.DiffEntry.from_raw(d["path"], d["diff_text"])
        for d in params.get("diffs", [])
    ]
    changes = [
        models.FileChange(
            path=c["path"],
            change_type=models.ChangeType.from_str(c.get("change_type")),
        )
        for c in params.get("changes", [])
    ]
    metadata = models.PRMetadata(
        pr_id=params.get("pr_id", 0),
        title=params.get("title", ""),
        description=params.get("description", ""),
    )
    return models.PRContext(metadata=metadata, changes=changes, diffs=diffs)


class DiffAnalyzerTool(BaseTool):
    """Analiza diffs de un PR: clasifica archivos, extrae funciones y endpoints."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            id="qa.diff_analyzer",
            name="Diff Analyzer",
            description="Clasifica archivos modificados, extrae funciones, endpoints y cambios de BD",
        )

    def _run(self, action: ToolAction, context: ProjectContext) -> dict:
        from jarvis.integrations.iaagent_bridge import get_diff_analyzer
        mod = get_diff_analyzer()

        pr_context = _build_pr_context(action.parameters)
        analyzer = mod.DiffAnalyzer()
        result = analyzer.analyze(pr_context)

        return {
            "file_classifications": result.file_classifications,
            "modified_functions": result.modified_functions,
            "modified_classes": result.modified_classes,
            "modified_endpoints": result.modified_endpoints,
            "db_changes": result.db_changes,
            "config_changes": result.config_changes,
            "findings_count": len(result.findings),
            "stats": {
                "total_files": result.stats.total_files,
                "total_added": result.stats.total_added,
                "total_deleted": result.stats.total_deleted,
            },
        }


class SecurityAnalyzerTool(BaseTool):
    """Detecta vulnerabilidades de seguridad (OWASP Top 10) en diffs."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            id="qa.security_analyzer",
            name="Security Analyzer",
            description="Detecta secretos, SQL injection, XSS, command injection y más (14+ patrones OWASP)",
        )

    def _run(self, action: ToolAction, context: ProjectContext) -> dict:
        from jarvis.integrations.iaagent_bridge import get_security_analyzer
        mod = get_security_analyzer()

        pr_context = _build_pr_context(action.parameters)
        analyzer = mod.SecurityAnalyzer()
        findings = analyzer.analyze(pr_context)

        return {
            "findings": [
                {
                    "id": f.id,
                    "severity": f.severity.value,
                    "category": f.category,
                    "title": f.title,
                    "description": f.description,
                    "file": f.file,
                    "line": f.line,
                }
                for f in findings
            ],
            "total": len(findings),
            "critical": sum(1 for f in findings if f.severity.value == "critical"),
            "high": sum(1 for f in findings if f.severity.value == "high"),
        }


class StaticAnalyzerTool(BaseTool):
    """Detecta TODOs, debug code, secrets hardcoded y bare except."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            id="qa.static_analyzer",
            name="Static Analyzer",
            description="Detecta TODOs, código de debug, secrets y patrones problemáticos",
        )

    def _run(self, action: ToolAction, context: ProjectContext) -> dict:
        from jarvis.integrations.iaagent_bridge import get_static_analyzer
        mod = get_static_analyzer()

        pr_context = _build_pr_context(action.parameters)
        analyzer = mod.StaticAnalyzer()
        findings = analyzer.analyze(pr_context)

        return {
            "findings": [
                {
                    "id": f.id,
                    "severity": f.severity.value,
                    "category": f.category,
                    "title": f.title,
                    "file": f.file,
                }
                for f in findings
            ],
            "total": len(findings),
        }


class RiskEngineTool(BaseTool):
    """Calcula score de riesgo ponderado (0-10) para un PR."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            id="qa.risk_engine",
            name="Risk Engine",
            description="Calcula score de riesgo 0-10 con factores ponderados",
        )

    def _run(self, action: ToolAction, context: ProjectContext) -> dict:
        from jarvis.integrations.iaagent_bridge import get_risk_engine
        mod = get_risk_engine()

        pr_context = _build_pr_context(action.parameters)
        engine = mod.RiskEngine()
        risk_score = engine.compute(
            context=pr_context,
            findings=action.parameters.get("_findings_objects", []),
            impact_areas=action.parameters.get("_impact_areas_objects", []),
        )

        return {
            "level": risk_score.level.value,
            "score": risk_score.score,
            "factors": risk_score.factors,
            "summary": risk_score.summary,
        }


class TestCaseGeneratorTool(BaseTool):
    """Genera casos de prueba estructurados en 7 categorías."""

    def spec(self) -> ToolSpec:
        return ToolSpec(
            id="qa.test_case_generator",
            name="Test Case Generator",
            description="Genera test cases: functional, regression, integration, security, negative, edge_case, performance",
        )

    def _run(self, action: ToolAction, context: ProjectContext) -> dict:
        from jarvis.integrations.iaagent_bridge import get_diff_analyzer, get_test_case_generator
        mod = get_test_case_generator()
        diff_mod = get_diff_analyzer()

        pr_context = _build_pr_context(action.parameters)

        # Run diff analysis first (needed by generator)
        diff_analyzer = diff_mod.DiffAnalyzer()
        diff_result = diff_analyzer.analyze(pr_context)

        generator = mod.TestCaseGenerator()
        test_cases = generator.generate(
            context=pr_context,
            diff_result=diff_result,
            findings=action.parameters.get("_findings_objects", []),
            impact_areas=action.parameters.get("_impact_areas_objects", []),
            risk_score=action.parameters.get("_risk_score_object", None),
        )

        return {
            "test_cases": [
                {
                    "id": tc.id,
                    "title": tc.title,
                    "priority": tc.priority.value,
                    "type": tc.test_type.value,
                    "steps": tc.steps,
                    "expected_result": tc.expected_result,
                }
                for tc in test_cases
            ],
            "total": len(test_cases),
        }


def register_qa_tools(registry) -> int:
    """Registrar todos los QA tools de IAAgent en un ToolRegistry.

    Retorna el número de tools registrados. Solo registra si IAAgent está disponible.
    """
    from jarvis.integrations.iaagent_bridge import is_available

    if not is_available():
        return 0

    tools = [
        DiffAnalyzerTool(),
        SecurityAnalyzerTool(),
        StaticAnalyzerTool(),
        RiskEngineTool(),
        TestCaseGeneratorTool(),
    ]

    count = 0
    for tool in tools:
        registry.register(tool)
        count += 1

    return count
