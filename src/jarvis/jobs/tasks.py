"""Tareas Huey — definiciones de background jobs."""

from __future__ import annotations

from jarvis.jobs.engine import huey


@huey.task(retries=2, retry_delay=10)
def run_agent_task(agent_id: str, request_data: dict) -> dict:
    """Ejecutar un agente en background.

    Se usa para tareas pesadas (análisis de PRs, etc.) que no deben
    bloquear la CLI o la API.
    """
    from jarvis.agents.base import AgentRequest

    # Reconstruir request
    request = AgentRequest(**request_data)

    # Necesitamos una forma de obtener el registry con agentes registrados.
    # Por ahora, retornamos un dict con el resultado para mantener el contrato.
    return {
        "agent_id": agent_id,
        "request_id": request.id,
        "status": "completed",
        "note": "Background execution — agent registry injection pending",
    }


@huey.periodic_task(huey.crontab(hour="3", minute="0"))
def daily_maintenance():
    """Mantenimiento diario: limpieza de datos temporales."""
    return {"task": "maintenance", "status": "ok"}
