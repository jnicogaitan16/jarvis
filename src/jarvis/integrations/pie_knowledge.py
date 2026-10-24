"""IntegratePIE Knowledge Base — conocimiento de reglas de negocio.

Extrae información clave de la auditoría para alimentar la memoria
semántica de JARVIS sobre IntegratePIE.
"""

from __future__ import annotations

from jarvis.core.models import MemoryType
from jarvis.memory.manager import MemoryManager

_PROJECT = "integratepie"
_SOURCE = "audit:integratepie"

# Conocimiento extraído de la auditoría (sin datos sensibles)
_KNOWLEDGE_ENTRIES = [
    {
        "content": "IntegratePIE es una plataforma SaaS multi-tenant para gestión del Programa de Integración Escolar (PIE) en Chile, regulada por el Decreto 170/2009 del MINEDUC.",
        "tags": ["overview", "regulacion"],
    },
    {
        "content": "Stack tecnológico: PHP 8.4, Laravel 8.83, MySQL utf8mb4, Vue.js 3, Bootstrap 3 + jQuery 3, Azure App Service.",
        "tags": ["stack", "tecnologia"],
    },
    {
        "content": "El sistema tiene ~174,000 líneas de código, 78 controladores, 46 servicios, 20 middleware, 368 migraciones de BD.",
        "tags": ["escala", "complejidad"],
    },
    {
        "content": "Existen 33 categorías de NEE (Necesidades Educativas Especiales): Transitorias (TDA/TDAH, TEL, DEA, FIL, ODF) y Permanentes (DA, DI, DIS, DV, DMultiple, DMotora, TEA, RGD, Síndrome Down, GArc).",
        "tags": ["nee", "diagnosticos", "negocio"],
    },
    {
        "content": "La cadena de formularios es: FUDEI (diagnóstico) → FUR (formulario único de registro) → PAI (plan de apoyo individual, 10 especialidades) → PACI (plan adecuación curricular). Un cambio en FUDEI tiene impacto en cascada.",
        "tags": ["formularios", "cadena", "negocio"],
    },
    {
        "content": "config/fur.php es el archivo más grande (186 KB) y contiene reglas de rollout, tipos FUR, importaciones y tracking HDU. Cualquier cambio tiene impacto sistémico.",
        "tags": ["config", "fur", "riesgo"],
    },
    {
        "content": "Rollout FUR 2026 funciona por fases usando módulo aritmético del RBD: Piloto → 25% → 50% → 85%. Controlado por PieHelper::furHdusHabilitadas().",
        "tags": ["rollout", "fur", "2026"],
    },
    {
        "content": "Regla GArc→TEA (FUR 2026): Estudiantes con diagnóstico GArc (pie_nee_id=33) reciben FUR tipo TEA (tipo 2) en vez de FUR Múltiple (tipo 3). Condiciones: año >= 2026, sin FUR Múltiple iniciado.",
        "tags": ["garc", "tea", "regla", "fur"],
    },
    {
        "content": "Máquina de estados de informes: NO_EMPEZADO(0) → EN_PROCESO(2) → TERMINADO(3) → APROBADO(8). También: SUBIDO_MINEDUC(4), ADJUNTADO(5), ERROR_SINCRONIZAR(7), REABRIR(9).",
        "tags": ["informes", "estados", "negocio"],
    },
    {
        "content": "Sistema de permisos PerPer: permisos almacenados como JSON en tabla perfil. Roles que firman documentos: Coordinador PIE(2), Coordinador Académico(53), UTP(41), Director(54).",
        "tags": ["permisos", "roles", "seguridad"],
    },
    {
        "content": "Multi-tenancy por campo *_rbd sin row-level security en MySQL. El aislamiento depende de que todos los queries incluyan WHERE *_rbd = $rbd.",
        "tags": ["multi-tenancy", "seguridad", "riesgo"],
    },
    {
        "content": "Tests: 643 métodos PHPUnit (43 archivos), 39 escenarios Nightwatch.js (12 archivos, 12 saltados). Playwright instalado pero sin tests escritos.",
        "tags": ["tests", "qa", "cobertura"],
    },
    {
        "content": "6 pipelines Azure DevOps: principal, QA, tests E2E, migration PR, producción, clone/backup. Tests con npm run test:headless (Nightwatch).",
        "tags": ["pipelines", "cicd", "azure"],
    },
    {
        "content": "PaiController tiene 201 KB — el controlador más grande del sistema con concentración excesiva de lógica.",
        "tags": ["deuda-tecnica", "controlador", "pai"],
    },
    {
        "content": "Criterios PAI: L (Logrado), L/A (Logrado con Ayuda), N/L (No Logrado), N/T (No Trabajado).",
        "tags": ["pai", "criterios", "negocio"],
    },
]


def seed_knowledge(manager: MemoryManager) -> int:
    """Cargar conocimiento de IntegratePIE en memoria.

    Retorna la cantidad de registros agregados. Salta los que ya existen.
    """
    existing = manager.search_by_project(_PROJECT, limit=100)
    existing_contents = {r.content[:80] for r in existing}

    added = 0
    for entry in _KNOWLEDGE_ENTRIES:
        # Evitar duplicados
        if entry["content"][:80] in existing_contents:
            continue

        manager.add(
            content=entry["content"],
            project=_PROJECT,
            source=_SOURCE,
            memory_type=MemoryType.PROJECT,
            confidence=0.9,
            tags=entry["tags"],
        )
        added += 1

    return added
