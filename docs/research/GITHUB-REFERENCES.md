# Investigación de Proyectos de Referencia — GitHub

**JARVIS — Análisis de arquitecturas open source**

Fecha: 2026-10-24

---

## 1. Matriz de decisiones

| Proyecto | Stars | Licencia | Decisión | Patrón clave | Justificación |
|----------|-------|----------|----------|--------------|---------------|
| OpenHands | ~91,700 | MIT | **Adaptar** | Event stream, Action/Observation/Executor | Patrones arquitectónicos aplicables sin importar la dependencia |
| Playwright MCP | ~38,600 | Apache 2.0 | **Adoptar** | MCP tools para browser automation | Usar directamente como servidor MCP externo |
| PR-Agent | ~13,600 | Apache 2.0 | **Referencia** | Command-as-Tool, context compression | Patrones de diseño para agente de code review |
| TestZeus Hercules | ~1,200 | **AGPL-3.0** | **Referencia** | Planner/Executor split, proof pipeline | Licencia incompatible; solo extraer ideas |
| Sentry MCP | ~944 | Sentry License | **Referencia** | Skills-based tool grouping | Licencia no-OSI; usar como modelo de diseño |
| Huey | ~6,055 | MIT | **Adoptar** | Decorator-based task queue, SQLite backend | Directamente usable para background jobs |

---

## 2. Análisis detallado por proyecto

### 2.1 OpenHands (All-Hands-AI/OpenHands)

**URL:** https://github.com/All-Hands-AI/OpenHands
**Versión:** 1.7.0 | **Licencia:** MIT | **Actividad:** >1.1M descargas/mes

**Arquitectura:**
- SDK Python con 4 capas: `openhands.sdk` (core), `openhands.tools`, `openhands.workspace`, `openhands.agent_server`
- **Event stream** como backbone: cada acción del agente y observación del entorno son eventos inmutables tipados.
- **Controller** gestiona el loop del agente y ciclo de vida del sandbox.
- Docker sandbox con `cap-drop ALL + no-new-privileges`.
- Sistema de **MicroAgents** para skills reutilizables.

**Patrones para JARVIS:**

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Action     │────▶│   Executor   │────▶│ Observation  │
│ (Pydantic)   │     │  (Tool impl) │     │ (Pydantic)   │
└─────────────┘     └──────────────┘     └─────────────┘
        │                                        │
        └────────────── Event Stream ────────────┘
```

- **Action/Observation/Executor triple:** Cada tool define su contrato de entrada (Action), lógica de ejecución (Executor), y resultado tipado (Observation). Aplicable directamente al Tool Layer de JARVIS.
- **Event stream inmutable:** Registro de toda la actividad como eventos. Facilita debugging, replay y auditoría.
- **Separación Controller/Runtime:** El controller (loop de razonamiento) es independiente del runtime (ejecución). Permite testing sin sandbox real.
- **MicroAgents como skills:** Prompts especializados con activación por trigger.

**Limitaciones para JARVIS:**
- La arquitectura completa (Agent Server multi-usuario) es excesiva para uso personal.
- Docker sandbox consume RAM significativa en Mac mini 16 GB.
- El repositorio principal migró a TypeScript; el SDK Python es un paquete separado.

**Decisión: ADAPTAR** — Implementar los patrones Action/Observation/Executor y event stream en código propio de JARVIS, sin importar la dependencia.

---

### 2.2 Playwright MCP (microsoft/playwright-mcp)

**URL:** https://github.com/microsoft/playwright-mcp
**Licencia:** Apache 2.0 | **Actividad:** Mantenido activamente por Microsoft

**Arquitectura:**
- Servidor MCP que expone 66+ herramientas de automatización de browser.
- Dos modos de transporte: **stdio** (CLI) y **SSE** (servidor).
- Usa **accessibility snapshots** en lugar de screenshots para interacción determinista.
- Timeouts configurables: action (5s), navigation (60s), settlement (500ms).

**Categorías de herramientas:**

| Categoría | Ejemplos |
|-----------|---------|
| Navegación | navigate, go_back, go_forward |
| Interacción | click, fill, select_option, check |
| Tabs | tab_new, tab_select, tab_close |
| Network | network_mock, network_unmock |
| Storage | storage_get, storage_set |
| DevTools | console_logs, coverage |
| Assertions | assert_text, assert_element |
| Media | screenshot, pdf_save |

**Aplicación directa en JARVIS:**
- El agente QA puede usar Playwright MCP para ejecutar pruebas E2E contra IntegratePIE.
- Las evidencias (screenshots, PDFs) se generan automáticamente.
- El modo accessibility snapshot es eficiente en tokens para el LLM.
- Compatible con el estado actual de IntegratePIE (Playwright instalado pero sin tests).

**Decisión: ADOPTAR** — Instalar como servidor MCP externo. No reescribir.

---

### 2.3 PR-Agent (qodo-ai/pr-agent)

**URL:** https://github.com/qodo-ai/pr-agent
**Licencia:** Apache 2.0 | **Actividad:** Mantenido por Qodo (antes CodiumAI)

**Arquitectura:**
```
pr_agent/
├── agent/          # Orquestación
├── algo/           # Compresión de PRs
├── git_providers/  # GitHub, GitLab, Bitbucket, Azure DevOps
├── tools/          # /review, /improve, /describe
├── servers/        # Webhooks, GitHub Actions
└── settings/       # Prompts en TOML
```

**Patrones relevantes:**

1. **Command-as-Tool:** Cada capacidad (`/review`, `/describe`) es un tool independiente con su propio prompt template en TOML. Exactamente el patrón que JARVIS necesita para skills de agentes.

2. **PR Compression Strategy:** Preprocesar y comprimir el contexto del PR antes de enviarlo al LLM. IAAgent ya hace esto parcialmente (budget de 12KB para diffs); PR-Agent lo lleva más lejos con algoritmos de relevancia.

3. **Configuration-driven prompts:** Prompts como configuración TOML, no hardcoded en código. IAAgent tiene el prompt hardcoded en `enrichment.py` — JARVIS debe adoptar el patrón de PR-Agent.

4. **Git provider abstraction:** Adaptadores para múltiples plataformas SCM. IAAgent solo soporta Azure DevOps; JARVIS debería abstraer el proveedor.

**Limitaciones:** Diseñado solo para code review en CI/CD, no interactivo. La versión completa es comercial (Qodo Merge).

**Decisión: REFERENCIA** — Extraer patrones de diseño para el agente de code review de JARVIS.

---

### 2.4 TestZeus Hercules (test-zeus-ai/testzeus-hercules)

**URL:** https://github.com/test-zeus-ai/testzeus-hercules
**Licencia:** AGPL-3.0 (incompatible con proyecto privado) | **Stars:** ~1,200

**Arquitectura:**
- State machine basada en **LangGraph** con dos nodos: Planner y Executor.
- El Planner genera JSON estructurado; el Executor lo enruta a helpers especializados.
- Helpers: `browser_nav_agent`, `api_nav_agent`, `sec_nav_agent`, `sql_nav_agent`, `mcp_nav_agent`.

**Patrones extraíbles (no el código):**

1. **Planner/Executor con modelos distintos:** Un modelo capaz (costoso) para planificación, uno rápido (barato) para ejecución de steps. Relevante para JARVIS: usar Claude/GPT-4 para razonamiento complejo, Qwen local para ejecución simple.

2. **JSON estructurado como handoff:** Comunicación inter-agente mediante JSON tipado, no lenguaje natural. Reduce alucinaciones en la coordinación.

3. **Proof generation pipeline:** Screenshots, videos, network logs y test data como evidencia automática.

4. **Per-scenario isolation:** Cada test run es independiente.

**Limitaciones:** Licencia AGPL-3.0 impide usar el código. Dependencia fuerte de LangGraph/LangChain (frameworks que JARVIS quiere evitar).

**Decisión: REFERENCIA** — Solo patrones de diseño. No usar código.

---

### 2.5 Sentry MCP (getsentry/sentry-mcp)

**URL:** https://github.com/getsentry/sentry-mcp
**Licencia:** Sentry License (no OSI-approved) | **Stars:** ~944

**Arquitectura:**
- Monorepo TypeScript con pnpm workspaces.
- Dos modos: Remote MCP (Cloudflare Workers + OAuth) y Stdio MCP (local).
- **Skills-based architecture:** Tools agrupados en "skills" habilitables/deshabilitables via env vars.

**Patrones extraíbles:**

1. **Skills-based tool grouping:** En lugar de exponer 60+ tools al contexto del LLM, agrupar por skill y cargar solo los relevantes. Para JARVIS: cuando se activa el contexto QA, cargar solo tools QA; cuando se activa KameCol, cargar solo tools de e-commerce.

2. **REST API → MCP tool wrapping:** Cada endpoint de Sentry se convierte en un tool MCP con contexto optimizado para LLMs. Patrón aplicable para wrappear APIs de Azure DevOps, KameCol, etc.

3. **Scoped tokens:** Permisos granulares por skill (`org:read`, `project:write`).

**Decisión: REFERENCIA** — Patrón de skills-based grouping aplicable a JARVIS.

---

### 2.6 Huey (coleifer/huey)

**URL:** https://github.com/coleifer/huey
**Licencia:** MIT | **Stars:** ~6,055 | **Mantenido por:** Charles Leifer (autor de peewee ORM)

**Características:**
- Task queue minimalista. Zero dependencias core.
- `SqliteHuey`: backend SQLite, sin Redis ni infraestructura externa.
- API por decoradores: `@huey.task()`, `@huey.periodic_task(crontab(...))`.
- Retries declarativas: `@huey.task(retries=3, retry_delay=60)`.
- Pipeline: encadenar tasks con `.then()`.
- Consumer como proceso separado.

**Aplicación directa en JARVIS:**

```python
from huey import SqliteHuey

huey = SqliteHuey(filename='jarvis-jobs.db')

@huey.task(retries=2, retry_delay=30)
def analyze_pr(pr_id: int, project: str):
    """Ejecutar análisis QA de un PR en background."""
    ...

@huey.periodic_task(crontab(hour='9', minute='0'))
def daily_kpi_summary():
    """Resumen diario de KPIs de KameCol."""
    ...
```

- Ideal para Mac mini: archivo SQLite local, sin Redis.
- El consumer corre como proceso separado del servidor FastAPI.
- Cubre scheduling, retries y async execution sin overhead.

**Limitaciones:** Sin dashboard web nativo. SQLite serializa writes (límite ~50 tasks/segundo). Sin integración oficial con FastAPI (pero trivial de implementar).

**Decisión: ADOPTAR** — Usar directamente con SqliteHuey.

---

## 3. Evaluación de frameworks adicionales

### 3.1 LangGraph

| Aspecto | Evaluación |
|---------|-----------|
| Stars | ~40,000 |
| Propósito | State machines para agentes con estado |
| Ventaja | Framework más maduro para agentes complejos |
| Problema | Dependencia pesada de LangChain; modelo mental rígido (grafo de nodos) |
| **Decisión** | **Posponer** — Si JARVIS necesita checkpointing complejo en el futuro, reconsiderar |

### 3.2 CrewAI

| Aspecto | Evaluación |
|---------|-----------|
| Propósito | Multi-agentes con roles |
| Problema | Routing mediado por LLM (no determinista); modelo "empleado con rol" no encaja |
| **Decisión** | **Descartar** |

### 3.3 AutoGen (AG2)

| Aspecto | Evaluación |
|---------|-----------|
| Estado | En declive, README redirige a otros proyectos |
| **Decisión** | **Descartar** |

### 3.4 n8n

| Aspecto | Evaluación |
|---------|-----------|
| Propósito | Automatizaciones visuales node-based |
| Ventaja | Excelente para triggers/webhooks no-agentivos |
| Problema | Limitante para el core de agentes AI |
| **Decisión** | **Posponer** — Posible capa de triggers externa en fases posteriores |

### 3.5 Bases de datos vectoriales

| Opción | Latencia (100K vectors) | Setup | Decisión |
|--------|------------------------|-------|----------|
| pgvector | 3-5ms | Si PostgreSQL existe | **Adoptar** (fase posterior) |
| ChromaDB | 8-15ms | Zero config, in-process | **Alternativa MVP** |
| Qdrant | 1-2ms | Docker | **Posponer** (>500K vectores) |

**Recomendación:** Empezar con SQLite + embeddings en archivo para el MVP. Migrar a PostgreSQL + pgvector cuando el volumen de memoria lo justifique.

---

## 4. Patrones arquitectónicos seleccionados para JARVIS

| # | Patrón | Origen | Aplicación en JARVIS |
|---|--------|--------|---------------------|
| 1 | Action/Observation/Executor | OpenHands | Contratos Pydantic tipados para cada tool |
| 2 | Event stream inmutable | OpenHands | Log de eventos como backbone de comunicación |
| 3 | Skills-based tool loading | Sentry MCP | Cargar solo tools del skill activo al contexto |
| 4 | Planner/Executor con modelos distintos | TestZeus | Modelo capaz para razonamiento, barato para ejecución |
| 5 | Single LLM call per action | PR-Agent | Tools que completan en una invocación |
| 6 | Configuration-driven prompts | PR-Agent | Prompts en archivos de configuración, no hardcoded |
| 7 | Dual transport MCP | Playwright/Sentry | stdio para CLI dev, SSE/HTTP para producción |
| 8 | Decorator-based task queue | Huey | `@task()` y `@periodic_task()` para background jobs |
| 9 | Graceful degradation | IAAgent | LLM opcional, todo funciona sin él |
| 10 | Proof generation pipeline | TestZeus | Evidencias automáticas en cada ejecución |

---

## 5. Conclusión

La investigación confirma que **no necesitamos frameworks pesados**. La arquitectura de JARVIS debe ser:

1. **Orquestador propio ligero** (~200-300 líneas) con loop explícito, tool registry y event log.
2. **Playwright MCP** como servidor externo para browser automation.
3. **Huey/SQLite** para background jobs.
4. **Patrones de OpenHands** (Action/Observation) implementados nativamente.
5. **Patrones de PR-Agent** (prompts en config) para skills configurables.
6. **Sin LangGraph, CrewAI, AutoGen ni n8n** en el core.

Esta combinación mantiene la complejidad manejable, las dependencias mínimas y la arquitectura extensible.
