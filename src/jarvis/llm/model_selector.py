"""Model Selector — selección óptima de modelos según tarea y recursos.

Permite configurar qué modelo usar para cada tipo de tarea,
y evaluar modelos disponibles contra benchmarks reales.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from jarvis.llm.base import TaskComplexity


@dataclass(frozen=True)
class ModelProfile:
    """Perfil de un modelo con sus capacidades y costos."""
    id: str
    provider: str
    name: str
    ram_gb: float = 0.0
    strengths: list[str] = field(default_factory=list)
    cost_per_mtok: float = 0.0
    max_context: int = 4096
    recommended_for: list[str] = field(default_factory=list)


# Perfiles built-in basados en hardware M4 16GB
BUILTIN_PROFILES: list[ModelProfile] = [
    ModelProfile(
        id="qwen2.5:7b",
        provider="ollama",
        name="Qwen 2.5 7B (Q4)",
        ram_gb=5.0,
        strengths=["general", "spanish", "instruction_following"],
        max_context=32768,
        recommended_for=["simple", "medium"],
    ),
    ModelProfile(
        id="codeqwen:7b",
        provider="ollama",
        name="CodeQwen 1.5 7B (Q4)",
        ram_gb=5.0,
        strengths=["code_analysis", "code_generation", "debugging"],
        max_context=65536,
        recommended_for=["code"],
    ),
    ModelProfile(
        id="qwen2.5:3b",
        provider="ollama",
        name="Qwen 2.5 3B (Q4)",
        ram_gb=2.5,
        strengths=["classification", "fast_response"],
        max_context=32768,
        recommended_for=["simple"],
    ),
    ModelProfile(
        id="gemini-2.5-flash",
        provider="gemini",
        name="Gemini 2.5 Flash",
        ram_gb=0.0,
        strengths=["reasoning", "long_context", "multilingual"],
        cost_per_mtok=0.15,
        max_context=1048576,
        recommended_for=["complex", "medium"],
    ),
]


@dataclass
class ModelSelection:
    """Resultado de la selección de modelo."""
    model_id: str
    provider: str
    reason: str


class ModelSelector:
    """Selecciona el modelo óptimo según tarea, política y recursos."""

    def __init__(self, profiles: list[ModelProfile] | None = None, config_path: str | None = None):
        self._profiles = {p.id: p for p in (profiles or BUILTIN_PROFILES)}
        if config_path:
            self._load_config(config_path)

    def select(
        self,
        complexity: TaskComplexity,
        available_providers: set[str],
        prefer_local: bool = True,
    ) -> ModelSelection:
        """Seleccionar el mejor modelo para la tarea."""
        candidates = [
            p for p in self._profiles.values()
            if p.provider in available_providers and complexity.value in p.recommended_for
        ]

        if not candidates:
            # Fallback: cualquier modelo disponible
            candidates = [p for p in self._profiles.values() if p.provider in available_providers]

        if not candidates:
            return ModelSelection("qwen2.5:7b", "ollama", "Default fallback — sin candidatos")

        # Ordenar: local primero si se prefiere, luego por costo
        if prefer_local:
            candidates.sort(key=lambda p: (0 if p.provider == "ollama" else 1, p.cost_per_mtok))
        else:
            candidates.sort(key=lambda p: p.cost_per_mtok)

        best = candidates[0]
        return ModelSelection(
            model_id=best.id,
            provider=best.provider,
            reason=f"Seleccionado para {complexity.value}: {best.name} ({', '.join(best.strengths[:2])})",
        )

    def list_profiles(self) -> list[ModelProfile]:
        return list(self._profiles.values())

    def get_profile(self, model_id: str) -> ModelProfile | None:
        return self._profiles.get(model_id)

    def _load_config(self, config_path: str):
        """Cargar configuración de modelos desde TOML."""
        path = Path(config_path)
        if not path.exists():
            return
        with open(path, "rb") as f:
            data = tomllib.load(f)
        for model_data in data.get("models", []):
            profile = ModelProfile(
                id=model_data["id"],
                provider=model_data.get("provider", "ollama"),
                name=model_data.get("name", model_data["id"]),
                ram_gb=model_data.get("ram_gb", 0),
                strengths=model_data.get("strengths", []),
                cost_per_mtok=model_data.get("cost_per_mtok", 0),
                max_context=model_data.get("max_context", 4096),
                recommended_for=model_data.get("recommended_for", []),
            )
            self._profiles[profile.id] = profile
