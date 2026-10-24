# JARVIS

**Plataforma personal de inteligencia artificial híbrida con agentes especializados, memoria persistente y ejecución verificable.**

## Visión

JARVIS es una plataforma modular que coordina agentes inteligentes para automatizar y asistir en tareas de desarrollo de software, QA, e-commerce y análisis de información. No es un chatbot: es un sistema operativo de agentes con capacidades reales, trazabilidad y control humano.

## Proyectos integrados

| Proyecto | Dominio | Stack | Integración |
|----------|---------|-------|-------------|
| **IntegratePIE** | Educación especial (Chile) | PHP/Laravel, MySQL, Azure | QA Intelligence, análisis de PRs |
| **IAAgent** | QA automatizado | Python, Typer, Azure DevOps | Módulo QA reutilizable |
| **KameCol** | E-commerce streetwear (Colombia) | Django/DRF, Next.js, PostgreSQL | Atención al cliente, automatización comercial |

## Arquitectura

```
USUARIO
   │
   ▼
JARVIS CLI / API (FastAPI)
   │
   ▼
JARVIS CORE
   ├── Router ──────── Clasifica y delega solicitudes
   ├── Memory ─────── Recupera contexto persistente
   └── Job Engine ──── Ejecuta tareas en background (Huey/SQLite)
         │
         ▼
   AGENT MANAGER
   ├── QA Agent ────── Análisis de PRs, test cases, evidencias
   ├── Dev Agent ───── Análisis de código, arquitectura
   └── Biz Agent ───── Atención al cliente, métricas comerciales
         │
         ▼
   TOOL LAYER
   ├── Azure DevOps ── Work items, PRs, pipelines
   ├── Playwright ──── Automatización de navegador
   ├── Git ─────────── Repositorios, diffs, análisis
   └── APIs ────────── KameCol, IntegratePIE (solo lectura)
         │
         ▼
   EVIDENCE & AUDIT ── Logs, resultados, capturas, trazabilidad
```

## Stack tecnológico

| Componente | Tecnología |
|-----------|-----------|
| Lenguaje | Python 3.12+ |
| API | FastAPI |
| Jobs | Huey (SQLite backend) |
| Persistencia | SQLite → PostgreSQL + pgvector |
| IA local | Ollama (Qwen 2.5, CodeQwen) |
| IA cloud | Gemini API (intercambiable, proveedor extensible) |
| QA | Playwright MCP |
| Tests | pytest |
| Interfaz | CLI + API REST (web posterior) |

## Estado del proyecto

**Fase actual: 1 — JARVIS Core** (en progreso)

- [x] Fase 0 — Investigación y arquitectura
- [x] Fase 1 — Core: CLI, Event Stream, Config, Security, Tests (53 tests, 97% cobertura)
- [ ] Fase 2 — Motor de IA híbrida (Ollama + Gemini)
- [ ] Fase 3 — Memoria persistente [MVP]

## Documentación

```
docs/
├── planning/
│   ├── MASTER-PLAN.md          # Plan maestro integral
│   ├── ROADMAP.md              # Fases de desarrollo
│   ├── BACKLOG.md              # Backlog técnico priorizado
│   └── MVP-SCOPE.md            # Alcance del MVP
├── architecture/
│   ├── SYSTEM-ARCHITECTURE.md  # Arquitectura del sistema
│   ├── AGENT-ARCHITECTURE.md   # Catálogo de agentes
│   ├── MEMORY-ARCHITECTURE.md  # Sistema de memoria persistente
│   ├── HYBRID-AI-ARCHITECTURE.md # Estrategia IA híbrida
│   ├── INTEGRATION-ARCHITECTURE.md # Integraciones externas
│   └── SECURITY-ARCHITECTURE.md    # Seguridad y aislamiento
├── research/
│   ├── GITHUB-REFERENCES.md        # Investigación de proyectos OSS
│   ├── IAAGENT-REUSE-ASSESSMENT.md # Evaluación de reutilización
│   └── AUDIT-CONSOLIDATION.md      # Análisis transversal de auditorías
├── decisions/
│   └── ADR-001-IAAGENT-STRATEGY.md # Decisión sobre IAAgent
└── execution/
    └── PHASE-01-IMPLEMENTATION-PLAN.md # Plan de la primera fase
```

## Auditorías base

- `docs/audits/integratepie-auditoria.md` — Auditoría técnica de IntegratePIE
- `docs/audits/iaAgent-auditoria.md` — Auditoría técnica de IAAgent
- `docs/audits/kame.colStore-auditoria.md` — Auditoría técnica de KameCol

## Quickstart

```bash
# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar JARVIS
pip install -e ".[dev]"

# Verificar
jarvis version
jarvis ask "hola"
jarvis status

# Tests
pytest tests/ -v
```

## Principios de diseño

1. **Modularidad** — Nuevos agentes y proyectos sin reconstruir el núcleo
2. **Independencia** — Cada proyecto conserva su propio repositorio
3. **IA híbrida** — Modelos locales + cloud + herramientas deterministas
4. **Memoria persistente** — Recuperar información sin repetir contexto
5. **Seguridad por defecto** — Permisos mínimos, aislamiento de proyectos
6. **Trazabilidad** — Cada ejecución genera evidencias verificables
7. **Control humano** — Aprobación requerida para operaciones con efectos externos

## Requisitos de infraestructura

- Mac mini Apple Silicon M4, 16 GB RAM
- macOS, Docker, Git
- Ollama para modelos locales
- Cursor, GPT Plus / Codex (herramientas de desarrollo)
- Python 3.12+ con entorno virtual

## Licencia

Proyecto personal. No distribuir sin autorización.
