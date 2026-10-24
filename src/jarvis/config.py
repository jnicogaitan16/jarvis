"""Sistema de configuración de JARVIS — TOML + env vars."""

from __future__ import annotations

import tomllib
from pathlib import Path

from dotenv import load_dotenv

from jarvis.core.models import ProjectContext

load_dotenv()

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_PROJECTS_DIR = _CONFIG_DIR / "projects"


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_global_config() -> dict:
    """Cargar configuración global desde config/jarvis.toml."""
    return _load_toml(_CONFIG_DIR / "jarvis.toml")


def load_project_context(project_id: str) -> ProjectContext:
    """Cargar contexto de proyecto desde config/projects/{id}.toml."""
    data = _load_toml(_PROJECTS_DIR / f"{project_id}.toml")

    project_section = data.get("project", {})
    ai_policy = data.get("ai_policy", {})
    privacy = data.get("privacy", {})
    perms = data.get("permissions", {})

    return ProjectContext(
        project_id=project_id,
        display_name=project_section.get("name", project_id),
        allowed_providers=frozenset(ai_policy.get("allowed_providers", ["ollama"])),
        allow_cloud=ai_policy.get("allow_cloud", False),
        allow_pii_to_cloud=privacy.get("allow_pii_to_cloud", False),
        sensitive_patterns=frozenset(privacy.get("sensitive_patterns", [])),
        allowed_tools=frozenset(perms.get("allowed_tools", [])),
        autonomy_level=ai_policy.get("autonomy_level", 0),
    )


def list_projects() -> list[str]:
    """Listar IDs de proyectos configurados."""
    if not _PROJECTS_DIR.exists():
        return []
    return sorted(
        p.stem for p in _PROJECTS_DIR.glob("*.toml")
    )
