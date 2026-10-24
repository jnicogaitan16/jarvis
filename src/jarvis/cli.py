"""CLI de JARVIS — interfaz principal con Typer."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from jarvis import __version__
from jarvis.config import list_projects, load_global_config, load_project_context
from jarvis.core.events import EventStore
from jarvis.core.models import EventType

app = typer.Typer(
    name="jarvis",
    help="JARVIS — Plataforma personal de IA híbrida.",
    no_args_is_help=True,
)
console = Console()


def _get_db_path() -> str:
    config = load_global_config()
    return config.get("database", {}).get("path", "data/jarvis.db")


def _get_event_store() -> EventStore:
    return EventStore(db_path=_get_db_path())


def _build_router():
    """Construir LLM Router con providers disponibles."""
    from jarvis.llm.gemini import GeminiProvider
    from jarvis.llm.ollama import OllamaProvider
    from jarvis.llm.router import LLMRouter
    from jarvis.llm.usage import UsageTracker

    tracker = UsageTracker(db_path=_get_db_path())
    router = LLMRouter(usage_tracker=tracker)

    ollama = OllamaProvider()
    router.register(ollama)

    gemini = GeminiProvider()
    if gemini.is_available():
        router.register(gemini)

    return router, tracker


def _build_orchestrator():
    """Construir Orchestrator con agentes registrados."""
    from jarvis.agents.echo import EchoAgent
    from jarvis.agents.registry import AgentRegistry
    from jarvis.core.orchestrator import Orchestrator

    registry = AgentRegistry()
    registry.register(EchoAgent())

    store = _get_event_store()
    mem = _get_memory_manager()

    return Orchestrator(
        agent_registry=registry,
        event_store=store,
        memory_manager=mem,
    ), registry


def _get_memory_manager():
    """Construir Memory Manager."""
    from jarvis.memory.manager import MemoryManager
    from jarvis.memory.store import MemoryStore

    store = MemoryStore(db_path=_get_db_path())
    return MemoryManager(store=store, embeddings_enabled=True)


@app.command()
def ask(
    question: str = typer.Argument(help="Pregunta o instrucción para JARVIS"),
    project: str = typer.Option("personal", "--project", "-p", help="Contexto de proyecto"),
):
    """Hacer una pregunta a JARVIS."""
    from jarvis.llm.base import LLMRequest

    store = _get_event_store()
    ctx = load_project_context(project)

    store.emit(
        EventType.ACTION,
        payload={"command": "ask", "question": question, "project": project},
        project=project,
    )

    router, tracker = _build_router()
    available = router.available_providers()

    if not any(p.available for p in available):
        console.print(
            Panel(
                f"[bold]Proyecto:[/bold] {ctx.display_name}\n\n"
                f"Pregunta: [italic]{question}[/italic]\n\n"
                "[yellow]Sin proveedores LLM disponibles.[/yellow]\n"
                "[dim]Verifica que Ollama esté corriendo o configura GEMINI_API_KEY.[/dim]",
                title="JARVIS",
                border_style="yellow",
            )
        )
        store.emit(
            EventType.OBSERVATION,
            payload={"response": "Sin proveedores disponibles", "project": project},
            project=project,
        )
        store.close()
        tracker.close()
        return

    # Inyectar contexto de memoria en el prompt
    mem = _get_memory_manager()
    memory_context = mem.get_context_for_prompt(question, project=project)
    mem.close()

    system_prompt = "Eres JARVIS, un asistente de IA personal. Responde de forma concisa y útil en español."
    if memory_context:
        system_prompt += f"\n\n{memory_context}"

    request = LLMRequest(
        prompt=question,
        system=system_prompt,
        project=project,
    )

    try:
        response = router.generate(request, ctx)
        console.print(
            Panel(
                Markdown(response.content),
                title=f"JARVIS — {response.provider}:{response.model}",
                subtitle=f"{response.total_tokens} tokens · {response.latency_ms}ms · ${response.cost_usd:.4f}",
                border_style="blue",
            )
        )
        store.emit(
            EventType.OBSERVATION,
            payload={
                "response": response.content[:200],
                "provider": response.provider,
                "model": response.model,
                "tokens": response.total_tokens,
                "latency_ms": response.latency_ms,
                "cost_usd": response.cost_usd,
            },
            project=project,
        )
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        store.emit(
            EventType.ERROR,
            payload={"error": str(e), "project": project},
            project=project,
        )

    store.close()
    tracker.close()


@app.command()
def status():
    """Ver estado del sistema JARVIS."""
    store = _get_event_store()
    projects = list_projects()

    table = Table(title="JARVIS Status")
    table.add_column("Componente", style="cyan")
    table.add_column("Estado", style="green")

    table.add_row("Versión", __version__)
    table.add_row("Eventos totales", str(store.count()))
    table.add_row("Proyectos configurados", ", ".join(projects) if projects else "ninguno")

    # Check LLM providers
    router, tracker = _build_router()
    for ps in router.available_providers():
        label = f"LLM ({ps.provider})"
        if ps.available:
            table.add_row(label, f"[green]{ps.model}[/green]")
        else:
            table.add_row(label, f"[dim]{ps.error or 'No disponible'}[/dim]")

    mem = _get_memory_manager()
    mem_count = mem.count()
    table.add_row("Memoria", f"[green]{mem_count} registros[/green]" if mem_count else "[dim]Vacía[/dim]")
    mem.close()

    table.add_row("Agentes", "[dim]Pendiente Fase 4[/dim]")

    console.print(table)
    store.close()
    tracker.close()


@app.command()
def costs(
    days: int = typer.Option(7, "--days", "-d", help="Período en días"),
):
    """Ver resumen de costos de LLM."""
    from jarvis.llm.usage import UsageTracker

    tracker = UsageTracker(db_path=_get_db_path())
    summary = tracker.get_summary(days=days)
    total = tracker.get_total_cost(days=days)

    if not summary:
        console.print(f"[dim]Sin uso de LLM en los últimos {days} días.[/dim]")
        tracker.close()
        return

    table = Table(title=f"Costos LLM — últimos {days} días")
    table.add_column("Provider", style="cyan")
    table.add_column("Requests", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Costo", justify="right", style="green")
    table.add_column("Errores", justify="right", style="red")
    table.add_column("Latencia avg", justify="right", style="dim")

    for row in summary:
        table.add_row(
            row["provider"],
            str(row["requests"]),
            f"{row['tokens']:,}",
            f"${row['cost_usd']:.4f}",
            str(row["errors"]),
            f"{row['avg_latency_ms']}ms",
        )

    table.add_section()
    table.add_row("Total", "", "", f"[bold]${total:.4f}[/bold]", "", "")

    console.print(table)
    tracker.close()


@app.command()
def version():
    """Ver versión de JARVIS."""
    console.print(f"JARVIS v{__version__}")


@app.command()
def events(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filtrar por proyecto"),
    limit: int = typer.Option(10, "--limit", "-n", help="Número de eventos"),
):
    """Ver últimos eventos del sistema."""
    store = _get_event_store()
    results = store.query(project=project, limit=limit)

    if not results:
        console.print("[dim]No hay eventos registrados.[/dim]")
        store.close()
        return

    table = Table(title=f"Últimos {len(results)} eventos")
    table.add_column("Hora", style="dim", width=19)
    table.add_column("Tipo", style="cyan", width=12)
    table.add_column("Proyecto", width=14)
    table.add_column("Detalle", overflow="fold")

    for ev in results:
        ts = ev.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        detail = ""
        if "command" in ev.payload:
            detail = f"{ev.payload['command']}: {ev.payload.get('question', '')}"
        elif "response" in ev.payload:
            detail = ev.payload["response"][:80]
        else:
            detail = str(ev.payload)[:80]
        table.add_row(ts, ev.event_type.value, ev.project or "-", detail)

    console.print(table)
    store.close()


# ---------------------------------------------------------------------------
# Memory commands
# ---------------------------------------------------------------------------

memory_app = typer.Typer(help="Gestionar memoria persistente de JARVIS.")
app.add_typer(memory_app, name="memory")


@memory_app.command("add")
def memory_add(
    content: str = typer.Argument(help="Contenido a recordar"),
    project: str = typer.Option("personal", "--project", "-p", help="Proyecto asociado"),
    source: str = typer.Option("user", "--source", "-s", help="Fuente del conocimiento"),
    tag: Optional[list[str]] = typer.Option(None, "--tag", "-t", help="Tags"),
):
    """Agregar un registro a la memoria."""
    from jarvis.core.models import MemoryType

    mem = _get_memory_manager()
    record = mem.add(
        content=content,
        project=project,
        source=source,
        memory_type=MemoryType.SEMANTIC,
        tags=tag or [],
    )
    console.print(f"[green]Memorizado[/green] [{record.id}] en proyecto [cyan]{project}[/cyan]")
    mem.close()


@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(help="Texto a buscar"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filtrar por proyecto"),
    limit: int = typer.Option(5, "--limit", "-n", help="Número de resultados"),
):
    """Buscar en la memoria."""
    mem = _get_memory_manager()
    results = mem.search(query, project=project, limit=limit)

    if not results:
        console.print("[dim]Sin resultados.[/dim]")
        mem.close()
        return

    table = Table(title=f"Memoria — {len(results)} resultados para '{query}'")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Proyecto", style="cyan", width=14)
    table.add_column("Fuente", width=10)
    table.add_column("Contenido", overflow="fold")
    table.add_column("Score", justify="right", width=6)

    for record, score in results:
        table.add_row(
            record.id,
            record.project,
            record.source,
            record.content[:120],
            f"{score:.2f}",
        )

    console.print(table)
    mem.close()


@memory_app.command("list")
def memory_list(
    project: str = typer.Option("personal", "--project", "-p", help="Proyecto"),
    memory_type: Optional[str] = typer.Option(None, "--type", "-t", help="Tipo de memoria"),
    limit: int = typer.Option(20, "--limit", "-n", help="Número de registros"),
):
    """Listar registros de memoria de un proyecto."""
    mem = _get_memory_manager()
    records = mem.search_by_project(project, memory_type=memory_type, limit=limit)

    if not records:
        console.print(f"[dim]Sin registros para proyecto '{project}'.[/dim]")
        mem.close()
        return

    table = Table(title=f"Memoria — {project} ({len(records)} registros)")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Tipo", width=14)
    table.add_column("Fuente", width=10)
    table.add_column("Contenido", overflow="fold")
    table.add_column("Fecha", style="dim", width=10)

    for rec in records:
        table.add_row(
            rec.id,
            rec.memory_type.value,
            rec.source,
            rec.content[:100],
            rec.updated_at.strftime("%Y-%m-%d"),
        )

    console.print(table)
    mem.close()


@memory_app.command("count")
def memory_count():
    """Ver conteo de registros de memoria por proyecto."""
    mem = _get_memory_manager()
    projects = list_projects()

    table = Table(title="Memoria — Registros por proyecto")
    table.add_column("Proyecto", style="cyan")
    table.add_column("Registros", justify="right")

    total = 0
    for p in projects:
        c = mem.count(project=p)
        total += c
        table.add_row(p, str(c))

    table.add_section()
    table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")

    console.print(table)
    mem.close()


# ---------------------------------------------------------------------------
# Agent commands
# ---------------------------------------------------------------------------

@app.command()
def agents():
    """Listar agentes registrados."""
    _, registry = _build_orchestrator()

    specs = registry.list_all()
    if not specs:
        console.print("[dim]Sin agentes registrados.[/dim]")
        return

    table = Table(title=f"Agentes JARVIS ({len(specs)})")
    table.add_column("ID", style="cyan")
    table.add_column("Nombre")
    table.add_column("Skills", style="dim")
    table.add_column("Proyectos", style="dim")

    for s in specs:
        table.add_row(
            s.id,
            s.name,
            ", ".join(s.skills) if s.skills else "—",
            ", ".join(s.supported_projects) if s.supported_projects else "todos",
        )

    console.print(table)


@app.command()
def run(
    task: str = typer.Argument(help="Descripción de la tarea"),
    project: str = typer.Option("personal", "--project", "-p", help="Proyecto"),
):
    """Ejecutar una tarea a través del orchestrator."""
    from jarvis.agents.base import AgentRequest

    orchestrator, _ = _build_orchestrator()
    request = AgentRequest(
        intent=task,
        payload={"question": task},
        project=project,
    )

    result = orchestrator.route(request)

    if result.success:
        console.print(
            Panel(
                result.content,
                title=f"Agente: {result.agent_id}",
                subtitle=f"{result.duration_ms}ms",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Error:[/red] {result.error}")


if __name__ == "__main__":
    app()
