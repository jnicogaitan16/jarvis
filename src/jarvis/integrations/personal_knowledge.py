"""Personal Knowledge — perfil del usuario y conocimiento personal."""

from __future__ import annotations

from jarvis.core.models import MemoryType
from jarvis.memory.manager import MemoryManager

_PROJECT = "personal"
_SOURCE = "user:profile"

_PROFILE_ENTRIES = [
    {
        "content": "El usuario es Nico Gaitán. Profesional de QA y desarrollo de software. Prefiere comunicación directa, práctica y sin rodeos. Trato informal pero profesional.",
        "tags": ["perfil", "nombre", "comunicacion"],
        "type": MemoryType.SEMANTIC,
    },
    {
        "content": "Nico trabaja como QA en una empresa que usa IntegratePIE (plataforma educativa en Chile). La cuenta Claude Max es empresarial y compartida. IAAgent es un proyecto propio usado en contexto laboral.",
        "tags": ["trabajo", "rol", "empresa"],
        "type": MemoryType.SEMANTIC,
    },
    {
        "content": "KameCol es el proyecto personal de Nico — tienda de streetwear colombiana. Tiene libertad total sobre este proyecto. Es el espacio seguro para experimentar con JARVIS.",
        "tags": ["kamecol", "personal", "proyecto"],
        "type": MemoryType.SEMANTIC,
    },
    {
        "content": "Infraestructura de Nico: Mac mini M4 16GB RAM, Cursor (personal), GPT Plus/Codex (personal), Claude Code via Claude Max (empresarial). Docker instalado. Ollama con Qwen 2.5 7B.",
        "tags": ["infraestructura", "hardware", "herramientas"],
        "type": MemoryType.SEMANTIC,
    },
    {
        "content": "Nico gestiona 3 proyectos: IntegratePIE (QA empresarial, PHP/Laravel), IAAgent (agente QA propio, Python), KameCol (e-commerce personal, Django/Next.js). JARVIS los conecta todos.",
        "tags": ["proyectos", "overview"],
        "type": MemoryType.SEMANTIC,
    },
    {
        "content": "Preferencias de Nico: código pragmático sobre perfecto, MVP antes de expandir, reutilizar antes de reconstruir, español con términos técnicos en inglés, no le gustan los rodeos.",
        "tags": ["preferencias", "estilo"],
        "type": MemoryType.SEMANTIC,
    },
]


def seed_profile(manager: MemoryManager) -> int:
    """Cargar perfil del usuario en memoria."""
    existing = manager.search_by_project(_PROJECT, limit=100)
    existing_contents = {r.content[:80] for r in existing}

    added = 0
    for entry in _PROFILE_ENTRIES:
        if entry["content"][:80] in existing_contents:
            continue
        manager.add(
            content=entry["content"],
            project=_PROJECT,
            source=_SOURCE,
            memory_type=entry.get("type", MemoryType.SEMANTIC),
            confidence=1.0,
            tags=entry["tags"],
        )
        added += 1
    return added
