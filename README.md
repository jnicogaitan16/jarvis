# JARVIS

**Plataforma personal de IA con agentes QA profesionales, orquestación multi-agente y ejecución verificable.**

![CI](https://github.com/jnicogaitan16/jarvis/actions/workflows/ci.yml/badge.svg)

## Qué es JARVIS

JARVIS coordina agentes inteligentes para automatizar QA, análisis de código, e-commerce y gestión de proyectos. No es un chatbot: es un sistema de agentes con capacidades reales, pipelines compuestos y control humano.

## Agentes (7)

| Agente | ID | Capacidad |
|--------|----|-----------|
| **QA Writer** | `qa.writer` | Bug reports, preguntas a DEV, notificaciones al equipo, hallazgos de revisión |
| **Gherkin Generator** | `qa.gherkin` | Escenarios BDD completos: happy path, validaciones, errores, seguridad |
| **Test Strategy Planner** | `qa.strategy` | Planifica tipos de testing, evalúa si automatizar con ROI estimado |
| **Code Review Agent** | `qa.code_review` | Análisis estático: credenciales, eval, SQL injection, complejidad |
| **QA Analyzer** | `qa.analyzer` | Pipeline completo de análisis de PRs (via IAAgent) |
| **KameCol Agent** | `biz.kamecol` | Catálogo, pedidos, dashboard KPIs, recuperación de pagos |
| **Echo Agent** | `core.echo` | Fallback para solicitudes generales |

## Pipelines Multi-Agente (4)

| Pipeline | Pasos | Uso |
|----------|-------|-----|
| `full_qa_review` | 4 | Code review + Gherkin + Strategy + Writer |
| `feature_planning` | 2 | Gherkin + Strategy |
| `security_audit` | 2 | Code review + Writer |
| `bug_triage` | 3 | Writer + Code review + Strategy |

## Plugins (10)

| Plugin | Categoría | Estado |
|--------|-----------|--------|
| **Playwright MCP** | QA | Connected |
| **GitHub MCP** | DevOps | Connected |
| Claude Docs | Docs | Connected |
| Google Drive | Docs | Connected |
| Mixpanel | Analytics | Connected |
| mysql-qa | Database | Connected |
| mysql-prod | Database | Connected |
| Warp | General | Enabled |
| monday.com | General | Needs auth |
| Jam | QA | Needs auth |

## Proyectos integrados

| Proyecto | Dominio | Integración |
|----------|---------|-------------|
| **IntegratePIE** | Educación especial (Chile) | QA Intelligence, análisis de PRs, Azure DevOps |
| **IAAgent** | QA automatizado | Motor de análisis de PRs reutilizable |
| **KameCol** | E-commerce streetwear (Colombia) | API, DB producción, dashboard KPIs |

## Quickstart

```bash
# Instalar
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verificar
jarvis version
jarvis status
jarvis agents

# Usar agentes
jarvis run "escribe un bug report: el login falla con contraseña vacía"
jarvis run "gherkin para el checkout de pagos"
jarvis run "estrategia de testing para el API de órdenes"
jarvis run "code review: api_key = 'secret123'"

# Pipelines
jarvis pipeline list
jarvis pipeline run feature_planning "login con email y contraseña"
jarvis pipeline run full_qa_review "endpoint API de pagos"

# Plugins
jarvis plugins scan
jarvis plugins health

# Tests
make test
make lint
```

## Makefile

```bash
make install    # Crear venv + instalar deps
make lint       # Ruff linter
make test       # pytest (331 tests)
make test-cov   # pytest + coverage
make serve      # Web dashboard (localhost:8000)
make plugins    # Escanear plugins
make build      # Docker build
make up         # Docker compose up
```

## Arquitectura

```
CLI / Web Dashboard (FastAPI)
        |
   Orchestrator --> Intent Detection --> Agent Registry
        |
   PipelineEngine --> Step 1 --> Step 2 --> Step N
        |                (contexto compartido)
   7 Agentes (QA Writer, Gherkin, Strategy, Code Review, QA Analyzer, KameCol, Echo)
        |
   Plugin Guardian --> 10 MCP Servers (Playwright, GitHub, MySQL, Mixpanel, ...)
        |
   Memory (SQLite + FTS5) | Events (append-only) | LLM Router (Ollama/Gemini/Claude)
```

## CI/CD

- **GitHub Actions**: lint (ruff) + tests (pytest) + coverage en push/PR a main
- **Docker**: Dockerfile + docker-compose para deploy containerizado
- **Linting**: ruff con reglas de seguridad (bandit), naming, imports, bugbear

## Stack

| Componente | Tecnología |
|-----------|-----------|
| Lenguaje | Python 3.12+ |
| CLI | Typer + Rich |
| API | FastAPI + Uvicorn |
| Testing | pytest (331 tests, 63% coverage) |
| Linting | ruff |
| CI/CD | GitHub Actions |
| Container | Docker |
| Base de datos | SQLite (FTS5) |
| MCP Servers | Playwright, GitHub, MySQL, Mixpanel, Google Drive, Claude Docs |

## Infraestructura

- Mac mini Apple Silicon M4, 16 GB RAM
- Claude Code como motor principal
- Acceso remoto: Tailscale + SSH desde iPhone

## Licencia

Proyecto personal. No distribuir sin autorización.
