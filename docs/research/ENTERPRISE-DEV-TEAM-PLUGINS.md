# JARVIS — Equipo de Desarrollo Empresarial: Investigacion y Propuesta de Plugins

**v2.0 — Subagentes de Claude Code (sin API externa)**

Fecha: 2026-10-27

---

## 0. Decision Arquitectonica: Subagentes de Claude Code

**Decision:** Los agentes del equipo se implementan como **subagentes de Claude Code** (archivos `.md` en `.claude/agents/`), NO como agentes Python autónomos que necesiten Gemini/Ollama.

**Implicaciones:**

| Aspecto | Antes (v1.0) | Ahora (v2.0) |
|---------|-------------|-------------|
| LLM | Gemini API + Ollama | Claude (incluido en suscripción Max) |
| Costo adicional | ~$5/mes | **$0** |
| Formato | Clases Python (BaseAgent) | Archivos Markdown (`.claude/agents/`) |
| Ejecución | JARVIS standalone (CLI, API, cron) | Dentro de sesiones Claude Code |
| Orquestación | Orchestrator Python + PipelineEngine | Claude Code Agent tool |
| MCP Servers | Los mismos | Los mismos (ya conectados) |
| Herramientas deterministas | iaagent-core analyzers via Python | Invocables via Bash desde subagentes |

**Qué NO cambia:**
- Los MCP servers ya conectados (GitHub, Playwright, MySQL, Mixpanel, etc.)
- Los plugins de Claude Code recomendados
- Los roles y departamentos del equipo
- El Plugin Guardian (sigue validando salud de MCP/plugins)
- Las herramientas deterministas de iaagent-core

**Ubicación de archivos:**
```
jarvis/.claude/
├── agents/           # Subagentes del equipo (NUEVO)
│   ├── req-analyst.md
│   ├── dev-architect.md
│   ├── dev-engineer.md
│   ├── dev-security.md
│   ├── qa-reviewer.md
│   ├── qa-automation.md
│   ├── prod-owner.md
│   ├── ci-retrospective.md
│   └── ...
├── settings.local.json  # Permisos MCP (existente)
└── CLAUDE.md            # Instrucciones del proyecto (si se crea)
```

---

## 1. Resumen Ejecutivo

Este documento presenta la investigacion de los principales frameworks, repositorios y plugins para construir un **equipo de desarrollo empresarial completo** dentro de JARVIS, implementado como subagentes de Claude Code con costo $0 adicional. El objetivo es tener agentes que cubran todo el ciclo de vida del software: requisitos, desarrollo, calidad, producto y mejora continua.

### Alcance

- Investigacion de 8+ repositorios de referencia en GitHub
- Evaluacion de 20+ plugins/MCP servers relevantes
- Propuesta de equipo de 12 agentes especializados
- Implementacion como subagentes Claude Code (`.claude/agents/`)

---

## 2. Repositorios de Referencia Investigados

### 2.1 Tier 1 — Referencia directa (Claude Code nativo)

| Repositorio | Stars | Agentes | Enfoque | URL |
|-------------|-------|---------|---------|-----|
| **aws-samples/sample-claude-code-agent-team** | Alto | 6 roles | Spec-driven development con pools paralelos | [GitHub](https://github.com/aws-samples/sample-claude-code-agent-team) |
| **arnaldo-delisio/claude-code-studio** | Alto | 40+ | Estudio completo con 5 departamentos | [GitHub](https://github.com/arnaldo-delisio/claude-code-studio) |
| **chuckplayer/claude-agent-pack** | Medio | 20 | Pipeline de dev con Obsidian memory | [GitHub](https://github.com/chuckplayer/claude-agent-pack) |
| **pate0304/claude-code-specialized-agents** | Medio | 12 | Roles enterprise IC + leadership | [GitHub](https://github.com/pate0304/claude-code-specialized-agents) |
| **VoltAgent/awesome-claude-code-subagents** | Alto | 161+ | Catalogo exhaustivo por dominio | [GitHub](https://github.com/VoltAgent/awesome-claude-code-subagents) |

### 2.2 Tier 2 — Referencia conceptual (frameworks multi-agente)

| Framework | Stars | Modelo | Enfoque |
|-----------|-------|--------|---------|
| **MetaGPT** | 50k+ | PM → Architect → Engineer → QA | Software company simulation con SOPs |
| **CrewAI** | 25k+ | Crews con roles, tools, memory | Enterprise multi-agent con Flows |
| **ChatDev** | 25k+ | CEO → CTO → CPO → Dev → QA | Comunicacion por chat entre agentes |

### 2.3 Patrones Clave Identificados

**Patron MetaGPT (Sequential SOP):**
```
ProductManager → Architect → ProjectManager → Engineer → QA
   PRD            Design       Tasks           Code      Tests
```

**Patron AWS Agent Team (Spec-Driven Parallel):**
```
FullStack Lead → [spec.md, design.md, tasks.md]
                 → Spawn: 6 coding + 2 devops + 4 review (parallel)
                 → Review cycle (max 3 iterations)
                 → End-to-end verification
```

**Patron claude-agent-pack (Pipeline Gates):**
```
git-engineer → tech-lead → engineers (worktrees) → code-reviewer
→ security-reviewer → performance-reviewer → smell-reviewer
→ test-engineer → merge-reviewer
```

---

## 3. Plugins y MCP Servers Evaluados

### 3.1 Plugins Oficiales de Claude Code (Marketplace)

| Plugin | Installs | Categoria | Relevancia para JARVIS |
|--------|----------|-----------|----------------------|
| **feature-dev** | 89k+ | Development | Pipeline 7 fases para features multi-archivo |
| **pr-review-toolkit** | Alto | QA | 6 agentes de review con confidence scoring |
| **security-guidance** | Alto | Security | Review automatico de OWASP, XSS, SSRF, secrets |
| **commit-commands** | Alto | DevOps | Commits semanticos y changelogs |
| **CLAUDE.md Management** | Alto | Meta | Gestion automatica de contexto de proyecto |

### 3.2 MCP Servers Criticos

| MCP Server | Categoria | Capacidad | Estado en JARVIS |
|------------|-----------|-----------|-----------------|
| **GitHub** | DevOps | PRs, issues, code search, Actions | Ya conectado |
| **Playwright** | QA | Browser automation, screenshots | Ya conectado |
| **Sentry** | Observability | Issues, stack traces, triage | Referenciado (IntegratePIE) |
| **Mixpanel** | Analytics | Eventos, metricas, dashboards | Ya conectado |
| **mysql-qa / mysql-prod** | Database | Queries directos a BDs | Ya conectados |
| **Google Drive** | Docs | Documentacion compartida | Ya conectado |
| **monday.com** | Project Mgmt | Work items, sprints | Disponible |

### 3.3 MCP Servers Recomendados para Incorporar

| MCP Server | Categoria | Para que | Prioridad |
|------------|-----------|----------|-----------|
| **Semgrep** | Security | SAST: vulnerabilidades, bugs, coding standards | P1 |
| **SonarCloud/SonarQube** | Quality | Metricas de calidad, code smells, coverage | P1 |
| **Linear** | Project Mgmt | Tracking de issues/epics (alternativa a Azure DevOps) | P2 |
| **Context7** | Docs | Documentacion tecnica actualizada para agentes | P2 |
| **Serena** | Code Intel | Analisis semantico de codigo | P2 |
| **axe-core** | Accessibility | Testing de accesibilidad web | P3 |
| **Postman** | API Testing | Testing de APIs, colecciones, environments | P3 |

---

## 4. Propuesta: Equipo de Desarrollo Empresarial JARVIS

### 4.1 Filosofia de Diseno

Basado en la arquitectura existente de JARVIS (taxonomia Agente/Skill/Herramienta/Servicio/Workflow del `AGENT-ARCHITECTURE.md`), el equipo sigue estos principios:

1. **No crear agente si un skill basta** — regla de diseno existente de JARVIS
2. **Orquestacion determinista primero** — consistente con el Orchestrator actual (regex + keywords)
3. **LLM solo cuando hay razonamiento** — herramientas deterministas para tareas repetibles
4. **Compatibilidad con BaseAgent** — todos extienden el protocolo existente
5. **Plugin Guardian integrado** — cada agente declara sus plugins/MCP requeridos

### 4.2 Equipo Propuesto: 12 Roles en 5 Departamentos

```
                        +-------------------+
                        |   ORCHESTRATOR    |
                        | (core.orchestrator)|
                        +--------+----------+
                                 |
         +----------+------------+------------+----------+
         |          |            |            |          |
    +----v----+ +---v----+ +----v----+ +----v----+ +---v--------+
    |REQUISITOS| |DESARROLLO| |CALIDAD | |PRODUCTO | |MEJORA      |
    |  (req)   | | (dev)    | | (qa)   | | (prod)  | |CONTINUA    |
    +----+----+ +----+----+ +----+----+ +----+----+ +---+--------+
         |           |           |           |          |
    req.analyst  dev.architect qa.analyzer prod.owner  ci.retrospective
    req.specifier dev.engineer  qa.reviewer prod.metrics ci.tech_debt
                 dev.security  qa.automation            ci.knowledge
```

---

### 4.3 Departamento de Requisitos (`req.*`)

#### 4.3.1 Requirements Analyst (`req.analyst`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Agente (requiere razonamiento) |
| **Responsabilidad** | Analizar user stories, PBIs, criterios de aceptacion; detectar ambiguedades y gaps |
| **Skills** | `parse-user-story`, `detect-gaps`, `extract-acceptance-criteria`, `suggest-edge-cases` |
| **Herramientas** | Azure DevOps client (read), GitHub issues, LLM |
| **MCP Requeridos** | GitHub, monday.com (opcional) |
| **Plugins** | - |
| **Modelo** | Cloud (Gemini) para analisis semantico; local para parsing |
| **Entradas** | `RequirementInput(source, content, project_context)` |
| **Salidas** | `RequirementAnalysis(gaps[], ambiguities[], acceptance_criteria[], edge_cases[])` |
| **Autonomia** | Nivel 1 — Solo analiza y propone |
| **Prioridad** | P2 |
| **Referencia** | MetaGPT ProductManager, claude-agent-pack backlog-auditor |

#### 4.3.2 Spec Writer (`req.specifier`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Skill del Requirements Analyst |
| **Responsabilidad** | Generar especificaciones tecnicas estructuradas a partir de requisitos analizados |
| **Salidas** | `TechnicalSpec(overview, data_model, api_contract, test_criteria, risks)` |
| **Referencia** | AWS agent-team spec.md generation, MetaGPT PRD |
| **Prioridad** | P2 |

---

### 4.4 Departamento de Desarrollo (`dev.*`)

#### 4.4.1 Software Architect (`dev.architect`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Agente (requiere razonamiento sobre trade-offs) |
| **Responsabilidad** | Disenar soluciones tecnicas, evaluar impacto arquitectonico, definir contratos |
| **Skills** | `design-solution`, `evaluate-impact`, `define-contracts`, `review-architecture` |
| **Herramientas** | Repo reader, git tools, dependency analyzer, LLM |
| **MCP Requeridos** | GitHub, Serena (code intelligence) |
| **Plugins** | feature-dev (para workflow de implementacion) |
| **Modelo** | Cloud (Gemini) para decisiones de diseno; local para busquedas |
| **Entradas** | `DesignRequest(requirement, codebase_context, constraints)` |
| **Salidas** | `ArchitectureDecision(design, rationale, trade_offs, implementation_plan, risks)` |
| **Autonomia** | Nivel 1 — Propone diseno, requiere aprobacion |
| **Prioridad** | P2 |
| **Referencia** | MetaGPT Architect, AWS agent-team sa-agent, claude-agent-pack tech-lead |

#### 4.4.2 Software Engineer (`dev.engineer`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Agente (requiere razonamiento para implementacion) |
| **Responsabilidad** | Implementar features, corregir bugs, refactorizar codigo segun especificaciones |
| **Skills** | `implement-feature`, `fix-bug`, `refactor-code`, `write-unit-tests` |
| **Herramientas** | Git tools, filesystem, linters, test runners, LLM |
| **MCP Requeridos** | GitHub |
| **Plugins** | feature-dev, commit-commands |
| **Modelo** | Cloud para implementaciones complejas; local para fixes puntuales |
| **Entradas** | `ImplementationRequest(spec, files_to_modify, acceptance_criteria)` |
| **Salidas** | `Implementation(files_changed[], tests_added[], commit_message)` |
| **Autonomia** | Nivel 2 — Implementa en worktree aislado |
| **Prioridad** | P2 |
| **Referencia** | AWS agent-team coding-agent, MetaGPT Engineer, claude-agent-pack engineers |

#### 4.4.3 Security Engineer (`dev.security`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Skill del Software Engineer + QA Analyzer |
| **Responsabilidad** | Escanear vulnerabilidades, validar compliance, revisar secrets |
| **Herramientas** | Semgrep MCP, security-guidance plugin, OWASP rules |
| **MCP Requeridos** | Semgrep |
| **Plugins** | security-guidance |
| **Salidas** | `SecurityScan(vulnerabilities[], compliance_status, recommendations[])` |
| **Prioridad** | P1 (integrado con QA existente) |
| **Referencia** | claude-agent-pack security-reviewer, security-guidance plugin |

---

### 4.5 Departamento de Calidad (`qa.*`)

#### 4.5.1 QA Analyzer (`qa.analyzer`) — YA EXISTENTE

| Campo | Valor |
|-------|-------|
| **Estado** | Implementado en `src/jarvis/agents/qa/agent.py` |
| **Mejoras propuestas** | Integrar Semgrep MCP, agregar skill de accessibility testing |
| **Nuevos skills** | `scan-accessibility` (axe-core), `validate-api-contract` (Postman) |

#### 4.5.2 Code Reviewer (`qa.reviewer`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Agente (requiere razonamiento multi-dimensional) |
| **Responsabilidad** | Review de PRs con multiples lentes: logica, seguridad, performance, mantenibilidad |
| **Skills** | `review-logic`, `review-performance`, `review-maintainability`, `synthesize-review` |
| **Herramientas** | Git diff, SonarCloud MCP, LLM |
| **MCP Requeridos** | GitHub, SonarCloud |
| **Plugins** | pr-review-toolkit |
| **Modelo** | Cloud para analisis profundo; local para checks mecanicos |
| **Entradas** | `ReviewRequest(pr_id, diff, context, review_depth)` |
| **Salidas** | `CodeReview(findings[], severity_scores, verdict, confidence)` |
| **Autonomia** | Nivel 0 — Solo analiza y reporta |
| **Prioridad** | P1 |
| **Referencia** | AWS agent-team review-agent, claude-agent-pack code-reviewer + smell-reviewer |

**Nota:** Este agente complementa al QA Analyzer existente. El QA Analyzer genera test cases y analiza riesgo; el Code Reviewer se enfoca en la calidad del codigo en si.

#### 4.5.3 Test Automation Agent (`qa.automation`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Agente (requiere razonamiento para estrategia de testing) |
| **Responsabilidad** | Generar y ejecutar tests automatizados, validar cobertura |
| **Skills** | `generate-e2e-tests`, `run-test-suite`, `analyze-coverage`, `suggest-test-strategy` |
| **Herramientas** | Playwright MCP, pytest, coverage tools, LLM |
| **MCP Requeridos** | Playwright |
| **Modelo** | Local para ejecucion de tests; cloud para generacion inteligente |
| **Entradas** | `TestRequest(scope, target_coverage, test_type)` |
| **Salidas** | `TestResult(tests_generated[], coverage_report, failures[], recommendations[])` |
| **Autonomia** | Nivel 2 — Genera y ejecuta tests |
| **Prioridad** | P2 |
| **Referencia** | AWS agent-team testing tiers (T1-T4), claude-agent-pack test-engineer |

---

### 4.6 Departamento de Producto (`prod.*`)

#### 4.6.1 Product Owner Agent (`prod.owner`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Agente (requiere razonamiento sobre prioridades y valor) |
| **Responsabilidad** | Priorizar backlog, evaluar valor de negocio, alinear features con objetivos |
| **Skills** | `prioritize-backlog`, `evaluate-business-value`, `generate-release-notes`, `track-okrs` |
| **Herramientas** | Azure DevOps client, GitHub issues, Mixpanel MCP, LLM |
| **MCP Requeridos** | GitHub, Mixpanel, monday.com |
| **Modelo** | Cloud para analisis de valor; local para priorizacion basica |
| **Entradas** | `BacklogInput(items[], objectives, constraints, metrics)` |
| **Salidas** | `PrioritizedBacklog(ranked_items[], rationale, release_plan)` |
| **Autonomia** | Nivel 1 — Propone priorizacion, requiere aprobacion |
| **Prioridad** | P3 |
| **Referencia** | MetaGPT ProductManager, pate0304 product-owner |

#### 4.6.2 Product Metrics Agent (`prod.metrics`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Skill del Product Owner |
| **Responsabilidad** | Recopilar y analizar metricas de producto (adoption, engagement, errors) |
| **Herramientas** | Mixpanel MCP, Sentry MCP, mysql-prod |
| **MCP Requeridos** | Mixpanel, Sentry, mysql-prod |
| **Salidas** | `ProductMetrics(kpis, trends, anomalies, recommendations)` |
| **Prioridad** | P3 |

---

### 4.7 Departamento de Mejora Continua (`ci.*`)

#### 4.7.1 Retrospective Agent (`ci.retrospective`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Agente (requiere razonamiento sobre patrones y tendencias) |
| **Responsabilidad** | Analizar ciclos de desarrollo, identificar patrones de fallo, proponer mejoras |
| **Skills** | `analyze-sprint`, `identify-patterns`, `generate-action-items`, `track-improvements` |
| **Herramientas** | Event store, Memory Manager, Git log, LLM |
| **MCP Requeridos** | GitHub |
| **Modelo** | Cloud para analisis de tendencias; local para metricas basicas |
| **Entradas** | `RetroInput(period, project, metrics, incidents)` |
| **Salidas** | `RetroReport(patterns[], improvements[], action_items[], metrics_comparison)` |
| **Autonomia** | Nivel 1 — Propone mejoras |
| **Prioridad** | P3 |
| **Referencia** | No hay referencia directa en repos — innovacion JARVIS |

#### 4.7.2 Tech Debt Tracker (`ci.tech_debt`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Skill del Retrospective Agent |
| **Responsabilidad** | Identificar, cuantificar y priorizar deuda tecnica |
| **Herramientas** | SonarCloud MCP, Semgrep, Git history, LLM |
| **MCP Requeridos** | SonarCloud, Semgrep |
| **Salidas** | `TechDebtReport(items[], total_cost_estimate, priority_ranking, remediation_plan)` |
| **Prioridad** | P3 |

#### 4.7.3 Knowledge Agent (`ci.knowledge`)

| Campo | Valor |
|-------|-------|
| **Tipo** | Servicio (ya definido como `core.knowledge_curator` en AGENT-ARCHITECTURE) |
| **Responsabilidad ampliada** | Capturar decisiones de diseno, lecciones aprendidas, y best practices del equipo |
| **Integracion** | Consume outputs de todos los departamentos para enriquecer la base de conocimiento |
| **Prioridad** | P2 (ya planificado) |

---

## 5. Arquitectura de Orquestacion

### 5.1 Modelo de Orquestacion Propuesto

Basado en el analisis de los repos de referencia, JARVIS debe usar un **modelo hibrido**:

```
Nivel 1: Orchestrator Determinista (existente)
         → Routing por regex/keywords a departamentos
         → Sin overhead de LLM para routing simple

Nivel 2: Pipeline Engine (existente)
         → Workflows predefinidos multi-agente
         → Contexto compartido entre steps

Nivel 3: Spec-Driven Orchestration (NUEVO)
         → Para tareas complejas que requieren multiples departamentos
         → Genera spec.md → design.md → tasks.md
         → Spawn paralelo de agentes en tareas independientes
         → Review cycles con max 3 iteraciones
```

### 5.2 Workflows del Equipo

#### Workflow: Feature Development (full cycle)
```
req.analyst (analiza requisito)
  → dev.architect (disena solucion)
    → dev.engineer (implementa, parallel)
      → qa.reviewer (review de codigo)
        → qa.automation (genera/ejecuta tests)
          → qa.analyzer (analisis de riesgo)
            → prod.owner (valida alineacion con objetivos)
              → ci.retrospective (registra metricas del ciclo)
```

#### Workflow: PR Analysis (enhanced — ya parcialmente implementado)
```
qa.analyzer (analisis existente)
  + qa.reviewer (review multi-dimensional)
  + dev.security (scan de seguridad)
  → synthesize → report + evidence
```

#### Workflow: Sprint Retrospective
```
ci.retrospective (analiza periodo)
  + ci.tech_debt (evalua deuda)
  + prod.metrics (metricas de producto)
  → ci.knowledge (almacena lecciones)
  → prod.owner (ajusta backlog)
```

### 5.3 Integracion con Plugin Guardian

El Plugin Guardian existente se extiende para:

1. **Validacion pre-ejecucion:** Antes de ejecutar un agente, verificar que sus MCP/plugins requeridos estan healthy
2. **Degradacion controlada:** Si un MCP no esta disponible, el agente informa que capacidades estan limitadas
3. **Reporte de dependencias:** `jarvis team health` muestra estado de cada agente y sus dependencias

---

## 6. Matriz de Dependencias: Agente → Plugin/MCP

| Agente | MCP Servers | Plugins | Herramientas Internas |
|--------|-------------|---------|----------------------|
| req.analyst | GitHub, monday.com | - | Azure DevOps client, LLM |
| dev.architect | GitHub, Serena | feature-dev | Repo reader, LLM |
| dev.engineer | GitHub | feature-dev, commit-commands | Git tools, linters, LLM |
| dev.security | Semgrep | security-guidance | iaagent SecurityAnalyzer |
| qa.analyzer | GitHub, Playwright | - | iaagent analyzers, LLM |
| qa.reviewer | GitHub, SonarCloud | pr-review-toolkit | Git diff, LLM |
| qa.automation | Playwright | - | pytest, coverage |
| prod.owner | GitHub, Mixpanel, monday.com | - | Azure DevOps, LLM |
| prod.metrics | Mixpanel, Sentry, mysql-prod | - | Analytics tools |
| ci.retrospective | GitHub | - | Event store, Memory, LLM |
| ci.tech_debt | SonarCloud, Semgrep | - | Git history |
| ci.knowledge | - | - | Memory Manager |

---

## 7. Plan de Implementacion

### Fase A — Fortalecer el Core QA (2 semanas)

**Alineado con Fase 6 del MASTER-PLAN**

| Tarea | Agente | Prioridad |
|-------|--------|-----------|
| Integrar Semgrep MCP | dev.security (skill) | P1 |
| Implementar qa.reviewer como agente completo | qa.reviewer | P1 |
| Agregar skill de security scanning al QA Agent | qa.analyzer | P1 |
| Instalar plugin security-guidance | Global | P1 |

### Fase B — Expandir Development (2 semanas)

| Tarea | Agente | Prioridad |
|-------|--------|-----------|
| Implementar dev.architect con design-solution skill | dev.architect | P2 |
| Implementar dev.engineer con implement-feature skill | dev.engineer | P2 |
| Instalar feature-dev y commit-commands plugins | Global | P2 |
| Implementar qa.automation con Playwright | qa.automation | P2 |

### Fase C — Requirements & Product (2 semanas)

| Tarea | Agente | Prioridad |
|-------|--------|-----------|
| Implementar req.analyst con detect-gaps skill | req.analyst | P2 |
| Implementar prod.owner con prioritize-backlog skill | prod.owner | P3 |
| Integrar SonarCloud MCP | qa.reviewer | P2 |
| Configurar monday.com MCP (si aplica) | req.analyst, prod.owner | P3 |

### Fase D — Mejora Continua (2 semanas)

| Tarea | Agente | Prioridad |
|-------|--------|-----------|
| Implementar ci.retrospective | ci.retrospective | P3 |
| Implementar ci.tech_debt como skill | ci.tech_debt | P3 |
| Ampliar ci.knowledge (knowledge curator) | ci.knowledge | P2 |
| Implementar Spec-Driven Orchestration (Nivel 3) | Orchestrator | P3 |

---

## 8. Estimacion de Costos y Recursos

### 8.1 Costo total: $0 adicional

Al usar subagentes de Claude Code, **todo el razonamiento LLM lo cubre la suscripcion Claude Max** (ya pagada por la empresa). No se necesita Gemini API, OpenAI API, ni ningun otro proveedor.

| Recurso | Costo | Notas |
|---------|-------|-------|
| LLM (Claude via Claude Code) | **$0** | Incluido en suscripcion Max |
| Plugins oficiales (feature-dev, security-guidance, etc.) | **$0** | Incluidos con Claude Code |
| MCP Servers (Semgrep, SonarCloud, etc.) | **$0** | Open source |
| Ollama (modelos locales) | **$0** | Solo si JARVIS standalone lo necesita |

### 8.2 Que consume cada subagente

| Operacion | Quien la ejecuta | Costo |
|-----------|------------------|-------|
| PR Analysis | Claude Code → subagente qa-reviewer | Incluido en Max |
| Code Review | Claude Code → subagente qa-reviewer | Incluido en Max |
| Architecture Design | Claude Code → subagente dev-architect | Incluido en Max |
| Requirement Analysis | Claude Code → subagente req-analyst | Incluido en Max |
| Security Scan | Claude Code → subagente dev-security + Semgrep MCP | Incluido en Max |
| Retrospective | Claude Code → subagente ci-retrospective | Incluido en Max |

**Total: $0/mes adicional.**

---

## 9. Comparacion con Repos de Referencia

| Capacidad | JARVIS (propuesto) | AWS Agent Team | claude-code-studio | MetaGPT |
|-----------|-------------------|----------------|-------------------|---------|
| Agentes especializados | 12 | 6 | 40+ | 5 |
| Orquestacion | Hibrida (determinista + spec-driven) | Spec-driven | Agent-first delegation | Sequential SOP |
| Memoria persistente | Si (SQLite + embeddings) | No (session only) | No | No |
| Plugin Guardian | Si (health monitoring) | No | No | No |
| Costo de infra | **$0** (Claude Max) | AWS-dependent | $0 (Claude Max) | API costs |
| Testing tiers | T1-T4 (inspirado AWS) | T1-T4 | No definido | Basic QA |
| Autonomia controlada | Niveles 0-4 con aprobacion | Worktree isolation | Fresh context per agent | Full auto |
| Validacion de resultados | Validation Agent | Review cycles | No | Basic check |
| Trazabilidad | Event stream + evidencias | Verification sentinel | No | No |

**Ventaja competitiva de JARVIS:** Es el unico que combina memoria persistente + plugin guardian + autonomia controlada + trazabilidad completa. Los otros repos son mas "fire and forget".

---

## 10. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|:---:|:---:|-----------|
| Sobre-ingenieria: crear 12 agentes antes de validar valor | Alta | Alto | Implementar en fases, empezar por QA (ya probado) |
| Gemini rate limits con 12 agentes activos | Media | Medio | Routing inteligente + local fallback + cache |
| Plugins de terceros con vulnerabilidades | Baja | Alto | Plugin Guardian + solo plugins oficiales/verificados |
| Complejidad de orquestacion multi-departamento | Media | Medio | Empezar con workflows simples, no spec-driven |
| Duplicacion de logica entre agentes | Media | Medio | Skills compartidos, DRY estricto |

---

## 11. Conclusion y Recomendacion

### Recomendacion: Implementacion incremental en 4 fases

1. **Fase A (inmediata):** Fortalecer QA con `qa.reviewer` + `dev.security` + Semgrep + security-guidance plugin. Esto complementa el QA Agent existente y genera valor inmediato.

2. **Fase B (siguiente):** Agregar desarrollo con `dev.architect` + `dev.engineer` + feature-dev plugin. Habilita el ciclo completo de desarrollo.

3. **Fase C (posterior):** Requisitos y producto con `req.analyst` + `prod.owner`. Cierra el ciclo de upstream.

4. **Fase D (maduracion):** Mejora continua con `ci.retrospective` + spec-driven orchestration. Habilita auto-mejora del equipo.

### Accion inmediata sugerida

Instalar los plugins oficiales de Claude Code que no requieren implementacion de agentes:

```bash
# Plugins de productividad inmediata
claude plugins install @anthropic/security-guidance
claude plugins install @anthropic/pr-review-toolkit
claude plugins install @anthropic/feature-dev
claude plugins install @anthropic/commit-commands
```

Y configurar Semgrep MCP:
```bash
claude mcp add semgrep -- npx -y @anthropic/semgrep-mcp-server
```

Esto da capacidades de equipo empresarial **hoy**, mientras se implementan los agentes custom.

---

## Fuentes

- [aws-samples/sample-claude-code-agent-team](https://github.com/aws-samples/sample-claude-code-agent-team)
- [arnaldo-delisio/claude-code-studio](https://github.com/arnaldo-delisio/claude-code-studio)
- [chuckplayer/claude-agent-pack](https://github.com/chuckplayer/claude-agent-pack)
- [pate0304/claude-code-specialized-agents](https://github.com/pate0304/claude-code-specialized-agents)
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)
- [Best Claude Code Plugins 2026](https://composio.dev/content/top-claude-code-plugins)
- [Best MCP Servers for Developers 2026](https://www.builder.io/blog/best-mcp-servers-2026)
- [MCP Servers for Test Automation 2026](https://www.testmuai.com/blog/mcp-servers-for-test-automation/)
- [Claude Code MCP Plugins Guide](https://www.clarista.io/blog/claude-code-mcp-plugins-guide)
- [CrewAI in Production 2026](https://www.agilesoftlabs.com/blog/2026/06/crewai-in-production-2026-real-lessons)
- [MetaGPT Multi-Agent Framework](https://docs.aiwg.io/pages/references--REF-013-metagpt-multi-agent-framework.html)
- [Claude Code Security](https://anthropic.com/news/claude-code-security)
