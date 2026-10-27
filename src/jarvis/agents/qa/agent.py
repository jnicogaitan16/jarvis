"""QA Agent — análisis integral de PRs usando IAAgent pipeline."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from jarvis.agents.base import AgentRequest, AgentResult, AgentSpec, BaseAgent


class QAAgent(BaseAgent):
    """Agente QA que orquesta el pipeline completo de análisis de PRs.

    Flujo:
    1. Obtener datos del PR (Azure DevOps o datos directos)
    2. Ejecutar pipeline de IAAgent (6 analyzers + generators)
    3. Almacenar resultado en memoria episódica
    4. Guardar evidencias (reporte markdown)
    5. Retornar resultado estructurado
    """

    def spec(self) -> AgentSpec:
        return AgentSpec(
            id="qa.analyzer",
            name="QA Analyzer",
            description="Analiza PRs: código, seguridad, riesgo, test cases, escenarios Gherkin",
            skills=["analyze_pr", "qa"],
            tools=[
                "qa.diff_analyzer",
                "qa.security_analyzer",
                "qa.static_analyzer",
                "qa.risk_engine",
                "qa.test_case_generator",
            ],
        )

    def execute(self, request: AgentRequest) -> AgentResult:
        start = time.monotonic()
        request.payload.get("pr_id")
        project = request.project

        try:
            # Obtener PRContext
            pr_context = self._get_pr_context(request)
            if not pr_context:
                return AgentResult(
                    success=False,
                    error="No se pudo obtener el contexto del PR. Verifica credenciales Azure DevOps.",
                )

            # Ejecutar pipeline completo de IAAgent
            from jarvis.integrations.iaagent_bridge import _import
            pipeline = _import("agent.pipeline")
            result = pipeline.run_analysis(pr_context)

            # Construir resumen
            report = result.report
            summary = (
                f"PR #{pr_context.pr_id}: {pr_context.metadata.title}\n"
                f"Riesgo: {result.risk_score.level.value.upper()} ({result.risk_score.score}/10)\n"
                f"Findings: {len(report.all_findings)} "
                f"({len(report.critical_findings)} critical, {len(report.high_findings)} high)\n"
                f"Test cases: {len(result.test_cases)}\n"
                f"Recomendación: {report.recommendation.value}"
            )

            # Guardar evidencias
            evidence_paths = self._save_evidence(pr_context.pr_id, project, result)

            elapsed = int((time.monotonic() - start) * 1000)
            return AgentResult(
                success=True,
                content=summary,
                data={
                    "pr_id": pr_context.pr_id,
                    "title": pr_context.metadata.title,
                    "risk_level": result.risk_score.level.value,
                    "risk_score": result.risk_score.score,
                    "findings_total": len(report.all_findings),
                    "findings_critical": len(report.critical_findings),
                    "findings_high": len(report.high_findings),
                    "test_cases": len(result.test_cases),
                    "recommendation": report.recommendation.value,
                    "has_llm_enrichment": bool(result.llm_enrichment),
                },
                duration_ms=elapsed,
                evidence=evidence_paths,
            )

        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            return AgentResult(
                success=False,
                error=f"Error en análisis QA: {e}",
                duration_ms=elapsed,
            )

    def _get_pr_context(self, request: AgentRequest):
        """Obtener PRContext desde Azure DevOps o datos directos."""
        pr_id = request.payload.get("pr_id")

        # Opción 1: Datos directos (para testing o uso sin Azure DevOps)
        if "diffs" in request.payload:
            from jarvis.integrations.iaagent_bridge import get_pr_context_models
            models = get_pr_context_models()

            diffs = [
                models.DiffEntry.from_raw(d["path"], d["diff_text"])
                for d in request.payload["diffs"]
            ]
            changes = [
                models.FileChange(
                    path=c["path"],
                    change_type=models.ChangeType.from_str(c.get("change_type")),
                )
                for c in request.payload.get("changes", [])
            ]
            metadata = models.PRMetadata(
                pr_id=pr_id or 0,
                title=request.payload.get("title", f"PR {pr_id}"),
                description=request.payload.get("description", ""),
            )
            return models.PRContext(metadata=metadata, changes=changes, diffs=diffs)

        # Opción 2: Fetch desde Azure DevOps
        if pr_id:
            return self._fetch_from_azdo(pr_id)

        return None

    def _fetch_from_azdo(self, pr_id: int):
        """Obtener PR desde Azure DevOps via IAAgent client."""
        import os
        pat = os.environ.get("AZDO_PAT")
        org_url = os.environ.get("AZDO_ORG_URL")
        project = os.environ.get("AZDO_PROJECT")

        if not all([pat, org_url, project]):
            return None

        try:
            from jarvis.integrations.iaagent_bridge import get_azure_devops_client
            azdo_mod = get_azure_devops_client()
            client = azdo_mod.AzureDevOpsClient(
                org_url=org_url,
                pat=pat,
                project=project,
            )
            return client.build_pr_context(pr_id)
        except Exception:
            return None

    def _save_evidence(self, pr_id: int, project: str, result) -> list[str]:
        """Guardar reporte markdown como evidencia."""
        evidence_dir = Path("data/evidence") / project / datetime.now(UTC).strftime("%Y-%m-%d")
        evidence_dir.mkdir(parents=True, exist_ok=True)

        paths = []

        # Reporte completo
        report_path = evidence_dir / f"pr-{pr_id}-report.md"
        report_path.write_text(result.markdown, encoding="utf-8")
        paths.append(str(report_path))

        # Comentario para PR
        comment_path = evidence_dir / f"pr-{pr_id}-comment.md"
        comment_path.write_text(result.comment, encoding="utf-8")
        paths.append(str(comment_path))

        # Datos estructurados
        data_path = evidence_dir / f"pr-{pr_id}-data.json"
        data = {
            "pr_id": pr_id,
            "risk_level": result.risk_score.level.value if result.risk_score else "unknown",
            "risk_score": result.risk_score.score if result.risk_score else 0,
            "findings_count": len(result.report.all_findings),
            "test_cases_count": len(result.test_cases),
            "recommendation": result.report.recommendation.value,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        data_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        paths.append(str(data_path))

        return paths
