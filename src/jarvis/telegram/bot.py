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
        "/logs — Últimos eventos\n\n"
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de texto — pregunta a JARVIS con IA + repos + memoria."""
    if not _is_authorized(update):
        return await _unauthorized(update)

    text = update.message.text
    if not text:
        return

    user_id = update.effective_user.id
    project = _get_project(user_id)

    await update.message.reply_chat_action("typing")

    try:
        from jarvis.config import load_global_config, load_project_context
        from jarvis.core.events import EventStore
        from jarvis.core.models import EventType
        from jarvis.llm.base import LLMRequest
        from jarvis.llm.gemini import GeminiProvider
        from jarvis.llm.ollama import OllamaProvider
        from jarvis.llm.router import LLMRouter
        from jarvis.llm.usage import UsageTracker
        from jarvis.memory.manager import MemoryManager
        from jarvis.memory.store import MemoryStore

        db = load_global_config().get("database", {}).get("path", "data/jarvis.db")
        ctx = load_project_context(project)

        # 1. Contexto de memoria
        mem_store = MemoryStore(db_path=db)
        mgr = MemoryManager(store=mem_store, embeddings_enabled=False)
        memory_context = mgr.get_context_for_prompt(text, project=project)
        mgr.close()

        # 2. Contexto del repo (si la pregunta lo necesita)
        repo_context = _get_repo_context(text, project)

        # 3. Historial conversacional
        history = _user_history.get(user_id, [])
        conversation = ""
        for msg in history[-_MAX_HISTORY:]:
            conversation += f"Nico: {msg['user']}\nJARVIS: {msg['assistant']}\n\n"

        # 4. System prompt enriquecido
        system_prompt = (
            "Eres JARVIS, el asistente personal de Nico Gaitán. "
            "Responde de forma directa, concisa y en español. "
            "Si tienes datos concretos (commits, código, memoria), úsalos. "
            "Si NO tienes la información, di que no la tienes — NUNCA inventes datos. "
            f"Proyecto actual: {ctx.display_name}."
        )
        if memory_context:
            system_prompt += f"\n\n{memory_context}"
        if repo_context:
            system_prompt += f"\n\nDatos reales del repositorio:\n{repo_context}"

        prompt = conversation + f"Nico: {text}\nJARVIS:" if conversation else text

        # 5. LLM
        tracker = UsageTracker(db_path=db)
        router = LLMRouter(usage_tracker=tracker)
        router.register(OllamaProvider())
        gemini = GeminiProvider()
        if gemini.is_available():
            router.register(gemini)

        request = LLMRequest(prompt=prompt, system=system_prompt, project=project)
        response = router.generate(request, ctx)

        # 6. Guardar en historial
        if user_id not in _user_history:
            _user_history[user_id] = []
        _user_history[user_id].append({"user": text, "assistant": response.content})
        if len(_user_history[user_id]) > _MAX_HISTORY:
            _user_history[user_id] = _user_history[user_id][-_MAX_HISTORY:]

        # 7. Event log
        store = EventStore(db_path=db)
        store.emit(EventType.ACTION, {"command": "telegram", "message": text}, project=project)
        store.emit(
            EventType.OBSERVATION,
            {"response": response.content[:200], "provider": response.provider, "tokens": response.total_tokens},
            project=project,
        )
        store.close()
        tracker.close()

        # 8. Responder
        reply = response.content
        footer = f"\n\n_{response.provider}:{response.model} · {response.total_tokens} tok · {response.latency_ms}ms_"
        # Telegram Markdown puede fallar con caracteres especiales
        try:
            await update.message.reply_text(reply + footer, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(reply + footer)

    except Exception as e:
        log.error("Telegram message error: %s", e)
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
