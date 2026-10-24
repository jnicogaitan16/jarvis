"""Health Checks — verificar estado de todos los componentes del sistema."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HealthCheck:
    component: str
    healthy: bool
    detail: str = ""


def check_all(db_path: str = "data/jarvis.db") -> list[HealthCheck]:
    """Ejecutar todos los health checks."""
    checks = [
        _check_sqlite(db_path),
        _check_ollama(),
        _check_gemini(),
        _check_iaagent(),
        _check_kamecol(),
        _check_memory(db_path),
    ]
    return checks


def _check_sqlite(db_path: str) -> HealthCheck:
    try:
        if not Path(db_path).exists():
            return HealthCheck("SQLite", True, "DB se creará al primer uso")
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT 1")
        conn.close()
        return HealthCheck("SQLite", True, db_path)
    except Exception as e:
        return HealthCheck("SQLite", False, str(e))


def _check_ollama() -> HealthCheck:
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return HealthCheck("Ollama", True, f"{len(models)} modelos: {', '.join(models[:3])}")
        return HealthCheck("Ollama", False, f"Status {resp.status_code}")
    except Exception:
        return HealthCheck("Ollama", False, "No accesible (localhost:11434)")


def _check_gemini() -> HealthCheck:
    import os
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return HealthCheck("Gemini API", True, "API key configurada")
    return HealthCheck("Gemini API", False, "GEMINI_API_KEY no configurada")


def _check_iaagent() -> HealthCheck:
    try:
        from jarvis.integrations.iaagent_bridge import is_available
        if is_available():
            from jarvis.integrations.iaagent_bridge import get_diff_analyzer
            get_diff_analyzer()  # Verify import works
            return HealthCheck("IAAgent", True, "Bridge funcional")
        return HealthCheck("IAAgent", False, "No encontrado")
    except Exception as e:
        return HealthCheck("IAAgent", False, str(e))


def _check_kamecol() -> HealthCheck:
    import os
    url = os.environ.get("KAMECOL_API_URL", "")
    if not url:
        return HealthCheck("KameCol", False, "KAMECOL_API_URL no configurada")
    try:
        import httpx
        resp = httpx.get(f"{url}/api/health/", timeout=5)
        if resp.status_code == 200:
            return HealthCheck("KameCol", True, url)
        return HealthCheck("KameCol", False, f"Status {resp.status_code}")
    except Exception:
        return HealthCheck("KameCol", False, f"No accesible ({url})")


def _check_memory(db_path: str) -> HealthCheck:
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT COUNT(*) FROM memory WHERE status = 'active'").fetchone()
        conn.close()
        count = row[0] if row else 0
        return HealthCheck("Memoria", True, f"{count} registros activos")
    except sqlite3.OperationalError:
        return HealthCheck("Memoria", True, "Sin registros aún")
    except Exception as e:
        return HealthCheck("Memoria", False, str(e))
