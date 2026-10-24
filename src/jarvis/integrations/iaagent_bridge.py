"""IAAgent Bridge — importa componentes de IAAgent como módulos de JARVIS.

Este bridge permite reutilizar los analyzers, generators y modelos de IAAgent
sin copiar código. IAAgent se importa dinámicamente desde su ruta local.

Configuración: IAAGENT_PATH en .env o config/jarvis.toml
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

_IAAGENT_PATH = os.environ.get(
    "IAAGENT_PATH",
    str(Path.home() / "Developer" / "Personal" / "IaAgent"),
)

_loaded = False


def _ensure_importable() -> bool:
    """Agregar IAAgent al sys.path si no está ya."""
    global _loaded
    if _loaded:
        return True

    path = Path(_IAAGENT_PATH)
    if not path.exists():
        return False

    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

    _loaded = True
    return True


def is_available() -> bool:
    """Verificar si IAAgent está disponible."""
    return _ensure_importable()


def _import(module_path: str) -> Any:
    """Importar un módulo de IAAgent."""
    if not _ensure_importable():
        raise RuntimeError(f"IAAgent no encontrado en {_IAAGENT_PATH}")
    return importlib.import_module(module_path)


# ---------------------------------------------------------------------------
# Lazy imports — se resuelven al primer acceso
# ---------------------------------------------------------------------------

def get_diff_analyzer():
    """Obtener módulo agent.analyzers.diff_analyzer."""
    return _import("agent.analyzers.diff_analyzer")


def get_security_analyzer():
    """Obtener módulo agent.analyzers.security_analyzer."""
    return _import("agent.analyzers.security_analyzer")


def get_static_analyzer():
    """Obtener módulo agent.analyzers.static_analyzer."""
    return _import("agent.analyzers.static_analyzer")


def get_dependency_analyzer():
    """Obtener módulo agent.analyzers.dependency_analyzer."""
    return _import("agent.analyzers.dependency_analyzer")


def get_impact_analyzer():
    """Obtener módulo agent.analyzers.impact_analyzer."""
    return _import("agent.analyzers.impact_analyzer")


def get_risk_engine():
    """Obtener módulo agent.analyzers.risk_engine."""
    return _import("agent.analyzers.risk_engine")


def get_test_case_generator():
    """Obtener módulo agent.generators.test_case_generator."""
    return _import("agent.generators.test_case_generator")


def get_report_generator():
    """Obtener módulo agent.generators.report_generator."""
    return _import("agent.generators.report_generator")


def get_comment_generator():
    """Obtener módulo agent.generators.comment_generator."""
    return _import("agent.generators.comment_generator")


def get_pr_context_models():
    """Obtener módulo agent.models.pr_context."""
    return _import("agent.models.pr_context")


def get_analysis_models():
    """Obtener módulo agent.models.analysis."""
    return _import("agent.models.analysis")


def get_azure_devops_client():
    """Obtener módulo agent.azure_devops."""
    return _import("agent.azure_devops")


def get_sanitizer():
    """Obtener módulo agent.sanitize."""
    return _import("agent.sanitize")
