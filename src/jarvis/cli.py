"""CLI de JARVIS — interfaz principal con Typer."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
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


def _get_event_store() -> EventStore:
    config = load_global_config()
    db_path = config.get("database", {}).get("path", "data/jarvis.db")
    return EventStore(db_path=db_path)


@app.command()
def ask(
    question: str = typer.Argument(help="Pregunta o instrucción para JARVIS"),
    project: str = typer.Option("personal", "--project", "-p", help="Contexto de proyecto"),
):
    """Hacer una pregunta a JARVIS."""
    store = _get_event_store()
    ctx = load_project_context(project)

    store.emit(
        EventType.ACTION,
        payload={"command": "ask", "question": question, "project": project},
        project=project,
    )

    # Fase 1: respuesta basada en contexto de proyecto (sin LLM aún)
    console.print(
        Panel(
            f"[bold]Proyecto:[/bold] {ctx.display_name}\n"
            f"[bold]Providers:[/bold] {', '.join(sorted(ctx.allowed_providers))}\n"
            f"[bold]Cloud:[/bold] {'Sí' if ctx.allow_cloud else 'No'}\n\n"
            f"Pregunta recibida: [italic]{question}[/italic]\n\n"
            "[dim]LLM no disponible aún (Fase 2). Evento registrado.[/dim]",
            title="JARVIS",
            border_style="blue",
        )
    )

    store.emit(
        EventType.OBSERVATION,
        payload={"response": "LLM pendiente (Fase 2)", "project": project},
        project=project,
    )
    store.close()


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
    table.add_row("LLM (Ollama)", "[dim]Pendiente Fase 2[/dim]")
    table.add_row("LLM (Gemini)", "[dim]Pendiente Fase 2[/dim]")
    table.add_row("Memoria", "[dim]Pendiente Fase 3[/dim]")
    table.add_row("Agentes", "[dim]Pendiente Fase 4[/dim]")

    console.print(table)
    store.close()


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
