# Evaluación de Reutilización de IAAgent

**JARVIS — Assessment técnico para decisión estratégica**

Fecha: 2026-10-24

---

## 1. Contexto

IAAgent es un agente de QA automatizado en producción (v0.1.0) que ha procesado exitosamente 38+ PRs de Azure DevOps. Este documento evalúa las alternativas para incorporar sus capacidades en JARVIS.

---

## 2. Estado actual de IAAgent

### 2.1 Arquitectura

IAAgent es un **pipeline lineal de 10 etapas**, no una arquitectura multiagente:

```
CLI (Typer)
  → Config
  → AzureDevOpsClient (leer PR, diffs, archivos)
  → TrelloClient (opcional)
  → build_pr_context() → PRContext
  → run_analysis(PRContext) → 10 etapas secuenciales:
      1. DiffAnalyzer
      2. StaticAnalyzer
      3. SecurityAnalyzer
      4. DependencyAnalyzer
      5. ImpactAnalyzer
      6. RiskEngine
      7. LLM Enrichment (opcional)
      8. TestCaseGenerator
      9. ReportGenerator
      10. CommentGenerator
  → write_structured_outputs() → 4 archivos .md
  → (opcional) post_pr_comment_from_file() → Azure DevOps
```

### 2.2 Inventario de código

| Módulo | Archivos | Líneas | Función |
|--------|----------|--------|---------|
| `agent/models/` | 3 | ~600 | PRContext, Finding, RiskScore, TestCase, QAReport (frozen dataclasses) |
| `agent/analyzers/` | 6 | ~2,500 | Análisis programático (regex, patterns) |
| `agent/generators/` | 3 | ~1,200 | Formateo de reportes y test cases |
| `agent/llm/` | 5 | ~1,800 | Abstracción LLM con fallback triple |
| `agent/` (root) | 8 | ~2,400 | Config, pipeline, Azure DevOps, Trello, sanitize, filesystem |
| `.claude/commands/` | 16 | ~3,200 | Skills como prompts markdown |
| `knowledge/` | 5 | ~1,500 | Knowledge base estática |
| Dead code | 3 | ~1,444 | gemini_client, context_pack, prompt_builder |
| **Total productivo** | ~28 | **~10,000** | |

### 2.3 Fortalezas confirmadas

- **Producción real:** 38+ PRs analizados exitosamente.
- **Graceful degradation:** LLM opcional. Todo funciona sin él.
- **Fallback triple:** Claude Code → Claude API → Gemini (detección automática en runtime).
- **Modelos tipados:** Frozen dataclasses como vocabulario consistente.
- **Separación de concerns:** Data collection / analysis / output completamente desacoplados.
- **Azure DevOps client maduro:** 1,018 líneas, multi-repo, manejo de errores.
- **Security detection:** 14+ patrones OWASP con evidencia de uso real.
- **74 tests pytest** que protegen regresiones.

### 2.4 Limitaciones

- **Stateless total:** Ninguna memoria entre sesiones.
- **Pipeline fijo:** 10 etapas secuenciales, sin routing condicional.
- **Single-shot LLM:** Una sola llamada por PR.
- **Solo CLI:** Sin HTTP server, webhooks ni API.
- **Solo Azure DevOps:** No soporta GitHub/GitLab.
- **Prompt hardcoded:** `_build_enrichment_prompt()` en español para Laravel/PHP.
- **Sin async:** Todo sincrónico.
- **pyproject.toml incompleto:** Declara 4 de 36 dependencias.

---

## 3. Alternativas evaluadas

### Alternativa A — Transformar IAAgent en JARVIS

Evolucionar el repositorio IAAgent directamente para convertirlo en JARVIS.

| Aspecto | Evaluación |
|---------|-----------|
| Complejidad | **Alta** — Requiere reescribir la arquitectura completa manteniendo compatibilidad |
| Reutilización | 100% del código existente (pero mucho debe cambiar) |
| Riesgo | **Alto** — Romper funcionalidad QA probada durante la transformación |
| Tiempo estimado | 6-8 semanas antes de tener JARVIS funcional |
| Acoplamiento | Máximo — JARVIS hereda toda la deuda técnica de IAAgent |
| Multi-dominio | Difícil — La estructura está orientada solo a QA de PRs |
| Mantenibilidad | Baja — Un repositorio con dos propósitos conflictivos |

**Veredicto: NO RECOMENDADA.** El costo de transformar un pipeline lineal en una plataforma multiagente es mayor que construir el core nuevo. Riesgo alto de regresiones en funcionalidad QA probada.

### Alternativa B — Crear JARVIS reutilizando módulos

Crear JARVIS como repositorio nuevo, copiando módulos selectos de IAAgent.

| Aspecto | Evaluación |
|---------|-----------|
| Complejidad | **Media** — Extraer y adaptar módulos |
| Reutilización | ~64% del código productivo (categorías A+B) |
| Riesgo | **Medio** — Fork implica mantener dos copias del mismo código |
| Tiempo estimado | 3-4 semanas para MVP con QA básico |
| Acoplamiento | Bajo inicialmente, pero crece si ambos evolucionan |
| Multi-dominio | Libre — JARVIS nace con arquitectura propia |
| Mantenibilidad | Media — Riesgo de divergencia entre las dos copias |

**Veredicto: VIABLE pero subóptima.** La copia de módulos crea deuda técnica de mantenimiento cuando IAAgent y JARVIS evolucionan independientemente.

### Alternativa C — Mantener IAAgent como servicio independiente

IAAgent sigue operando como está. JARVIS lo llama como servicio externo via CLI o API.

| Aspecto | Evaluación |
|---------|-----------|
| Complejidad | **Baja** — No se modifica IAAgent |
| Reutilización | 0% — JARVIS no aprovecha el código, solo los resultados |
| Riesgo | **Bajo** — Cada sistema evoluciona independientemente |
| Tiempo estimado | 1 semana para integrar como servicio |
| Acoplamiento | Mínimo — Solo contrato de I/O |
| Multi-dominio | JARVIS libre, IAAgent aislado |
| Mantenibilidad | Alta para cada sistema, pero JARVIS duplica capacidades QA |

**Veredicto: VIABLE pero desperdicia oportunidad.** JARVIS terminaría reconstruyendo capacidades QA que ya existen en IAAgent (analyzers, security patterns, risk engine).

### Alternativa D — IAAgent como módulo especializado de JARVIS (RECOMENDADA)

JARVIS como núcleo nuevo con arquitectura propia. IAAgent se refactoriza gradualmente como paquete Python importable que JARVIS consume como módulo QA.

| Aspecto | Evaluación |
|---------|-----------|
| Complejidad | **Media** — Empaquetar IAAgent como librería |
| Reutilización | ~64% directa + evolución coordinada |
| Riesgo | **Medio-bajo** — IAAgent sigue funcionando como CLI durante transición |
| Tiempo estimado | 2-3 semanas para MVP, IAAgent empaquetado en paralelo |
| Acoplamiento | Controlado — Interfaces definidas entre módulo QA y core |
| Multi-dominio | Libre — JARVIS nace con arquitectura multiagente |
| Mantenibilidad | Alta — Un solo lugar para lógica QA, evoluciona coordinadamente |

**Veredicto: RECOMENDADA.** Maximiza reutilización mientras permite a JARVIS innovar en las dimensiones donde IAAgent tiene cero cobertura (memoria, multiagente, multi-dominio).

---

## 4. Comparación resumida

| Criterio | A (Transformar) | B (Copiar) | C (Servicio) | **D (Módulo)** |
|----------|:---:|:---:|:---:|:---:|
| Reutilización de código | Alta (con riesgo) | Alta | Nula | **Alta** |
| Preserva QA funcional | Riesgo alto | Sí | Sí | **Sí** |
| Arquitectura limpia | No | Parcial | Sí | **Sí** |
| Tiempo al MVP | Lento | Medio | Rápido | **Medio** |
| Mantenibilidad a largo plazo | Baja | Media | Alta (pero duplica) | **Alta** |
| Evolución coordinada | N/A | Diverge | Independiente | **Coordinada** |
| Riesgo general | Alto | Medio | Bajo | **Medio-bajo** |

---

## 5. Plan de ejecución de la Alternativa D

### Fase 1 — Coexistencia (semanas 1-2)

1. Crear repositorio JARVIS con arquitectura propia.
2. IAAgent sigue funcionando como CLI independiente.
3. JARVIS importa directamente archivos de IAAgent via path o git submodule temporal.
4. Definir interfaces Pydantic para los contratos entre módulos.

### Fase 2 — Empaquetamiento (semanas 3-4)

1. Refactorizar IAAgent en paquete instalable (`iaagent-core`):
   - `iaagent_core/analyzers/` — Los 6 analyzers
   - `iaagent_core/generators/` — Los 3 generators
   - `iaagent_core/llm/` — Provider abstraction
   - `iaagent_core/models/` — Dataclasses tipados
   - `iaagent_core/integrations/` — Azure DevOps, Trello
   - `iaagent_core/utils/` — Sanitize, filesystem, logging
2. IAAgent CLI se convierte en thin wrapper sobre `iaagent-core`.
3. JARVIS instala `iaagent-core` como dependencia.

### Fase 3 — Integración (semanas 5-6)

1. JARVIS QA Agent delega análisis a `iaagent-core`.
2. JARVIS agrega: memoria de análisis previos, routing dinámico, HTTP API.
3. IAAgent CLI sigue funcionando para uso directo.

### Componentes de IAAgent clasificados por destino

**Se mueven a `iaagent-core` (reutilizables):**

```
agent/models/enums.py          → iaagent_core/models/
agent/models/pr_context.py     → iaagent_core/models/
agent/models/analysis.py       → iaagent_core/models/
agent/analyzers/*.py           → iaagent_core/analyzers/
agent/generators/*.py          → iaagent_core/generators/
agent/llm/base.py              → iaagent_core/llm/
agent/llm/factory.py           → iaagent_core/llm/
agent/llm/claude_code.py       → iaagent_core/llm/
agent/llm/claude.py            → iaagent_core/llm/
agent/llm/gemini.py            → iaagent_core/llm/
agent/azure_devops.py          → iaagent_core/integrations/
agent/trello.py                → iaagent_core/integrations/
agent/sanitize.py              → iaagent_core/utils/
agent/filesystem.py            → iaagent_core/utils/
agent/logging_config.py        → iaagent_core/utils/
```

**Permanecen en IAAgent CLI (wrappers):**

```
agent/pipeline.py              → IAAgent CLI (orquesta iaagent-core)
agent/cli.py                   → IAAgent CLI
agent/config.py                → IAAgent CLI (+ versión expandida en JARVIS)
agent/output_writer.py         → IAAgent CLI
```

**Se eliminan (dead code):**

```
agent/gemini_client.py         → Eliminar
agent/context_pack.py          → Eliminar
agent/prompt_builder.py        → Eliminar
```

**Se trasladan a JARVIS (referencia conceptual):**

```
agent/llm/enrichment.py        → JARVIS reimplementa con prompts dinámicos
.claude/commands/*.md           → JARVIS adapta como templates de skills
knowledge/*.md                  → JARVIS incorpora a su knowledge base
```

---

## 6. Riesgos de la Alternativa D

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|:---:|:---:|-----------|
| Refactorizar IAAgent rompe funcionalidad QA existente | Media | Alto | Tests de regresión antes y después del refactor |
| Interfaces entre módulo y core resultan inadecuadas | Media | Medio | Diseñar contratos Pydantic antes de implementar |
| El empaquetamiento toma más de lo estimado | Media | Bajo | Fase 1 funciona sin empaquetamiento formal |
| IAAgent evoluciona y diverge del módulo | Baja | Medio | Un solo equipo (el usuario) mantiene ambos |

---

## 7. Decisión

**Se recomienda la Alternativa D: IAAgent como módulo especializado de JARVIS.**

Fundamentos:
1. Maximiza reutilización del 64% del código productivo probado en producción.
2. Preserva la funcionalidad QA durante la transición.
3. Permite a JARVIS nacer con arquitectura multiagente limpia.
4. IAAgent CLI sigue operativo como herramienta independiente.
5. La evolución es coordinada, no divergente.

Esta decisión se formaliza en el ADR-001.
