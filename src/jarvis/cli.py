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

    request = LLMRequest(
        prompt=question,
        system="Eres JARVIS, un asistente de IA personal. Responde de forma concisa y útil en español.",
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

    table.add_row("Memoria", "[dim]Pendiente Fase 3[/dim]")
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


if __name__ == "__main__":
    app()
