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

    # Registrar QA Agent si IAAgent está disponible
    try:
        from jarvis.agents.qa.agent import QAAgent
        from jarvis.integrations.iaagent_bridge import is_available
        if is_available():
            registry.register(QAAgent())
    except Exception:
        pass

    # Registrar KameCol Agent
    from jarvis.agents.business.kamecol_agent import KameColAgent
    registry.register(KameColAgent())

    store = _get_event_store()
    mem = _get_memory_manager()

    return Orchestrator(
        agent_registry=registry,
        event_store=store,
        memory_manager=mem,
    ), registry


def _build_tool_registry():
    """Construir Tool Registry con herramientas disponibles."""
    from jarvis.tools.registry import ToolRegistry

    registry = ToolRegistry()

    # Registrar QA tools de IAAgent si está disponible
    try:
        from jarvis.tools.qa.analyzers import register_qa_tools
        register_qa_tools(registry)
    except Exception:
        pass  # IAAgent no disponible, sin tools QA

    return registry


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

    _, agent_reg = _build_orchestrator()
    table.add_row("Agentes", f"[green]{agent_reg.count}[/green]")

    tool_reg = _build_tool_registry()
    table.add_row("Tools QA (IAAgent)", f"[green]{tool_reg.count}[/green]" if tool_reg.count else "[dim]No disponible[/dim]")

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
# QA commands
# ---------------------------------------------------------------------------

@app.command("analyze-pr")
def analyze_pr(
    pr_id: int = typer.Argument(help="ID del Pull Request"),
    project: str = typer.Option("integratepie", "--project", "-p", help="Proyecto"),
):
    """Analizar un PR completo con el QA Agent."""
    from jarvis.agents.base import AgentRequest
    from jarvis.core.models import MemoryType
    from jarvis.integrations.iaagent_bridge import is_available

    if not is_available():
        console.print("[red]IAAgent no disponible.[/red] Verifica IAAGENT_PATH.")
        return

    store = _get_event_store()
    mem = _get_memory_manager()

    console.print(f"[cyan]Analizando PR #{pr_id}...[/cyan]")

    from jarvis.agents.qa.agent import QAAgent
    agent = QAAgent()
    request = AgentRequest(
        intent="analyze_pr",
        payload={"pr_id": pr_id},
        project=project,
    )

    store.emit(
        EventType.ACTION,
        payload={"command": "analyze-pr", "pr_id": pr_id, "project": project},
        agent_id="qa.analyzer",
        project=project,
    )

    result = agent.execute(request)

    if result.success:
        console.print(
            Panel(
                result.content,
                title=f"QA Analysis — PR #{pr_id}",
                subtitle=f"{result.duration_ms}ms",
                border_style="green",
            )
        )

        # Guardar en memoria episódica
        mem.add(
            content=f"Análisis QA PR #{pr_id}: {result.content}",
            project=project,
            source=f"qa.analyzer:pr-{pr_id}",
            memory_type=MemoryType.EPISODIC,
            metadata=result.data,
            tags=["qa", "pr-analysis", f"pr-{pr_id}"],
        )

        if result.evidence:
            console.print(f"\n[dim]Evidencias guardadas:[/dim]")
            for path in result.evidence:
                console.print(f"  [dim]{path}[/dim]")

        store.emit(
            EventType.OBSERVATION,
            payload={
                "command": "analyze-pr",
                "pr_id": pr_id,
                "success": True,
                **result.data,
            },
            agent_id="qa.analyzer",
            project=project,
        )
    else:
        console.print(f"[red]Error:[/red] {result.error}")
        store.emit(
            EventType.ERROR,
            payload={"command": "analyze-pr", "pr_id": pr_id, "error": result.error},
            agent_id="qa.analyzer",
            project=project,
        )

    store.close()
    mem.close()


@app.command("work-item")
def work_item(
    wi_id: int = typer.Argument(help="ID del Work Item"),
):
    """Consultar un work item de Azure DevOps."""
    from jarvis.integrations.azure_devops import AzureDevOpsExtended

    client = AzureDevOpsExtended()
    if not client.is_configured:
        console.print("[yellow]Azure DevOps no configurado.[/yellow] Configura AZDO_PAT, AZDO_ORG_URL, AZDO_PROJECT.")
        return

    wi = client.get_work_item(wi_id)
    if not wi:
        console.print(f"[red]Work item #{wi_id} no encontrado.[/red]")
        return

    console.print(Panel(
        f"[bold]Tipo:[/bold] {wi.work_item_type}\n"
        f"[bold]Estado:[/bold] {wi.state}\n"
        f"[bold]Asignado:[/bold] {wi.assigned_to or '—'}\n"
        f"[bold]Tags:[/bold] {', '.join(wi.tags) if wi.tags else '—'}\n\n"
        f"[bold]Descripción:[/bold]\n{wi.description[:500] or '—'}\n\n"
        f"[bold]Criterios de aceptación:[/bold]\n{wi.acceptance_criteria[:500] or '—'}",
        title=f"#{wi.id} — {wi.title}",
        border_style="cyan",
    ))


@app.command("seed-knowledge")
def seed_knowledge_cmd(
    project: str = typer.Option("integratepie", "--project", "-p", help="Proyecto"),
):
    """Cargar knowledge base de un proyecto en memoria."""
    mem = _get_memory_manager()

    if project == "integratepie":
        from jarvis.integrations.pie_knowledge import seed_knowledge
        added = seed_knowledge(mem)
        console.print(f"[green]IntegratePIE:[/green] {added} registros agregados a memoria.")
    else:
        console.print(f"[yellow]Sin knowledge base disponible para '{project}'.[/yellow]")

    mem.close()


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
# Observability commands
# ---------------------------------------------------------------------------

@app.command()
def dashboard(
    days: int = typer.Option(7, "--days", "-d", help="Período en días"),
):
    """Dashboard completo de métricas del sistema."""
    from jarvis.observability.metrics import MetricsCollector

    collector = MetricsCollector(db_path=_get_db_path())
    m = collector.collect(days=days)

    # System overview
    table = Table(title=f"JARVIS Dashboard — últimos {days} días")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", justify="right")

    table.add_row("Eventos totales", f"{m.total_events:,}")
    table.add_row("Registros de memoria", f"{m.memory_records:,}")
    table.add_row("Requests LLM", f"{m.llm_requests:,}")
    table.add_row("Tokens consumidos", f"{m.llm_tokens:,}")
    table.add_row("Costo LLM", f"[green]${m.llm_cost_usd:.4f}[/green]")

    console.print(table)

    # Events by type
    if m.events_by_type:
        t2 = Table(title="Eventos por tipo")
        t2.add_column("Tipo", style="cyan")
        t2.add_column("Count", justify="right")
        for k, v in m.events_by_type.items():
            t2.add_row(k, str(v))
        console.print(t2)

    # Events by project
    if m.events_by_project:
        t3 = Table(title="Eventos por proyecto")
        t3.add_column("Proyecto", style="cyan")
        t3.add_column("Count", justify="right")
        for k, v in m.events_by_project.items():
            t3.add_row(k, str(v))
        console.print(t3)

    # Agent metrics
    if m.agent_metrics:
        t4 = Table(title="Métricas de agentes")
        t4.add_column("Agente", style="cyan")
        t4.add_column("Runs", justify="right")
        t4.add_column("OK", justify="right", style="green")
        t4.add_column("Fail", justify="right", style="red")
        t4.add_column("Rate", justify="right")
        t4.add_column("Avg ms", justify="right", style="dim")
        for am in m.agent_metrics:
            t4.add_row(
                am.agent_id, str(am.total_runs), str(am.successes),
                str(am.failures), f"{am.success_rate:.0f}%", str(am.avg_duration_ms),
            )
        console.print(t4)


@app.command()
def health():
    """Verificar estado de todos los componentes."""
    from jarvis.observability.health import check_all

    checks = check_all(db_path=_get_db_path())

    table = Table(title="Health Checks")
    table.add_column("Componente", style="cyan")
    table.add_column("Estado", width=6, justify="center")
    table.add_column("Detalle")

    for c in checks:
        icon = "[green]OK[/green]" if c.healthy else "[red]FAIL[/red]"
        table.add_row(c.component, icon, c.detail)

    console.print(table)


@app.command()
def benchmark(
    suite: str = typer.Option("intent", "--suite", "-s", help="Suite: intent, security, memory, all"),
):
    """Ejecutar benchmarks de calidad."""
    from jarvis.observability.benchmarks import (
        INTENT_DETECTION_CASES,
        MEMORY_ISOLATION_CASES,
        SECURITY_DETECTION_CASES,
        BenchmarkRunner,
    )

    runner = BenchmarkRunner()
    results = []

    if suite in ("intent", "all"):
        from jarvis.core.orchestrator import detect_intent
        r = runner.run_suite(
            "Intent Detection",
            INTENT_DETECTION_CASES,
            lambda data: {"intent": detect_intent(data["text"])},
        )
        results.append(r)

    if suite in ("security", "all"):
        try:
            from jarvis.integrations.iaagent_bridge import get_pr_context_models, get_security_analyzer, is_available
            if is_available():
                def _run_security(data):
                    mod = get_security_analyzer()
                    models = get_pr_context_models()
                    metadata = models.PRMetadata(pr_id=0, title="bench")
                    diff = models.DiffEntry.from_raw("test.py", data["diff"])
                    change = models.FileChange(path="test.py", change_type=models.ChangeType.EDIT)
                    ctx = models.PRContext(metadata=metadata, diffs=[diff], changes=[change])
                    findings = mod.SecurityAnalyzer().analyze(ctx)
                    return {"has_findings": len(findings) > 0}

                r = runner.run_suite("Security Detection", SECURITY_DETECTION_CASES, _run_security)
                results.append(r)
        except Exception as e:
            console.print(f"[yellow]Security benchmark skipped: {e}[/yellow]")

    if suite in ("memory", "all"):
        from jarvis.memory.manager import MemoryManager
        from jarvis.memory.store import MemoryStore

        store = MemoryStore(db_path=_get_db_path())
        mgr = MemoryManager(store=store, embeddings_enabled=False)

        def _run_memory(data):
            if data.get("data_project"):
                mgr.add(f"Test data for {data['query']}", project=data["data_project"], source="benchmark")
            results = mgr.search(data["query"], project=data["search_project"])
            return {"results_count": len(results), "results_found": len(results) > 0}

        r = runner.run_suite("Memory Isolation", MEMORY_ISOLATION_CASES, _run_memory)
        results.append(r)
        mgr.close()

    if not results:
        console.print("[yellow]Sin benchmarks ejecutados.[/yellow]")
        return

    for r in results:
        color = "green" if r.pass_rate >= 80 else "yellow" if r.pass_rate >= 50 else "red"
        table = Table(title=f"{r.name} — [{color}]{r.pass_rate:.0f}%[/{color}] ({r.passed}/{r.total})")
        table.add_column("ID", style="dim", width=8)
        table.add_column("Nombre")
        table.add_column("Estado", width=6, justify="center")
        table.add_column("ms", justify="right", width=5)

        for br in r.results:
            icon = "[green]PASS[/green]" if br.passed else "[red]FAIL[/red]"
            table.add_row(br.case_id, br.case_id, icon, str(br.duration_ms))

        console.print(table)


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
def tools(
    project: str = typer.Option("personal", "--project", "-p", help="Filtrar por proyecto"),
):
    """Listar herramientas disponibles."""
    reg = _build_tool_registry()
    specs = reg.list_for_project(project)

    if not specs:
        console.print("[dim]Sin herramientas disponibles.[/dim]")
        return

    table = Table(title=f"Herramientas JARVIS ({len(specs)})")
    table.add_column("ID", style="cyan")
    table.add_column("Nombre")
    table.add_column("Descripción", overflow="fold")
    table.add_column("Side effects", justify="center", width=12)

    for s in specs:
        table.add_row(s.id, s.name, s.description, "Sí" if s.has_side_effects else "No")

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


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host"),
    port: int = typer.Option(8000, "--port", help="Puerto"),
):
    """Iniciar servidor web con dashboard y API REST."""
    import uvicorn

    console.print(f"[cyan]JARVIS Web → http://{host}:{port}[/cyan]")
    console.print("[dim]API docs → /docs  |  Dashboard → /[/dim]")
    uvicorn.run("jarvis.web.app:app", host=host, port=port, reload=False)


@app.command()
def models():
    """Listar perfiles de modelos LLM disponibles."""
    from jarvis.llm.model_selector import ModelSelector

    selector = ModelSelector()
    profiles = selector.list_profiles()

    table = Table(title=f"Modelos LLM ({len(profiles)})")
    table.add_column("ID", style="cyan")
    table.add_column("Provider")
    table.add_column("Nombre")
    table.add_column("RAM", justify="right")
    table.add_column("Costo/MTok", justify="right")
    table.add_column("Recomendado para")

    for p in profiles:
        ram = f"{p.ram_gb}GB" if p.ram_gb else "cloud"
        cost = f"${p.cost_per_mtok:.2f}" if p.cost_per_mtok else "gratis"
        table.add_row(p.id, p.provider, p.name, ram, cost, ", ".join(p.recommended_for))

    console.print(table)


@app.command()
def approvals():
    """Ver políticas de autonomía y aprobación."""
    from jarvis.security.autonomy import DEFAULT_POLICIES

    table = Table(title="Políticas de Autonomía")
    table.add_column("Operación", style="cyan")
    table.add_column("Nivel mín.", justify="center")
    table.add_column("Aprobación", justify="center")
    table.add_column("Descripción")

    for p in DEFAULT_POLICIES:
        approval = "[red]Requerida[/red]" if p.requires_human_approval else "[green]Auto[/green]"
        table.add_row(p.operation.value, str(p.min_autonomy_level), approval, p.description)

    console.print(table)


if __name__ == "__main__":
    app()
