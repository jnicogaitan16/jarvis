# JARVIS — Documentación Técnica Completa

> Fecha: 2026-10-28
> Versión: 0.1.0
> Verificado: Tests ejecutados (331/333 passed), código auditado

---

## Qué es JARVIS

JARVIS es un asistente personal de productividad orientado a QA Engineering, construido como CLI + API web. Orquesta múltiples LLMs (local y cloud), integra herramientas de desarrollo (Azure DevOps, Sentry, bases de datos) y ejecuta pipelines de análisis QA automatizado.

---

## Stack Tecnológico (comprobado)

- **Lenguaje:** Python 3.12+
- **CLI:** Typer + Rich (20+ comandos)
- **Web:** FastAPI + Uvicorn + Jinja2
- **Base de datos:** SQLite (WAL mode) + FTS5 full-text search
- **LLM local:** Ollama (qwen2.5:7b, codeqwen:7b, qwen2.5:3b)
- **LLM cloud:** Google Gemini 2.5 Flash (REST API)
- **LLM alternativo:** Claude Code CLI via subprocess
- **Embeddings:** Ollama nomic-embed-text + cosine similarity
- **Background jobs:** Huey con SQLite backend
- **Validación:** Pydantic v2
- **HTTP client:** httpx
- **Testing:** pytest + pytest-cov (331 tests, threshold 60%)
- **Linting:** Ruff (con reglas flake8-bandit para seguridad)
- **CI/CD:** GitHub Actions (ruff lint + pytest)
- **Container:** Docker + docker-compose

---

## Estructura del Proyecto

```
jarvis/
├── src/jarvis/                  # Paquete principal
│   ├── __init__.py              # Version 0.1.0
│   ├── __main__.py              # Entry point: python -m jarvis
│   ├── cli.py                   # CLI Typer (~1318 líneas, 20+ comandos)
│   ├── config.py                # Carga TOML + .env
│   │
│   ├── agents/                  # Sistema de agentes
│   │   ├── base.py              # Protocol: AgentSpec, AgentRequest, AgentResult, BaseAgent
│   │   ├── registry.py          # Registro de agentes por ID
│   │   ├── echo.py              # Agente fallback (echo)
│   │   ├── qa/
│   │   │   ├── agent.py         # QAAgent — orquesta pipeline IAAgent completo
│   │   │   ├── code_review_agent.py  # Análisis estático regex (12+ patrones OWASP)
│   │   │   ├── gherkin_agent.py      # Generador BDD/Gherkin determinista (sin LLM)
│   │   │   ├── test_strategy_agent.py # Planificador de testing + evaluación ROI
│   │   │   ├── writer_agent.py       # Redactor QA (bug reports, preguntas DEV)
│   │   │   └── templates.py          # 5 templates estructurados
│   │   └── business/
│   │       └── kamecol_agent.py      # Consultas catálogo/pedidos/KPIs via API
│   │
│   ├── core/
│   │   ├── models.py            # Pydantic models: Event, ProjectContext, MemoryRecord
│   │   ├── orchestrator.py      # Router determinista por regex (10 patrones de intent)
│   │   └── events.py            # EventStore append-only en SQLite
│   │
│   ├── llm/
│   │   ├── base.py              # Protocol: LLMProvider, LLMRequest, LLMResponse
│   │   ├── router.py            # Selección de provider por complejidad + políticas
│   │   ├── ollama.py            # Provider local: Ollama REST API
│   │   ├── gemini.py            # Provider cloud: Google Gemini 2.5 Flash
│   │   ├── claude_code.py       # Provider: Claude Code CLI via subprocess
│   │   ├── model_selector.py    # Perfiles de modelos con recomendaciones por tarea
│   │   └── usage.py             # Tracking de costos/tokens en SQLite
│   │
│   ├── memory/
│   │   ├── store.py             # SQLite + FTS5 full-text search
│   │   ├── manager.py           # Búsqueda híbrida: FTS5 (40%) + semántica (60%)
│   │   └── embeddings.py        # Embeddings via Ollama (nomic-embed-text)
│   │
│   ├── security/
│   │   ├── context.py           # SecurityGate: sanitización de credenciales + PII
│   │   └── autonomy.py          # 5 niveles de autonomía (0-4) + políticas
│   │
│   ├── integrations/
│   │   ├── iaagent_bridge.py    # Bridge dinámico a IAAgent
│   │   ├── azure_devops.py      # Client REST para work items + PR comments
│   │   ├── kamecol.py           # Client REST público + admin KameCol
│   │   ├── kamecol_db.py        # Consultas PostgreSQL directas
│   │   ├── kamecol_knowledge.py # Seed de conocimiento KameCol
│   │   ├── pie_knowledge.py     # Seed de 15 entradas IntegratePIE
│   │   ├── personal_knowledge.py # Seed de perfil personal
│   │   └── repo_reader.py       # Lectura controlada de repos locales
│   │
│   ├── pipelines/
│   │   ├── engine.py            # Ejecución secuencial multi-agente
│   │   ├── models.py            # PipelineDef, PipelineStep, PipelineResult
│   │   └── workflows.py         # 4 workflows predefinidos
│   │
│   ├── plugins/
│   │   ├── guardian.py          # Escaneo + validación de plugins
│   │   ├── discovery.py         # Descubre MCP servers + Claude plugins
│   │   ├── registry.py          # Registro in-memory
│   │   └── models.py            # PluginSpec, PluginHealth, enums
│   │
│   ├── tools/
│   │   ├── base.py              # Protocol: BaseTool, ToolSpec
│   │   ├── registry.py          # Registro de herramientas
│   │   └── qa/analyzers.py      # 5 wrappers de analyzers IAAgent como Tools
│   │
│   ├── jobs/
│   │   ├── engine.py            # Huey con SQLite backend
│   │   ├── scheduler.py         # Scheduling (estructura)
│   │   ├── worker.py            # Workers (estructura)
│   │   └── tasks.py             # 2 tareas: run_agent_task + daily_maintenance
│   │
│   ├── web/
│   │   ├── app.py               # FastAPI server
│   │   ├── api.py               # REST API: /health, /metrics, /projects, /agents, /memory, /events
│   │   ├── pages.py             # HTML pages con Jinja2
│   │   └── templates/           # 5 templates HTML
│   │
│   └── observability/
│       ├── metrics.py           # MetricsCollector desde SQLite
│       ├── health.py            # 7 health checks
│       └── benchmarks.py        # Framework de benchmarks con 3 suites
│
├── config/
│   ├── jarvis.toml              # Config global
│   ├── models.toml              # Budget LLM ($5/semana, $1.50/día alerta)
│   └── projects/
│       ├── personal.toml        # autonomy=1, cloud=true
│       ├── integratepie.toml    # autonomy=0, pii_to_cloud=false
│       └── kamecol.toml         # autonomy=0, pii_to_cloud=false
│
├── data/
│   ├── jarvis.db                # SQLite principal
│   └── evidence/                # Reportes generados por proyecto/fecha
│
├── tests/                       # 23 archivos, 333 tests
├── workspace/.cache/            # Cache de enrichments LLM (JSON)
├── .github/workflows/ci.yml     # CI: ruff lint + pytest
├── Dockerfile + docker-compose.yml
└── Makefile
```

---

## Puntos de Entrada

JARVIS tiene **tres puntos de entrada**:

- **CLI (principal):** comando `jarvis`, definido en `pyproject.toml` como `jarvis = "jarvis.cli:app"`. Usa Typer con Rich para output formateado.
- **Python module:** `python -m jarvis` via `__main__.py`
- **Web server:** `jarvis serve` levanta FastAPI en `localhost:8000`

---

## Flujos de Ejecución Principales

### `jarvis ask "pregunta" --project personal`

1. Carga contexto del proyecto desde TOML
2. Construye LLMRouter con Ollama + Gemini + Claude Code
3. Obtiene contexto de memoria relevante (búsqueda híbrida FTS5 + semántica)
4. Crea `LLMRequest` con prompt + system prompt (con memoria inyectada)
5. Router selecciona provider según complejidad (regex heurísticas):
   - Simple → Ollama (local)
   - Medio/Complejo/Code → Claude Code
   - Fallback cloud → Gemini
6. Ejecuta generación con fallback automático entre providers
7. Registra uso (tokens, costo, latencia) en SQLite

### `jarvis analyze-pr 42 --project integratepie`

1. Verifica que IAAgent esté disponible via bridge
2. Crea `QAAgent` con `AgentRequest(intent="analyze_pr", payload={"pr_id": 42})`
3. QAAgent obtiene contexto del PR:
   - Si hay datos directos → construye PRContext localmente
   - Si solo hay pr_id → fetch via Azure DevOps client
4. Importa `agent.pipeline` de IAAgent y ejecuta 6 analyzers + generators:
   - DiffAnalyzer, SecurityAnalyzer, StaticAnalyzer, ImpactAnalyzer, DependencyAnalyzer
   - RiskEngine (score 0-10), TestCaseGenerator (7 categorías), ReportGenerator, CommentGenerator
5. Guarda evidencias en `data/evidence/{project}/{date}/`
6. Guarda resultado en memoria episódica

### `jarvis pipeline run full_qa_review "descripcion"`

1. Obtiene workflow predefinido (4 steps)
2. Ejecuta secuencialmente: CodeReview → Gherkin → Strategy → Writer
3. Contexto compartido entre steps: output del step 1 se inyecta como input del step 2

### `jarvis run "tarea" --project integratepie`

1. Orchestrator recibe el texto de la tarea
2. `detect_intent()` prueba 10 patrones regex secuencialmente
3. Busca agente por match de intent → ejecuta `agent.execute(request)`

---

## Integraciones (comprobadas)

- **Azure DevOps** (`integrations/azure_devops.py`) — Work items, PR comments, publicación controlada. Variable `AZDO_ENABLE_PUBLISH` controla si se publican comentarios.
- **IAAgent** (`integrations/iaagent_bridge.py`) — Bridge dinámico via `sys.path` injection. 12 imports lazy (analyzers, generators, models del proyecto IAAgent).
- **KameCol API** (`integrations/kamecol.py`) — Client público (productos, pedidos) + admin (dashboard, recovery).
- **KameCol DB** (`integrations/kamecol_db.py`) — Consultas PostgreSQL directas.
- **Ollama** (`llm/ollama.py`) — REST API local en localhost:11434.
- **Gemini** (`llm/gemini.py`) — REST API con retry/backoff.
- **Claude Code** (`llm/claude_code.py`) — CLI subprocess con JSON output.
- **MCP Plugins** (`plugins/discovery.py`) — Descubrimiento via `claude mcp list`.
- **Repos locales** (`integrations/repo_reader.py`) — Lectura controlada con allow/deny patterns.

---

## Outputs Generados

1. **Reportes QA en Markdown** — `data/evidence/{project}/{date}/pr-{id}-report.md`
2. **Comentarios para PR** — `data/evidence/{project}/{date}/pr-{id}-comment.md`
3. **Datos estructurados JSON** — `pr-{id}-data.json` (risk level, findings, test cases)
4. **Escenarios Gherkin** — generados por GherkinAgent (determinista, sin LLM)
5. **Bug reports estructurados** — via WriterAgent con 5 templates
6. **Estrategias de testing** — tablas de recomendaciones con evaluación ROI
7. **Code review findings** — tabla de hallazgos por severidad (análisis estático regex)
8. **Dashboard métricas** — CLI y Web API (`/api/v1/metrics`)
9. **Enrichments LLM** — cacheados en `workspace/.cache/` como JSON

---

## Seguridad

### SecurityGate (implementado pero NO integrado en flujo real)

Archivo: `src/jarvis/security/context.py`

El `SecurityGate` implementa:
- `sanitize_for_logging()` — redacta credenciales (API keys, tokens, PATs, RUTs chilenos) con regex
- `sanitize_for_cloud()` — aplica sanitize_for_logging + sensitive_patterns del proyecto
- `check_tool_access()`, `check_provider_access()`, `check_memory_access()`

**Patrones de sanitización definidos:**

```python
_CREDENTIAL_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|password|secret|pat)\s*[=:]\s*\S+"),
    re.compile(r"sk-ant-[a-zA-Z0-9-]+"),          # Anthropic keys
    re.compile(r"AI[a-zA-Z0-9_-]{30,}"),           # Gemini keys
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),            # GitHub PATs
    re.compile(r"gho_[a-zA-Z0-9]{36}"),            # GitHub OAuth
    re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b"),  # RUT chileno
]
```

**Sensitive patterns por proyecto (config TOML):**
- **IntegratePIE:** `run`, `rut`, `nombre_alumno`, `diagnostico`
- **KameCol:** `cedula`, `telefono`, `email`, `direccion`

### HALLAZGO CRITICO: SecurityGate no se invoca en el flujo de ejecución

- `SecurityGate` NO se importa ni usa en ningún módulo fuera de `security/context.py` y tests
- No se llama en `llm/router.py` antes de enviar prompts al LLM
- No se llama en `cli.py` antes de `ask` o `chat`
- No se llama en ningún agente
- El campo `allow_pii_to_cloud=False` se configura pero **nunca se verifica** en runtime
- Los datos se envían **sin sanitizar** a los LLMs (tanto local como cloud)

### Aislamiento de Memoria

La memoria SÍ tiene aislamiento por proyecto (funcional y testeado):
- `MemoryManager.search()` filtra por namespace de proyecto
- `SecurityGate.check_memory_access()` permite acceso solo al propio namespace + "system"
- Pero `check_memory_access()` no se invoca en el flujo real

### Niveles de Autonomía

5 niveles definidos en `security/autonomy.py`:
- **0 (Observe):** Solo lectura, no ejecuta acciones
- **1 (Suggest):** Sugiere acciones, requiere aprobación
- **2 (Assist):** Ejecuta acciones reversibles sin aprobación
- **3 (Act):** Ejecuta la mayoría de acciones automáticamente
- **4 (Full):** Autonomía completa

Configurados por proyecto:
- IntegratePIE: autonomy=0 (observe only)
- KameCol: autonomy=0
- Personal: autonomy=1 (suggest)

### Lectura de Repos

`repo_reader.py` tiene control de acceso:
- **Allow:** `*.py, *.ts, *.tsx, *.json, *.toml, *.yml, *.md`
- **Deny:** `.env, *.db, *.sqlite3, media/*, node_modules/*`

---

## Sistema de Memoria

### Almacenamiento
- SQLite con FTS5 (full-text search) para búsqueda eficiente
- Tabla principal + tabla FTS virtual sincronizada

### Búsqueda Híbrida
- **FTS5 (40% peso):** Búsqueda textual rápida
- **Semántica (60% peso):** Embeddings via Ollama (nomic-embed-text) + cosine similarity
- Máximo 5 registros, máximo 3000 caracteres inyectados en system prompt

### Knowledge Base
- 15 entradas de IntegratePIE (stack, reglas FUR, NEE, permisos, tests)
- Conocimiento de KameCol (catálogo, pagos, arquitectura)
- Perfil personal del usuario
- Cargadas via `jarvis seed-knowledge`

---

## LLM Router

### Selección de Provider
1. Evalúa complejidad del prompt (simple/medium/complex/code) via heurísticas regex
2. Verifica providers permitidos por el proyecto
3. Verifica disponibilidad real del provider
4. Prioridad: local (Ollama) → Claude Code → Gemini (fallback cloud)

### Budget
- Configurado: $5/semana, $1.50/día alerta, auto-switch a local al 80%
- **NOTA:** El enforcement del budget está configurado pero no se verifica antes de hacer requests

### Usage Tracking
- Cada request registra: provider, model, tokens, costo, latencia, proyecto, errores
- Tabla `llm_usage` en SQLite
- Consultable via `jarvis llm-usage`

---

## Análisis Estático

### CodeReviewAgent (propio, regex)
12 patrones de detección:
- **CRITICAL:** Credenciales hardcodeadas
- **HIGH:** `eval()`, `exec/system/popen/subprocess.call`, credenciales en logs, SSL disabled
- **MEDIUM:** `except:` bare, `import *`, `time.sleep(largo)`, `SELECT *`
- **LOW:** TODO/FIXME/HACK, `print()` residual
- **INFO:** Legacy formatting (`.format()/%s`)

Más análisis de complejidad: funciones >50 líneas, anidamiento >=5, archivos >500 líneas.

### IAAgent Bridge (análisis avanzado)
Via bridge: SecurityAnalyzer (14+ patrones OWASP), StaticAnalyzer, DiffAnalyzer, RiskEngine (score 0-10 ponderado).

---

## Pipelines

4 workflows predefinidos:
1. **full_qa_review** — CodeReview → Gherkin → Strategy → Writer
2. **quick_review** — CodeReview → Writer
3. **test_planning** — Strategy → Gherkin
4. **bug_report** — Writer (solo redacción)

Ejecución secuencial con contexto compartido entre steps.

---

## Observabilidad

### Health Checks (7)
- SQLite, Ollama, Claude Code, Gemini, IAAgent, KameCol, Memory

### Métricas
- Total de requests LLM, tokens, costos
- Eventos por tipo
- Registros de memoria por proyecto
- Consultable via CLI (`jarvis metrics`) y API (`/api/v1/metrics`)

### Benchmarks
3 suites:
- **Intent detection:** Precisión del router de intents
- **Security:** Efectividad de sanitización
- **Memory:** Precisión de búsqueda

---

## Tests (verificados)

- **23 archivos** en `tests/unit/`
- **333 tests totales:** 331 passed, 2 failed (incompatibilidad Typer + Python 3.14)
- **Coverage threshold:** 60% (configurado en `pyproject.toml`)
- **CI:** GitHub Actions ejecuta `ruff check` + `pytest --cov-fail-under=60`

---

## Configuración

### Variables de Entorno (.env)

- `JARVIS_ENV` — Entorno (development/production/ci)
- `IAAGENT_PATH` — Ruta al proyecto IAAgent
- `GEMINI_API_KEY` — API key de Gemini
- `AZDO_ORG_URL`, `AZDO_PAT`, `AZDO_PROJECT` — Azure DevOps
- `KAMECOL_API_URL`, `KAMECOL_SESSION` — KameCol store
- `KAMECOL_DATABASE_URL` — PostgreSQL de KameCol
- `MYSQL_HOST/PORT/DATABASE/USER/PASSWORD` — MySQL IntegratePIE
- `SENTRY_AUTH_TOKEN/ORG/PROJECT` — Sentry
- `TRELLO_KEY/TOKEN` — Trello (opcional)

### Config TOML
- `config/jarvis.toml` — DB path, logging
- `config/models.toml` — Budget LLM, preferencias de modelos
- `config/projects/{id}.toml` — Políticas por proyecto (providers, PII, autonomía)

---

## Puntos de Mejora Identificados

1. **SecurityGate no integrado** — Las funciones de sanitización existen y tienen tests, pero no se invocan antes de enviar datos a LLMs cloud
2. **Sin cache de respuestas LLM** — El campo `cached` en `LLMResponse` existe pero no se implementa
3. **Budget no enforced** — Se configura pero no se verifica antes de requests
4. **Background jobs esquelético** — Huey configurado pero tareas son stubs
5. **Orchestrator solo regex** — No hay ML ni LLM para detección de intent
6. **Agentes QA son deterministas** — Solo QAAgent (via IAAgent) y ask/chat usan LLM

---

*Documentación generada y verificada por JARVIS · 2026-10-28*
