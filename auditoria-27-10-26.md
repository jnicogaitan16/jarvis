# Auditoría Completa de JARVIS — 27 de Octubre 2026

## Estado Actual

- **Versión:** 0.1.0
- **Commits:** 16
- **Desarrollo:** 3 días (Oct 24-26, 2026)
- **Código fuente:** ~7,887 líneas en 60 archivos Python
- **Tests:** ~2,528 líneas en 23 archivos (~170+ tests)
- **Autor:** Juan Nicolás Gaitán Quimbay (único contribuidor)
- **Plataforma:** Mac mini Apple Silicon M4, 16 GB RAM
- **Python:** 3.12+
- **Build system:** Hatchling

---

## Estructura Completa del Proyecto

```
/Users/nicogaitan/Developer/Personal/jarvis/
├── .claude/settings.local.json    -- Permisos Claude Code
├── .coverage                      -- Datos de cobertura pytest
├── .env                           -- SECRETOS EN VIVO (ver sección seguridad)
├── .env.example                   -- Template de variables de entorno
├── .gitignore
├── .pytest_cache/
├── .venv/                         -- Entorno virtual Python
├── README.md
├── pyproject.toml                 -- Config del paquete + dependencias
├── config/
│   ├── jarvis.toml                -- Configuración global
│   ├── models.toml                -- Budget/preferencias LLM
│   └── projects/
│       ├── integratepie.toml      -- Config IntegratePIE
│       ├── kamecol.toml           -- Config KameCol
│       └── personal.toml          -- Config Personal
├── data/
│   ├── jarvis.db                  -- SQLite base de datos principal
│   └── evidence/                  -- Archivos de evidencia PR
│       ├── integratepie/          -- 3 fechas, 2 PRs cada una
│       └── personal/              -- 3 fechas, 1 PR cada una
├── docs/                          -- Documentación extensa
├── src/jarvis/                    -- Paquete fuente principal (60 .py, ~7,887 líneas)
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                     -- CLI principal (1,041 líneas, 20+ comandos)
│   ├── config.py                  -- Cargador TOML + env
│   ├── agents/                    -- Sistema de agentes
│   ├── core/                      -- Eventos, modelos, orquestador
│   ├── integrations/              -- Sistemas externos
│   ├── jobs/                      -- Jobs background con Huey
│   ├── llm/                       -- Proveedores LLM + routing
│   ├── memory/                    -- Memoria persistente con FTS5
│   ├── observability/             -- Métricas, health, benchmarks
│   ├── security/                  -- Autonomía, sanitización
│   ├── telegram/                  -- Bot Telegram [DEPRECADO 27-10-26]
│   ├── tools/                     -- Protocolo de tools + QA tools
│   └── web/                       -- Dashboard FastAPI + API
├── tests/                         -- Suite de tests (23 .py, ~2,528 líneas)
│   ├── conftest.py
│   ├── integration/               -- Vacío (placeholder)
│   └── unit/                      -- 20 archivos de test
└── workspace/.cache/              -- Cache de enriquecimiento PR
```

---

## Dependencias Python

### Core

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| typer | >=0.12.0 | Framework CLI |
| rich | >=13.0.0 | Formateo terminal |
| pydantic | >=2.0.0 | Modelos/validación de datos |
| python-dotenv | >=1.0.0 | Carga de .env |
| httpx | >=0.27.0 | Cliente HTTP (Ollama, Gemini, KameCol APIs) |
| huey | >=2.5.0 | Motor de jobs background (backend SQLite) |
| fastapi | >=0.115.0 | Web API + dashboard |
| uvicorn[standard] | >=0.30.0 | Servidor ASGI |
| jinja2 | >=3.1.0 | Templating HTML |
| python-telegram-bot | >=21.0 | Bot Telegram [DEPRECADO] |
| psycopg2-binary | >=2.9.0 | Cliente PostgreSQL (KameCol prod DB) |

### Dev

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| pytest | >=8.0.0 | Testing |
| pytest-cov | >=5.0.0 | Reportes de cobertura |

---

## Configuración

### `.env` (CONTIENE SECRETOS)

- `TELEGRAM_BOT_TOKEN` — Token del bot Telegram
- `TELEGRAM_ALLOWED_USERS` — ID de usuario 1401059055
- `KAMECOL_API_URL` — URL producción KameCol en Render
- `KAMECOL_DATABASE_URL` — String de conexión PostgreSQL producción completo con credenciales

**ALERTA DE SEGURIDAD:** El archivo `.env` contiene un string de conexión a base de datos de producción con credenciales en texto plano. Aunque `.env` está en `.gitignore`, es la base de datos real de producción de KameCol en Render.

### `config/jarvis.toml`

- Versión: 0.1.0
- Proyecto default: "personal"
- Path BD: data/jarvis.db
- Nivel de logging: INFO

### `config/models.toml`

- Presupuesto semanal: $5.00 USD
- Alerta diaria: $1.50 USD
- Auto-switch a local al 80% del presupuesto
- Preferencia: prefer_local = true

### Configs de Proyecto (`config/projects/*.toml`)

- **personal.toml:** Cloud permitido, providers [ollama, gemini], autonomy_level=1, sin patrones sensibles
- **integratepie.toml:** Cloud permitido, providers [ollama, gemini], autonomy_level=0, PII-to-cloud bloqueado, patrones sensibles: run, rut, nombre_alumno, diagnostico. Lectura Azure DevOps permitida, escritura bloqueada
- **kamecol.toml:** Cloud permitido, providers [ollama, gemini], autonomy_level=0, PII-to-cloud bloqueado, patrones sensibles: cedula, telefono, email, direccion. Lectura API permitida, escritura bloqueada

---

## Agentes y Capacidades Actuales

### Agentes Registrados

| Agente | ID | Skills | Proyectos | Estado |
|--------|----|--------|-----------|--------|
| Echo Agent | `core.echo` | general, help, status | todos | Placeholder/Fallback |
| QA Analyzer | `qa.analyzer` | analyze_pr, qa | todos | Depende de IAAgent externo |
| KameCol Agent | `biz.kamecol` | catalog, order_status, dashboard, recovery | kamecol | Básico |

### Tools QA (via IAAgent Bridge)

1. **DiffAnalyzerTool** (`qa.diff_analyzer`) — Clasifica archivos modificados, extrae funciones/endpoints/cambios DB
2. **SecurityAnalyzerTool** (`qa.security_analyzer`) — Detección OWASP Top 10 (14+ patrones)
3. **StaticAnalyzerTool** (`qa.static_analyzer`) — TODOs, código debug, secretos, bare except
4. **RiskEngineTool** (`qa.risk_engine`) — Score de riesgo 0-10 con factores ponderados
5. **TestCaseGeneratorTool** (`qa.test_case_generator`) — 7 categorías de casos de prueba

---

## Arquitectura

```
Interfaces             CLI (Typer) | Web Dashboard (FastAPI)
                              |
Core                   Orchestrator -> Intent Detection (regex) -> Agent Registry
                              |
Agentes                EchoAgent | QAAgent | KameColAgent
                              |
Tools                  QA Analyzers (via IAAgent Bridge) | KameCol Clients
                              |
Memoria                MemoryManager -> MemoryStore (SQLite + FTS5) + Embeddings (Ollama)
                              |
LLM                    Router -> OllamaProvider | GeminiProvider | ClaudeCodeProvider
                              |
Integraciones          IAAgent Bridge | Azure DevOps | KameCol API | KameCol DB | Repo Reader
                              |
Infraestructura        SQLite (events, memory, usage) | Huey (background jobs) | Ollama (local AI)
```

### Patrones de Diseño

1. **Agent Protocol** (`BaseAgent`): Todos implementan `spec()` y `execute()`
2. **Tool Protocol** (`BaseTool`): Todos implementan `spec()` y `_run()`
3. **LLM Provider Protocol** (`LLMProvider`): `is_available()`, `generate()`, `status()`
4. **Event-Driven**: Stream inmutable append-only en SQLite
5. **Memory Isolation**: Cada proyecto tiene su namespace. Cross-project denegado por SecurityGate
6. **Security by Default**: Niveles de autonomía (0-4), PII sanitization, credential detection
7. **Hybrid AI Routing**: Clasificación de complejidad → selección de provider

### Schema de Base de Datos (SQLite)

**events:** id, timestamp, event_type, agent_id, project, payload, parent_event_id
**memory:** id, project, memory_type, source, content, metadata, confidence, status, created_at, updated_at, version, tags, permissions, embedding
**llm_usage:** id, timestamp, provider, model, project, agent_id, task_type, input_tokens, output_tokens, total_tokens, cost_usd, latency_ms, success, error

---

## MCP Servers Configurados

1. **mysql-prod** — Queries MySQL producción
2. **mysql-qa** — Queries MySQL QA
3. **Claude Docs** — Operaciones de documentos
4. **Google Drive** — Operaciones de archivos
5. **Mixpanel** — Analytics (queries, events, dashboards, experiments, feature flags)
6. **monday.com** — Autenticación
7. **Jam** — Autenticación

---

## Integraciones en Código Fuente

1. **Azure DevOps** — Work items CRUD, PR work items, publicación de comentarios
2. **IAAgent Bridge** — Import dinámico del proyecto IAAgent externo (10+ módulos)
3. **KameCol Public API** — Catálogo, detalle producto, navegación, estado de orden
4. **KameCol Admin API** — Dashboard KPIs, órdenes pendientes, recordatorios, inventario
5. **KameCol Production DB** — Acceso PostgreSQL read-only con protecciones
6. **Repo Reader** — Acceso controlado read-only a repos locales
7. **Knowledge Bases** — 36 entradas de conocimiento de dominio (personal, PIE, KameCol)

---

## Cobertura de Tests

| Archivo | Tests | Cubre |
|---------|-------|-------|
| test_models.py | 15 | Event, ProjectContext, ToolAction, ToolObservation, MemoryRecord, enums |
| test_events.py | 10 | EventStore: emit, query, count, persistencia |
| test_config.py | 8 | Config global, contextos de proyecto, listing |
| test_cli.py | 6 | version, ask, status, events, help |
| test_agents.py | 14 | AgentRegistry, EchoAgent, intent detection, Orchestrator |
| test_router.py | 12 | Clasificación complejidad, LLMRouter, generate |
| test_llm_base.py | 8 | LLMRequest, LLMResponse, ProviderStatus, TaskComplexity |
| test_memory_store.py | 16 | CRUD, FTS5 search, embeddings, persistencia |
| test_memory_manager.py | 14 | CRUD, FTS search, aislamiento, context injection |
| test_security.py | 10 | SecurityGate: tools, providers, memoria, sanitización |
| test_autonomy.py | 16 | Niveles autonomía, permisos, workflow aprobación |
| test_tools.py | 10 | BaseTool, ToolRegistry |
| test_usage.py | 7 | UsageTracker: record, summary, cost |
| test_observability.py | 8 | MetricsCollector, AgentMetrics, health checks, benchmarks |
| test_web.py | 10 | API endpoints, páginas web |
| test_qa_agent.py | 6 | QA agent pipeline |
| test_iaagent_bridge.py | 12 | Bridge imports, tool registration |
| test_integratepie.py | 6 | AzureDevOps, knowledge seeding |
| test_kamecol.py | 10 | Modelos datos, clients, KameCol agent |

**Total:** ~170+ tests | **Coverage threshold:** 80%

---

## Historial Git

| Fecha | Commit | Descripción |
|-------|--------|-------------|
| Oct 24, 15:22 | Phase 0+1 | Planning + JARVIS Core (CLI, events, config, security) |
| Oct 24, 15:28 | Phase 2 | Hybrid AI engine (Ollama + Gemini routing, fallback) |
| Oct 24, 15:35 | Phase 3 | Persistent memory (FTS5, embeddings, isolation) — MVP |
| Oct 24, 15:40 | Phase 4 | Agent system (orchestrator, tools, Huey jobs) |
| Oct 24, 15:45 | Phase 5 | IAAgent reuse via dynamic bridge |
| Oct 24, 15:49 | Phase 6 | QA Intelligence (full PR analysis pipeline) |
| Oct 24, 15:54 | Phase 7 | IntegratePIE connector (work items, publisher, knowledge) |
| Oct 24, 15:58 | Phase 8 | KameCol Intelligence (agent, API clients) |
| Oct 24, 16:01 | Phase 9 | Observability (dashboard, health checks, benchmarks) |
| Oct 24, 16:05 | Phase 10 | Control Center (web dashboard, REST API, HTMX) |
| Oct 24, 16:08 | Phase 11 | Optimization and autonomy (roadmap complete) |
| Oct 24, 16:17 | Fix | test_ask compatible with Ollama |
| Oct 24, 16:31 | Feature | Knowledge bases, repo reader |
| Oct 24, 17:07 | Feature | Telegram bot + chat + repo context |
| Oct 25, 07:35 | Feature | Telegram bot + Claude Code engine + KameCol prod DB |
| Oct 26, 10:20 | Docs | Remote workflow guide (iPhone + Tailscale + SSH) |

---

## Problemas Críticos

### 1. Seguridad: `--dangerously-skip-permissions` en Telegram Bot
**Archivo:** `src/jarvis/telegram/bot.py:611`
**Riesgo:** CRÍTICO — cualquier usuario autorizado puede ejecutar operaciones arbitrarias sin verificación de permisos a través de Claude Code

### 2. Credenciales de Producción en `.env`
**Riesgo:** ALTO — String de conexión PostgreSQL con user/password en texto plano para la BD de producción de KameCol

### 3. Sin CI/CD
**Riesgo:** ALTO — No hay GitHub Actions, no hay linting automatizado, no hay pipeline de deploy

### 4. Tests de Integración Vacíos
**Riesgo:** MEDIO — El directorio `tests/integration/` existe pero no tiene tests

### 5. Solo 3 Agentes (1 es placeholder)
**Impacto:** ALTO — Echo es fallback, QA depende de IAAgent externo, KameCol es básico

### 6. Sin Sistema de Plugins
**Impacto:** ALTO — Todo hardcodeado, sin descubrimiento ni validación de plugins

### 7. Tarea Duplicada `daily_maintenance`
**Archivo:** Definida en `jobs/scheduler.py` y `jobs/tasks.py` con implementaciones diferentes

### 8. Directorio static/ referenciado pero inexistente
**Archivo:** `web/app.py` monta `/static` desde directorio que puede no existir

---

## Ecosistema MCP Investigado — Plugins Recomendados

### Tier 1: Instalar inmediatamente (production-ready)

| Plugin | Stars | Propósito |
|--------|-------|-----------|
| **microsoft/playwright-mcp** | ~38,700 | Testing E2E, browser automation |
| **github/github-mcp-server** | ~34,000 | PRs, Issues, Actions, CI/CD |
| **SonarSource/sonarqube-mcp-server** | ~674 | Code quality gates |
| **postmanlabs/postman-mcp-server** | ~324 | API testing & collections |

### Tier 2: Evaluar según workflow

| Plugin | Stars | Propósito |
|--------|-------|-----------|
| **cisco-ai-defense/mcp-scanner** | ~1,100 | Seguridad de MCP servers |
| **semgrep** (MCP built-in) | ~667 | Análisis estático seguridad |
| **RunMaestro/Maestro** | ~3,500 | Orquestación multi-agente |

### Tier 3: Experimental pero prometedor

| Plugin | Stars | Propósito |
|--------|-------|-----------|
| **cocaxcode/api-testing-mcp** | ~6 | API testing + load testing |
| **xz-dev/bdd-skill** | bajo | Guía BDD/Gherkin |
| **HelpCode-ai/ecommerce-mcp-server** | bajo | E-commerce multi-plataforma |

### Gaps (sin MCP maduro)

- **Load testing** dedicado (k6, JMeter)
- **Gherkin/Cucumber** ejecución nativa
- **Test management** (TestRail, Xray)

---

## Visión Propuesta: JARVIS Profesional

```
                        ┌─────────────────────────────┐
                        │     PLUGIN GUARDIAN          │
                        │  Descubre · Valida · Audita  │
                        └──────────┬──────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
   ┌────▼────┐              ┌─────▼─────┐             ┌──────▼──────┐
   │  QA Hub │              │  BizOps   │             │  DevOps     │
   │         │              │  Hub      │             │  Hub        │
   ├─────────┤              ├───────────┤             ├─────────────┤
   │Playwright│             │ KameCol   │             │ GitHub MCP  │
   │Postman   │             │ E-commerce│             │ CI/CD       │
   │SonarQube │             │ Analytics │             │ Docker      │
   │Semgrep   │             │ Recovery  │             │ Deploy      │
   │Gherkin   │             │ Inventory │             │ Monitoring  │
   │Load Test │             └───────────┘             └─────────────┘
   │Security  │
   └─────────┘
        │
   ┌────▼──────────────────────────────────┐
   │  ORQUESTADOR MULTI-AGENTE             │
   │  Propone · Planifica · Ejecuta · Reporta │
   └───────────────────────────────────────┘
```

---

*Auditoría realizada el 27 de octubre de 2026 por Claude Code (Opus 4.6)*
