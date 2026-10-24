"""JARVIS Web Pages — dashboard HTML con Jinja2."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from jarvis import __version__
from jarvis.config import list_projects, load_global_config
from jarvis.core.events import EventStore
from jarvis.memory.manager import MemoryManager
from jarvis.memory.store import MemoryStore
from jarvis.observability.health import check_all
from jarvis.observability.metrics import MetricsCollector

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

router = APIRouter(tags=["pages"])


def _db_path() -> str:
    config = load_global_config()
    return config.get("database", {}).get("path", "data/jarvis.db")


def _render(request: Request, template: str, ctx: dict) -> HTMLResponse:
    """Render a template handling Starlette API differences."""
    ctx["request"] = request
    return _TEMPLATES.TemplateResponse(request=request, name=template, context=ctx)


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    collector = MetricsCollector(db_path=_db_path())
    metrics = collector.collect(days=7)
    checks = check_all(db_path=_db_path())

    return _render(request, "index.html", {
        "version": __version__,
        "metrics": metrics,
        "checks": checks,
        "projects": list_projects(),
        "healthy_count": sum(1 for c in checks if c.healthy),
        "total_checks": len(checks),
    })


@router.get("/memory", response_class=HTMLResponse)
def memory_page(request: Request):
    projects = list_projects()
    store = MemoryStore(db_path=_db_path())
    mgr = MemoryManager(store=store, embeddings_enabled=False)
    counts = {p: mgr.count(project=p) for p in projects}
    total = mgr.count()
    mgr.close()

    return _render(request, "memory.html", {
        "version": __version__,
        "projects": projects,
        "counts": counts,
        "total": total,
    })


@router.get("/agents", response_class=HTMLResponse)
def agents_page(request: Request):
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

    from jarvis.tools.registry import ToolRegistry
    tool_reg = ToolRegistry()
    try:
        from jarvis.tools.qa.analyzers import register_qa_tools
        register_qa_tools(tool_reg)
    except Exception:
        pass

    return _render(request, "agents.html", {
        "version": __version__,
        "agents": registry.list_all(),
        "tools": tool_reg.list_all(),
    })


@router.get("/events", response_class=HTMLResponse)
def events_page(request: Request):
    store = EventStore(db_path=_db_path())
    events = store.query(limit=50)
    store.close()

    return _render(request, "events.html", {
        "version": __version__,
        "events": events,
    })
