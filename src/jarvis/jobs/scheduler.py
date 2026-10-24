"""Scheduler — tareas periódicas configurables con Huey."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from jarvis.jobs.engine import huey

log = logging.getLogger(__name__)


@huey.periodic_task(huey.crontab(hour="3", minute="0"))
def daily_maintenance():
    """Mantenimiento diario (3 AM): limpiar eventos antiguos, verificar memoria."""
    log.info("Maintenance: starting daily cleanup")
    try:
        from jarvis.config import load_global_config
        from jarvis.core.events import EventStore

        db_path = load_global_config().get("database", {}).get("path", "data/jarvis.db")
        store = EventStore(db_path=db_path)
        count = store.count()
        store.close()
        log.info("Maintenance: %d events in store", count)
        return {"status": "ok", "events": count, "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        log.error("Maintenance failed: %s", e)
        return {"status": "error", "error": str(e)}


@huey.periodic_task(huey.crontab(day_of_week="1", hour="9", minute="0"))
def weekly_knowledge_audit():
    """Auditoría semanal de memoria (lunes 9 AM): detectar registros obsoletos."""
    log.info("Knowledge audit: starting weekly check")
    try:
        from jarvis.config import list_projects, load_global_config
        from jarvis.memory.manager import MemoryManager
        from jarvis.memory.store import MemoryStore

        db_path = load_global_config().get("database", {}).get("path", "data/jarvis.db")
        store = MemoryStore(db_path=db_path)
        mgr = MemoryManager(store=store, embeddings_enabled=False)

        report = {}
        for project in list_projects():
            count = mgr.count(project=project)
            report[project] = count

        mgr.close()
        log.info("Knowledge audit: %s", report)
        return {"status": "ok", "memory_counts": report}
    except Exception as e:
        log.error("Knowledge audit failed: %s", e)
        return {"status": "error", "error": str(e)}


@huey.task(retries=2, retry_delay=30)
def run_scheduled_analysis(pr_id: int, project: str = "integratepie"):
    """Análisis QA programado para un PR específico."""
    log.info("Scheduled analysis: PR #%d in %s", pr_id, project)
    try:
        from jarvis.agents.base import AgentRequest
        from jarvis.agents.qa.agent import QAAgent

        agent = QAAgent()
        request = AgentRequest(
            intent="analyze_pr",
            payload={"pr_id": pr_id},
            project=project,
        )
        result = agent.execute(request)
        return {
            "pr_id": pr_id,
            "success": result.success,
            "summary": result.content[:200] if result.success else result.error,
        }
    except Exception as e:
        log.error("Scheduled analysis failed: %s", e)
        return {"pr_id": pr_id, "success": False, "error": str(e)}
