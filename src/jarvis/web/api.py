"""JARVIS API — endpoints REST JSON."""

from __future__ import annotations

from fastapi import APIRouter, Query

from jarvis import __version__
from jarvis.config import list_projects, load_global_config
from jarvis.core.events import EventStore
from jarvis.memory.manager import MemoryManager
from jarvis.memory.store import MemoryStore
from jarvis.observability.health import check_all
from jarvis.observability.metrics import MetricsCollector

router = APIRouter(tags=["api"])


def _db_path() -> str:
    config = load_global_config()
    return config.get("database", {}).get("path", "data/jarvis.db")


@router.get("/health")
def health():
    checks = check_all(db_path=_db_path())
    healthy = all(c.healthy for c in checks)
    return {
        "status": "healthy" if healthy else "degraded",
        "version": __version__,
        "checks": [{"component": c.component, "healthy": c.healthy, "detail": c.detail} for c in checks],
    }


@router.get("/metrics")
def metrics(days: int = Query(7, ge=1, le=365)):
    collector = MetricsCollector(db_path=_db_path())
    m = collector.collect(days=days)
    return {
        "period_days": days,
        "events_total": m.total_events,
        "events_by_type": m.events_by_type,
        "events_by_project": m.events_by_project,
        "memory_records": m.memory_records,
        "memory_by_project": m.memory_by_project,
        "llm_requests": m.llm_requests,
        "llm_tokens": m.llm_tokens,
        "llm_cost_usd": m.llm_cost_usd,
        "agents": [
            {
                "agent_id": a.agent_id,
                "runs": a.total_runs,
                "successes": a.successes,
                "failures": a.failures,
                "success_rate": round(a.success_rate, 1),
                "avg_ms": a.avg_duration_ms,
            }
            for a in m.agent_metrics
        ],
    }


@router.get("/projects")
def projects():
    return {"projects": list_projects()}


@router.get("/agents")
def agents():
    from jarvis.agents.echo import EchoAgent
    from jarvis.agents.registry import AgentRegistry

    registry = AgentRegistry()
    registry.register(EchoAgent())

    try:
        from jarvis.agents.qa.agent import QAAgent
        from jarvis.integrations.iaagent_bridge import is_available
        if is_available():
            registry.register(QAAgent())
    except Exception:
        pass

    try:
        from jarvis.agents.business.kamecol_agent import KameColAgent
        registry.register(KameColAgent())
    except Exception:
        pass

    return {
        "agents": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "skills": s.skills,
                "projects": s.supported_projects or ["todos"],
            }
            for s in registry.list_all()
        ]
    }


@router.get("/memory/search")
def memory_search(
    q: str = Query(..., min_length=1),
    project: str = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    store = MemoryStore(db_path=_db_path())
    mgr = MemoryManager(store=store, embeddings_enabled=False)
    results = mgr.search(q, project=project, limit=limit)
    mgr.close()
    return {
        "query": q,
        "project": project,
        "results": [
            {
                "id": r.id,
                "project": r.project,
                "type": r.memory_type.value,
                "source": r.source,
                "content": r.content,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat(),
                "tags": r.tags,
            }
            for r, score in results
        ],
    }


@router.get("/memory/list")
def memory_list(
    project: str = Query("personal"),
    memory_type: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    store = MemoryStore(db_path=_db_path())
    mgr = MemoryManager(store=store, embeddings_enabled=False)
    records = mgr.search_by_project(project, memory_type=memory_type, limit=limit)
    mgr.close()
    return {
        "project": project,
        "count": len(records),
        "records": [
            {
                "id": r.id,
                "type": r.memory_type.value,
                "source": r.source,
                "content": r.content,
                "confidence": r.confidence,
                "status": r.status,
                "updated_at": r.updated_at.isoformat(),
                "tags": r.tags,
            }
            for r in records
        ],
    }


@router.get("/events")
def events(
    project: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    store = EventStore(db_path=_db_path())
    results = store.query(project=project, limit=limit)
    store.close()
    return {
        "count": len(results),
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "type": e.event_type.value,
                "agent": e.agent_id,
                "project": e.project,
                "payload": e.payload,
            }
            for e in results
        ],
    }
