# Arquitectura de Agentes JARVIS

**v1.0 — Catálogo de agentes, skills y herramientas**

Fecha: 2026-10-24

---

## 1. Taxonomía de componentes

Antes de definir agentes, es fundamental distinguir los tipos de componentes:

| Tipo | Definición | Ejemplo | Autonomía |
|------|-----------|---------|-----------|
| **Agente** | Componente con capacidad de razonamiento, selección de herramientas y generación de plan | QA Agent | Alta — decide qué hacer |
| **Skill** | Capacidad especializada que un agente puede invocar, con prompt y lógica definidos | "Generar escenarios Gherkin" | Media — ejecuta una tarea definida |
| **Herramienta** | Función determinista que ejecuta una operación específica | DiffAnalyzer, git_diff | Ninguna — ejecuta lo que se le pide |
| **Servicio** | Componente de infraestructura compartido | LLM Router, Memory Manager | Ninguna — sirve solicitudes |
| **Workflow** | Secuencia predefinida de steps | "Analizar PR completo" | Baja — secuencia fija |

**Regla de diseño:** No crear un agente si un skill o herramienta es suficiente. Los agentes implican razonamiento LLM; si la tarea es determinista, debe ser una herramienta.

---

## 2. Core Agents

### 2.1 Orchestrator Agent

| Campo | Valor |
|-------|-------|
| **ID** | `core.orchestrator` |
| **Responsabilidad** | Coordinar solicitudes complejas que requieren múltiples agentes o steps |
| **Objetivo** | Dividir objetivos en tareas, asignar agentes, coordinar ejecución |
| **Datos necesarios** | Solicitud del usuario, contexto de proyecto, historial reciente |
| **Herramientas** | Agent Registry, Tool Registry, Job Engine |
| **Modelo recomendado** | Cloud (Gemini Flash) para planificación compleja; local (Qwen 7B) para routing simple |
| **Memoria** | Episódica (qué se ejecutó antes), procedimental (workflows frecuentes) |
| **Permisos** | Lectura de todos los proyectos; ejecución delegada a agentes especializados |
| **Entradas** | `UserRequest(query, project, context)` |
| **Salidas** | `ExecutionPlan(steps[], agents[], dependencies)` |
| **Dependencias** | Todos los agentes registrados |
| **Riesgos** | Sobre-planificación (dividir en demasiados steps), delegación incorrecta |
| **Criterios de aceptación** | Divide correctamente tareas multi-paso; selecciona el agente correcto >90% |
| **Prioridad** | P0 — Fundamental |
| **Autonomía real** | Nivel 1 (propone plan) → Nivel 3 (coordina con aprobación) |

**Nota de diseño:** Para el MVP, el Orchestrator es un router determinista (regex + keywords). El razonamiento LLM se agrega cuando los patrones simples no sean suficientes.

### 2.2 Validation Agent

| Campo | Valor |
|-------|-------|
| **ID** | `core.validator` |
| **Responsabilidad** | Verificar que los resultados de agentes y herramientas cumplen criterios de calidad |
| **Objetivo** | Prevenir la propagación de resultados incorrectos o incompletos |
| **Datos necesarios** | Resultado del agente, criterios de aceptación de la tarea, evidencias |
| **Herramientas** | Schema validators, diff tools, assertion library |
| **Modelo recomendado** | Local (Qwen 7B) para validaciones estructurales; cloud para validación semántica |
| **Memoria** | Episódica (patrones de fallos anteriores) |
| **Permisos** | Solo lectura |
| **Entradas** | `AgentResult(data, evidence, metadata)` |
| **Salidas** | `ValidationResult(passed, issues[], confidence)` |
| **Dependencias** | Ninguna |
| **Riesgos** | False positives que bloqueen resultados válidos |
| **Criterios de aceptación** | Detecta resultados sin evidencia; identifica datos inventados |
| **Prioridad** | P1 — Alta |
| **Autonomía real** | Nivel 0 — Solo analiza, no modifica |

---

## 3. QA Intelligence Agents

### 3.1 QA Agent (Principal)

| Campo | Valor |
|-------|-------|
| **ID** | `qa.analyzer` |
| **Responsabilidad** | Análisis integral de PRs: código, seguridad, riesgo, test cases |
| **Objetivo** | Producir análisis QA verificable para PRs de Azure DevOps |
| **Datos necesarios** | PR data (diffs, archivos, metadata), contexto de proyecto, reglas de negocio |
| **Herramientas** | `iaagent-core` (6 analyzers + 3 generators), Azure DevOps client, Git tools |
| **Modelo recomendado** | Determinista (analyzers) + Cloud (Gemini Flash) para enrichment |
| **Memoria** | Episódica (análisis previos del mismo repo), semántica (reglas de negocio), de proyecto (arquitectura) |
| **Permisos** | Lectura Azure DevOps, lectura de repositorios |
| **Entradas** | `PRAnalysisRequest(pr_id, project, depth)` |
| **Salidas** | `QAReport(findings, test_cases, risk_score, gherkin_scenarios, evidence)` |
| **Dependencias** | Azure DevOps connectivity, iaagent-core |
| **Riesgos** | Análisis incorrecto de reglas de negocio; falsos positivos en seguridad |
| **Criterios de aceptación** | Detecta vulnerabilidades OWASP Top 10; genera test cases trazables; produce evidencias verificables |
| **Prioridad** | P0 — Fundamental (MVP) |
| **Autonomía real** | Nivel 2 — Ejecuta análisis, propone resultados |

**Skills del QA Agent:**

| Skill | Tipo | Descripción | Fuente |
|-------|------|-------------|--------|
| `analyze-diff` | Herramienta | Clasificar archivos modificados | iaagent-core DiffAnalyzer |
| `scan-security` | Herramienta | Detectar vulnerabilidades OWASP | iaagent-core SecurityAnalyzer |
| `scan-static` | Herramienta | TODOs, debug code, secrets | iaagent-core StaticAnalyzer |
| `analyze-dependencies` | Herramienta | Cambios en manifests | iaagent-core DependencyAnalyzer |
| `assess-impact` | Herramienta | Áreas impactadas | iaagent-core ImpactAnalyzer |
| `calculate-risk` | Herramienta | Score de riesgo 0-10 | iaagent-core RiskEngine |
| `generate-test-cases` | Skill | Test cases en 7 categorías | iaagent-core TestCaseGenerator + LLM |
| `generate-gherkin` | Skill | Escenarios BDD | LLM con template |
| `enrich-analysis` | Skill | Análisis profundo con contexto | LLM (Gemini Flash / modelo local) |
| `generate-report` | Herramienta | Reporte QA estructurado | iaagent-core ReportGenerator |

### 3.2 Evidence Collector

| Campo | Valor |
|-------|-------|
| **ID** | `qa.evidence_collector` |
| **Responsabilidad** | Recopilar y organizar evidencias de ejecuciones |
| **Tipo real** | **Skill** del QA Agent (no agente independiente) |
| **Herramientas** | Playwright MCP (screenshots, PDFs), filesystem |
| **Salidas** | `EvidenceBundle(screenshots, logs, reports, metadata)` |
| **Prioridad** | P1 |

### 3.3 Azure DevOps Publisher

| Campo | Valor |
|-------|-------|
| **ID** | `qa.publisher` |
| **Responsabilidad** | Publicar resultados QA como comentarios en PRs de Azure DevOps |
| **Tipo real** | **Skill** del QA Agent con aprobación humana obligatoria |
| **Herramientas** | Azure DevOps client (write) |
| **Permisos** | Escritura en Azure DevOps — **requiere aprobación explícita por cada publicación** |
| **Entradas** | `PublishRequest(pr_id, comment, evidence, approval_token)` |
| **Controles** | Verificar PR correcto, adjuntar evidencias, distinguir "ejecutado" de "propuesto" |
| **Prioridad** | P2 (después del MVP) |
| **Autonomía** | Nivel 2 — Prepara; Nivel 3 — Publica solo con aprobación |

---

## 4. Developer Agents

### 4.1 Code Analyst

| Campo | Valor |
|-------|-------|
| **ID** | `dev.code_analyst` |
| **Responsabilidad** | Analizar estructura, patrones y calidad de código |
| **Tipo real** | **Agente** (requiere razonamiento sobre código) |
| **Herramientas** | Git tools, filesystem, grep/glob, LLM |
| **Modelo recomendado** | Cloud para análisis profundo; local para búsquedas simples |
| **Memoria** | De proyecto (arquitectura, convenciones), semántica (patrones) |
| **Permisos** | Lectura de repositorios autorizados |
| **Salidas** | `CodeAnalysis(structure, patterns, issues, suggestions)` |
| **Prioridad** | P2 |

### 4.2 Documentation Agent

| Campo | Valor |
|-------|-------|
| **ID** | `dev.documenter` |
| **Tipo real** | **Skill** del Code Analyst |
| **Responsabilidad** | Generar/actualizar documentación técnica |
| **Prioridad** | P3 |

**Nota:** Los agentes de developer son posteriores al MVP. Las capacidades existentes de IAAgent cubren code review como parte del análisis QA.

---

## 5. KameCol Business Agents

### 5.1 Customer Support Agent

| Campo | Valor |
|-------|-------|
| **ID** | `biz.customer_support` |
| **Responsabilidad** | Responder consultas de clientes sobre productos, pedidos y disponibilidad |
| **Objetivo** | Automatizar atención al cliente de KameCol via WhatsApp |
| **Datos necesarios** | Catálogo de productos, estado de pedidos, políticas de envío |
| **Herramientas** | KameCol API (público), WhatsApp Business API (futuro) |
| **Modelo recomendado** | Local (Qwen 7B) para consultas simples de catálogo; cloud para consultas complejas |
| **Memoria** | Conversacional (historial del cliente), semántica (catálogo, políticas) |
| **Permisos** | Lectura KameCol APIs públicas; lectura admin con credenciales |
| **Entradas** | `CustomerQuery(message, customer_id, channel)` |
| **Salidas** | `CustomerResponse(message, products[], order_status, escalation_needed)` |
| **Dependencias** | KameCol API disponible, WhatsApp Business API configurado |
| **Riesgos** | Información incorrecta de stock/precios (mitigado: KameCol recalcula server-side) |
| **Criterios de aceptación** | Responde correctamente consultas de catálogo; escala a humano cuando no puede resolver |
| **Prioridad** | P3 (post-MVP, requiere WhatsApp Business API) |
| **Autonomía** | Nivel 1 (solo responde) → Nivel 2 (ejecuta consultas) |

### 5.2 Sales Analytics Agent

| Campo | Valor |
|-------|-------|
| **ID** | `biz.sales_analytics` |
| **Tipo real** | **Skill** que consume endpoints de dashboard de KameCol |
| **Responsabilidad** | Generar resúmenes y alertas de métricas comerciales |
| **Herramientas** | KameCol admin API (dashboard KPIs, analytics) |
| **Prioridad** | P3 |

### 5.3 Order Recovery Agent

| Campo | Valor |
|-------|-------|
| **ID** | `biz.order_recovery` |
| **Tipo real** | **Workflow** automatizado (no requiere razonamiento LLM) |
| **Responsabilidad** | Recuperar pedidos con pago pendiente |
| **Herramientas** | KameCol admin API (pending-recovery, send-reminder) |
| **Controles** | Rate limit 1 recordatorio/24h por orden (ya implementado en KameCol) |
| **Prioridad** | P3 |

---

## 6. Knowledge Agents

### 6.1 Knowledge Curator

| Campo | Valor |
|-------|-------|
| **ID** | `core.knowledge_curator` |
| **Tipo real** | **Servicio** (proceso periódico, no agente conversacional) |
| **Responsabilidad** | Proponer incorporación y actualización de conocimiento persistente |
| **Herramientas** | Memory Manager, document parser, embedding generator |
| **Criterios** | Solo incorpora conocimiento con fuente verificable y fecha |
| **Prioridad** | P2 |

### 6.2 Knowledge Auditor

| Campo | Valor |
|-------|-------|
| **ID** | `core.knowledge_auditor` |
| **Tipo real** | **Skill** periódico del Knowledge Curator |
| **Responsabilidad** | Validar vigencia, consistencia y procedencia del conocimiento |
| **Prioridad** | P2 |

---

## 7. Resumen de componentes por tipo

### Agentes reales (requieren razonamiento LLM)

| Agente | Proyecto | Prioridad | MVP |
|--------|----------|-----------|-----|
| Orchestrator | Core | P0 | Si (determinista) |
| QA Agent | IntegratePIE | P0 | Si |
| Validation Agent | Core | P1 | No |
| Code Analyst | General | P2 | No |
| Customer Support | KameCol | P3 | No |

### Skills (capacidades invocables por agentes)

| Skill | Agente padre | Fuente |
|-------|-------------|--------|
| analyze-diff | QA Agent | iaagent-core |
| scan-security | QA Agent | iaagent-core |
| generate-test-cases | QA Agent | iaagent-core + LLM |
| generate-gherkin | QA Agent | LLM |
| enrich-analysis | QA Agent | LLM |
| publish-to-azdo | QA Agent | Azure DevOps client |
| collect-evidence | QA Agent | Playwright MCP |
| generate-docs | Code Analyst | LLM |
| analyze-kpis | Sales Analytics | KameCol API |
| audit-knowledge | Knowledge Curator | Memory Manager |

### Herramientas (deterministas, sin LLM)

| Herramienta | Tipo | Origen |
|-------------|------|--------|
| DiffAnalyzer | Informativa | iaagent-core |
| StaticAnalyzer | Informativa | iaagent-core |
| SecurityAnalyzer | Informativa | iaagent-core |
| DependencyAnalyzer | Informativa | iaagent-core |
| ImpactAnalyzer | Informativa | iaagent-core |
| RiskEngine | Analítica | iaagent-core |
| TestCaseGenerator | Analítica | iaagent-core |
| ReportGenerator | Analítica | iaagent-core |
| CommentGenerator | Propositiva | iaagent-core |
| Git tools | Informativa | Nuevo |
| Filesystem reader | Informativa | Nuevo |
| Azure DevOps client | Informativa/Ejecutiva | iaagent-core |
| KameCol API client | Informativa | Nuevo |
| Playwright MCP | Ejecutiva | Externo (npm) |

### Workflows (secuencias predefinidas)

| Workflow | Steps | Trigger |
|----------|-------|---------|
| full-pr-analysis | fetch PR → analyzers → LLM enrich → report → evidence | `jarvis analyze-pr` |
| order-recovery | fetch pending → filter → send reminder | Periódico (Huey) |
| daily-kpi-summary | fetch KPIs → generate summary → notify | Periódico (Huey) |
| knowledge-audit | scan KB → check dates → flag stale → report | Semanal (Huey) |

---

## 8. Contratos de comunicación inter-agente

### 8.1 Formato estándar

Toda comunicación entre agentes usa JSON estructurado (patrón de TestZeus Hercules):

```python
@dataclass(frozen=True)
class AgentMessage:
    from_agent: str
    to_agent: str
    message_type: str          # "request", "response", "delegation"
    payload: dict
    correlation_id: str        # Para trazar la conversación
    project_context: str
    timestamp: datetime
```

### 8.2 Delegación

Cuando el Orchestrator delega a un agente especializado:

```json
{
    "from_agent": "core.orchestrator",
    "to_agent": "qa.analyzer",
    "message_type": "request",
    "payload": {
        "task": "analyze_pr",
        "pr_id": 1234,
        "project": "integratepie",
        "depth": "full",
        "memory_context": ["episodic:last_analysis_1233", "semantic:fur_rules"]
    },
    "correlation_id": "job-2026-10-24-001"
}
```

---

## 9. Niveles de autonomía por agente

| Nivel | Descripción | Agentes |
|-------|-------------|---------|
| 0 — Consulta | Solo responde y analiza | Validation Agent |
| 1 — Propuesta | Genera planes y recomendaciones | Orchestrator (MVP), Customer Support (MVP) |
| 2 — Ejecución controlada | Ejecuta herramientas seguras | QA Agent, Code Analyst |
| 3 — Coordinación | Coordina acciones, pide aprobación | Orchestrator (posterior), Publisher |
| 4 — Delegada | Ejecuta tareas recurrentes dentro de límites | Order Recovery (posterior) |

**Progresión:** Cada agente comienza en el nivel más bajo viable y sube cuando hay evidencia de confiabilidad (métricas de éxito, validación humana positiva).
