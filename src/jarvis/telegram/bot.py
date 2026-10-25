"""JARVIS Telegram Bot — control remoto desde iPhone.

Comandos:
  /start     — Bienvenida
  /status    — Estado del sistema
  /health    — Health checks
  /memoria   — Buscar en memoria
  /proyecto  — Cambiar proyecto activo
  /costos    — Consumo LLM
  /agentes   — Listar agentes
  /logs      — Últimos eventos
  (texto)    — Pregunta a JARVIS con IA
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from jarvis import __version__

log = logging.getLogger(__name__)

# Seguridad: solo usuarios autorizados
_ALLOWED_USERS: set[int] = set()
_allowed_raw = os.environ.get("TELEGRAM_ALLOWED_USERS", "")
if _allowed_raw:
    _ALLOWED_USERS = {int(uid.strip()) for uid in _allowed_raw.split(",") if uid.strip().isdigit()}

# Proyecto activo por usuario
_user_projects: dict[int, str] = {}


def _is_authorized(update: Update) -> bool:
    """Verificar si el usuario está autorizado. Si no hay allowlist, acepta a todos."""
    if not _ALLOWED_USERS:
        return True  # Sin restricciones configuradas
    return update.effective_user and update.effective_user.id in _ALLOWED_USERS


def _get_project(user_id: int) -> str:
    return _user_projects.get(user_id, "personal")


async def _unauthorized(update: Update):
    user = update.effective_user
    log.warning("Unauthorized access attempt from user %s (%s)", user.id, user.username)
    await update.message.reply_text(
        f"No autorizado. Tu ID: {user.id}\n"
        "Agrega tu ID a TELEGRAM_ALLOWED_USERS en .env para habilitarte."
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return await _unauthorized(update)

    user = update.effective_user
    # Registrar el user ID para facilitar la configuración
    log.info("User started bot: %s (ID: %s)", user.username, user.id)

    await update.message.reply_text(
        f"Hola Nico. Soy JARVIS v{__version__}.\n\n"
        f"Tu user ID: {user.id}\n\n"
        "Comandos:\n"
        "/status — Estado del sistema\n"
        "/health — Health checks\n"
        "/memoria <texto> — Buscar en memoria\n"
        "/proyecto <id> — Cambiar proyecto\n"
        "/costos — Consumo LLM\n"
        "/agentes — Listar agentes\n"
        "/logs — Últimos eventos\n"
        "/docker status|up|down|logs — Docker KameCol\n\n"
        "O simplemente escribe tu pregunta."
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return await _unauthorized(update)

    from jarvis.config import list_projects, load_global_config
    from jarvis.core.events import EventStore
    from jarvis.memory.manager import MemoryManager
    from jarvis.memory.store import MemoryStore

    db = load_global_config().get("database", {}).get("path", "data/jarvis.db")
    store = EventStore(db_path=db)
    mem_store = MemoryStore(db_path=db)
    mgr = MemoryManager(store=mem_store, embeddings_enabled=False)

    projects = list_projects()
    events = store.count()
    memory = mgr.count()
    project = _get_project(update.effective_user.id)

    text = (
        f"JARVIS v{__version__}\n"
        f"Eventos: {events}\n"
        f"Memoria: {memory} registros\n"
        f"Proyectos: {', '.join(projects)}\n"
        f"Proyecto activo: {project}"
    )
    store.close()
    mgr.close()
    await update.message.reply_text(text)


async def cmd_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return await _unauthorized(update)

    from jarvis.config import load_global_config
    from jarvis.observability.health import check_all

    db = load_global_config().get("database", {}).get("path", "data/jarvis.db")
    checks = check_all(db_path=db)

    lines = ["Health Checks:"]
    for c in checks:
        icon = "✅" if c.healthy else "❌"
        lines.append(f"{icon} {c.component}: {c.detail}")

    await update.message.reply_text("\n".join(lines))


async def cmd_memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return await _unauthorized(update)

    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Uso: /memoria <texto a buscar>")
        return

    from jarvis.config import load_global_config
    from jarvis.memory.manager import MemoryManager
    from jarvis.memory.store import MemoryStore

    db = load_global_config().get("database", {}).get("path", "data/jarvis.db")
    project = _get_project(update.effective_user.id)
    mem_store = MemoryStore(db_path=db)
    mgr = MemoryManager(store=mem_store, embeddings_enabled=False)

    results = mgr.search(query, project=project, limit=5)
    mgr.close()

    if not results:
        await update.message.reply_text(f"Sin resultados para '{query}' en {project}.")
        return

    lines = [f"Memoria ({project}) — '{query}':"]
    for rec, score in results:
        lines.append(f"• [{rec.source}] {rec.content[:150]}")

    await update.message.reply_text("\n".join(lines))


async def cmd_proyecto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return await _unauthorized(update)

    if not context.args:
        from jarvis.config import list_projects
        projects = list_projects()
        current = _get_project(update.effective_user.id)
        await update.message.reply_text(
            f"Proyecto actual: {current}\nDisponibles: {', '.join(projects)}\n\n"
            "Uso: /proyecto <id>"
        )
        return

    new_project = context.args[0].strip()
    _user_projects[update.effective_user.id] = new_project
    await update.message.reply_text(f"Proyecto cambiado a: {new_project}")


async def cmd_costos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return await _unauthorized(update)

    from jarvis.config import load_global_config
    from jarvis.llm.usage import UsageTracker

    db = load_global_config().get("database", {}).get("path", "data/jarvis.db")
    tracker = UsageTracker(db_path=db)
    summary = tracker.get_summary(days=7)
    total = tracker.get_total_cost(days=7)
    tracker.close()

    if not summary:
        await update.message.reply_text("Sin uso de LLM en los últimos 7 días.")
        return

    lines = ["Costos LLM (7 días):"]
    for row in summary:
        lines.append(f"• {row['provider']}: {row['requests']} req, {row['tokens']:,} tokens, ${row['cost_usd']:.4f}")
    lines.append(f"\nTotal: ${total:.4f}")

    await update.message.reply_text("\n".join(lines))


async def cmd_agentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return await _unauthorized(update)

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

    lines = ["Agentes JARVIS:"]
    for s in registry.list_all():
        projects = ", ".join(s.supported_projects) if s.supported_projects else "todos"
        lines.append(f"• {s.name} ({s.id}) — {projects}")

    await update.message.reply_text("\n".join(lines))


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_authorized(update):
        return await _unauthorized(update)

    from jarvis.config import load_global_config
    from jarvis.core.events import EventStore

    db = load_global_config().get("database", {}).get("path", "data/jarvis.db")
    store = EventStore(db_path=db)
    events = store.query(limit=5)
    store.close()

    if not events:
        await update.message.reply_text("Sin eventos.")
        return

    lines = ["Últimos 5 eventos:"]
    for e in events:
        ts = e.timestamp.strftime("%H:%M:%S")
        detail = ""
        if "command" in e.payload:
            detail = f"{e.payload['command']}"
        elif "response" in e.payload:
            detail = e.payload["response"][:60]
        lines.append(f"[{ts}] {e.event_type.value} | {e.project or '—'} | {detail}")

    await update.message.reply_text("\n".join(lines))


async def cmd_docker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionar Docker de KameCol desde Telegram."""
    if not _is_authorized(update):
        return await _unauthorized(update)

    import subprocess

    action = context.args[0] if context.args else "status"
    kamecol_path = os.path.expanduser("~/Developer/Personal/kame.colStore")

    if action == "status":
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout.strip():
                lines = ["🐳 Contenedores activos:"]
                for line in result.stdout.strip().split("\n"):
                    parts = line.split("\t")
                    name = parts[0] if parts else "?"
                    status = parts[1] if len(parts) > 1 else "?"
                    lines.append(f"• {name}: {status}")
                await update.message.reply_text("\n".join(lines))
            else:
                await update.message.reply_text("🐳 Sin contenedores activos.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    elif action == "up":
        await update.message.reply_text("🐳 Levantando KameCol...")
        try:
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=kamecol_path, capture_output=True, text=True, timeout=60,
            )
            output = result.stdout + result.stderr
            await update.message.reply_text(f"🐳 KameCol:\n{output[-500:]}")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    elif action == "down":
        await update.message.reply_text("🐳 Deteniendo KameCol...")
        try:
            result = subprocess.run(
                ["docker", "compose", "down"],
                cwd=kamecol_path, capture_output=True, text=True, timeout=30,
            )
            await update.message.reply_text(f"🐳 KameCol detenido.\n{result.stdout[-300:]}")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    elif action == "logs":
        try:
            result = subprocess.run(
                ["docker", "compose", "logs", "--tail=15"],
                cwd=kamecol_path, capture_output=True, text=True, timeout=10,
            )
            logs = result.stdout[-1500:] if result.stdout else "Sin logs."
            await update.message.reply_text(f"🐳 Logs:\n{logs}")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    elif action == "restart":
        await update.message.reply_text("🐳 Reiniciando KameCol...")
        try:
            subprocess.run(["docker", "compose", "down"], cwd=kamecol_path, capture_output=True, timeout=30)
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=kamecol_path, capture_output=True, text=True, timeout=60,
            )
            await update.message.reply_text(f"🐳 KameCol reiniciado.\n{result.stdout[-300:]}")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    else:
        await update.message.reply_text(
            "🐳 Comandos Docker:\n"
            "/docker status — Ver contenedores\n"
            "/docker up — Levantar KameCol\n"
            "/docker down — Detener KameCol\n"
            "/docker restart — Reiniciar\n"
            "/docker logs — Ver logs"
        )


# Historial conversacional por usuario (últimos N mensajes)
_user_history: dict[int, list[dict]] = {}
_MAX_HISTORY = 8  # Últimos 4 intercambios


def _get_repo_context(text: str, project: str) -> str:
    """Detectar si la pregunta necesita datos del repo y obtenerlos."""
    import re

    text_lower = text.lower()
    repo_keywords = ("commit", "código", "code", "archivo", "file", "rama", "branch",
                     "repo", "repositorio", "último cambio", "git", "push", "merge",
                     "estructura", "modelo", "model", "endpoint", "url", "api")

    if not any(kw in text_lower for kw in repo_keywords):
        return ""

    try:
        from jarvis.integrations.repo_reader import get_reader

        # Mapear proyecto a repo
        repo_map = {"kamecol": "kamecol", "iaagent": "iaagent", "personal": "jarvis",
                     "integratepie": None}  # No tenemos acceso al repo de PIE
        repo_id = repo_map.get(project)
        if not repo_id:
            return ""

        reader = get_reader(repo_id)
        if not reader or not reader.exists:
            return ""

        context_parts = []

        # Si pide commits/cambios
        if any(kw in text_lower for kw in ("commit", "cambio", "push", "merge", "último", "log", "git")):
            commits = reader.get_git_log(limit=5)
            if commits:
                lines = ["Últimos commits del repo:"]
                for c in commits:
                    lines.append(f"  {c['hash']} ({c['date']}) {c['message']}")
                context_parts.append("\n".join(lines))

        # Si pide estructura
        if any(kw in text_lower for kw in ("estructura", "directorio", "carpeta", "folder", "árbol")):
            structure = reader.get_structure(max_depth=2)
            if structure:
                context_parts.append("Estructura del repo:\n" + "\n".join(structure[:30]))

        # Si pide buscar código
        code_search = re.search(r"(?:busca|encuentra|dónde está|class |def |function )\s*(\w+)", text_lower)
        if code_search:
            pattern = code_search.group(1)
            results = reader.search_code(pattern, max_results=5)
            if results:
                lines = [f"Resultados de búsqueda '{pattern}':"]
                for r in results:
                    lines.append(f"  {r['file']}:{r['line']} — {r['content'][:100]}")
                context_parts.append("\n".join(lines))

        return "\n\n".join(context_parts) if context_parts else ""

    except Exception as e:
        log.warning("Repo context error: %s", e)
        return ""


def _get_api_context(text: str, project: str) -> str:
    """Detectar si la pregunta necesita datos de APIs reales y obtenerlos."""
    if project != "kamecol":
        return ""

    text_lower = text.lower()
    try:
        return _fetch_kamecol_data(text_lower)
    except Exception as e:
        log.warning("API context error: %s", e)
        return ""


def _fetch_kamecol_data(text_lower: str) -> str:
    api_keywords = ("producto", "product", "catálogo", "catalogo", "tienda", "precio",
                    "talla", "stock", "departamento", "categoría", "categoria",
                    "pedido", "orden", "order", "venta", "inventario",
                    "cuántos", "cuantos", "lista", "muestra", "dime")

    if not any(kw in text_lower for kw in api_keywords):
        return ""

    from jarvis.integrations.kamecol import KameColPublicClient

    client = KameColPublicClient()
    if not client.is_configured:
        return ""

    context_parts = []

    # Productos / catálogo
    if any(kw in text_lower for kw in ("producto", "product", "catálogo", "catalogo",
                                        "tienda", "cuántos", "cuantos", "precio", "stock")):
        products = client.get_products(limit=50)
        if products:
            lines = [f"Catálogo KameCol ({len(products)} productos):"]
            for p in products[:15]:
                price = f"${p.price:,.0f}"
                if p.discount_price:
                    price = f"${p.discount_price:,.0f} (antes ${p.price:,.0f})"
                stock_txt = "✅" if p.in_stock else "❌"
                lines.append(f"  {stock_txt} {p.name} — {price} COP [{p.category}]")
            if len(products) > 15:
                lines.append(f"  ... y {len(products) - 15} más")
            context_parts.append("\n".join(lines))

    # Departamentos / categorías
    if any(kw in text_lower for kw in ("departamento", "categoría", "categoria", "navegación")):
        nav = client.get_navigation()
        if nav:
            lines = ["Departamentos y categorías:"]
            for dept in nav:
                name = dept.get("name", "?")
                cats = dept.get("categories", [])
                cat_names = ", ".join(c.get("name", "") for c in cats) if cats else "—"
                lines.append(f"  {name}: {cat_names}")
            context_parts.append("\n".join(lines))

    # Estado de pedido
    if any(kw in text_lower for kw in ("pedido", "orden", "order", "tracking")):
        import re
        ref_match = re.search(r"[A-Z0-9]{6,}", text_lower.upper())
        if ref_match:
            status = client.get_order_status(ref_match.group())
            if status:
                context_parts.append(
                    f"Pedido {status.reference}: estado={status.status}, "
                    f"total=${status.total:,.0f} COP"
                )

    return "\n\n".join(context_parts) if context_parts else ""


def _get_db_context(text: str, project: str) -> str:
    """Consultar la DB de PRODUCCIÓN. Se activa siempre para proyecto kamecol."""
    if project != "kamecol":
        return ""

    try:
        from jarvis.integrations.kamecol_db import KameColDB
        db = KameColDB()
        if not db.is_configured:
            return ""

        parts = []

        # Siempre incluir resumen base de producción
        summary = db.get_orders_summary(30)
        parts.append(
            f"[DATOS PRODUCCIÓN] KameCol (30 días): {summary['total_orders']} órdenes, "
            f"${summary['total_revenue']:,.0f} COP. "
            f"Clientes: {db.get_customers_count()}. Productos: {db.get_product_count()}. "
            "Estado: " + ", ".join(f"{k}={v['count']}" for k, v in summary["by_status"].items())
        )

        # Últimas órdenes siempre visibles
        orders = db.get_recent_orders(5)
        if orders:
            lines = []
            for o in orders:
                lines.append(
                    f"{o['payment_reference']} — {o['status']} — "
                    f"${float(o['total']):,.0f} COP — {o['payment_method'] or '?'} — "
                    f"{str(o['created_at'])[:10]}"
                )
            parts.append("Últimas órdenes:\n" + "\n".join(lines))

        # Top productos
        top = db.get_top_products(90, 5)
        if top:
            lines = [f"{p['name']}: {p['units_sold']}u — ${float(p['revenue']):,.0f}" for p in top]
            parts.append("Top productos (90d): " + "; ".join(lines))

        # Stock bajo
        text_lower = text.lower()
        if any(kw in text_lower for kw in ("stock", "inventario", "agotado", "talla")):
            low = db.get_inventory_low(3)
            if low:
                lines = [f"{i['category']} {i['variant']} {i['color']}: {i['quantity']}u" for i in low[:8]]
                parts.append("Stock bajo: " + "; ".join(lines))

        # Funnel
        if any(kw in text_lower for kw in ("funnel", "conversión", "visita", "analítica")):
            funnel = db.get_funnel_stats(30)
            if funnel:
                lines = [f"{f['event']}={f['count']}" for f in funnel]
                parts.append("Funnel (30d): " + ", ".join(lines))

        return "\n".join(parts) if parts else ""

    except Exception as e:
        log.warning("DB context error: %s", e)
        return ""


# Mapeo de proyecto a directorio de trabajo para Claude Code
_PROJECT_DIRS: dict[str, str] = {
    "kamecol": os.path.expanduser("~/Developer/Personal/kame.colStore"),
    "iaagent": os.path.expanduser("~/Developer/Personal/IaAgent"),
    "jarvis": os.path.expanduser("~/Developer/Personal/jarvis"),
    "personal": os.path.expanduser("~/Developer/Personal/jarvis"),
}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecutar Claude Code CLI con el mensaje — misma potencia que la terminal."""
    if not _is_authorized(update):
        return await _unauthorized(update)

    text = update.message.text
    if not text:
        return

    user_id = update.effective_user.id
    project = _get_project(user_id)
    cwd = _PROJECT_DIRS.get(project, _PROJECT_DIRS["personal"])

    await update.message.reply_chat_action("typing")

    try:
        import shutil
        import subprocess
        import time

        cli = shutil.which("claude")
        if not cli:
            await update.message.reply_text("Claude Code CLI no encontrado en el sistema.")
            return

        # Construir prompt con contexto de proyecto
        prompt = (
            f"Responde BREVE en español (máximo 4 oraciones). "
            f"Proyecto actual: {project}. Directorio: {cwd}. "
            f"La DB de KameCol es PostgreSQL (KAMECOL_DATABASE_URL en env). "
            f"NO uses MySQL. Usa psql o python con psycopg2 si necesitas consultar la DB. "
            f"Pregunta: {text}"
        )

        start = time.monotonic()
        result = subprocess.run(
            [cli, "-p", prompt, "--max-turns", "10",
             "--dangerously-skip-permissions"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120,
            env={**os.environ, "TERM": "dumb"},
        )
        elapsed = int((time.monotonic() - start) * 1000)

        if result.returncode != 0 and not result.stdout:
            error = result.stderr[:300] if result.stderr else "Error desconocido"
            await update.message.reply_text(f"Error Claude: {error}")
            return

        reply = result.stdout.strip()
        if not reply:
            reply = "Sin respuesta de Claude Code."

        # Truncar si es muy largo para Telegram (límite 4096 chars)
        if len(reply) > 3800:
            reply = reply[:3800] + "\n\n... (respuesta truncada)"

        footer = f"\n\n_claude-code · {elapsed}ms_"
        try:
            await update.message.reply_text(reply + footer, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply + footer)

        # Guardar en historial
        if user_id not in _user_history:
            _user_history[user_id] = []
        _user_history[user_id].append({"user": text, "assistant": reply[:200]})
        if len(_user_history[user_id]) > _MAX_HISTORY:
            _user_history[user_id] = _user_history[user_id][-_MAX_HISTORY:]

    except subprocess.TimeoutExpired:
        await update.message.reply_text("Timeout — Claude tardó más de 2 minutos.")
    except Exception as e:
        log.error("Claude Code error: %s", e)
        await update.message.reply_text(f"Error: {e}")


def create_bot() -> Application:
    """Crear instancia del bot de Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN no configurado en .env")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("memoria", cmd_memoria))
    app.add_handler(CommandHandler("proyecto", cmd_proyecto))
    app.add_handler(CommandHandler("costos", cmd_costos))
    app.add_handler(CommandHandler("agentes", cmd_agentes))
    app.add_handler(CommandHandler("logs", cmd_logs))
    app.add_handler(CommandHandler("docker", cmd_docker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
