# JARVIS — Backlog Técnico

**v1.0**

Fecha: 2026-10-24

---

## Convenciones

**Prioridades:**
- **P0** — Fundamental (bloquea el MVP)
- **P1** — Alta (necesario para QA funcional)
- **P2** — Media (mejora significativa)
- **P3** — Posterior (nice to have)

**Estado:** Pendiente | En progreso | Completado

---

## Fase 1 — JARVIS Core

| ID | Historia / Tarea | Prioridad | Dependencias | Criterios de aceptación |
|----|-----------------|:---------:|:------------:|------------------------|
| J-001 | Inicializar repositorio Git | P0 | — | `git init`, `.gitignore`, primer commit |
| J-002 | Crear entorno virtual Python 3.12+ | P0 | J-001 | `python -m venv .venv`, activación documentada |
| J-003 | Configurar `pyproject.toml` con dependencias mínimas | P0 | J-002 | `pip install -e .` funciona, deps: typer, rich, pydantic |
| J-004 | Crear estructura de directorios del MVP | P0 | J-003 | Directorios `src/jarvis/`, `tests/`, `config/`, `data/` |
| J-005 | Implementar CLI básico con Typer | P0 | J-004 | `jarvis ask "hola"` responde, `jarvis version` funciona |
| J-006 | Implementar modelos Pydantic core | P0 | J-004 | Event, ProjectContext, ToolAction, ToolObservation definidos |
| J-007 | Implementar Event Stream en SQLite | P0 | J-006 | Eventos se persisten, tabla `events` creada, append-only |
| J-008 | Implementar sistema de configuración TOML | P0 | J-004 | Archivos TOML se cargan, config por proyecto funciona |
| J-009 | Implementar ProjectContext y SecurityGate | P0 | J-006 | Contexto de proyecto se valida, namespace enforcement |
| J-010 | Implementar `.env.example` y manejo de env vars | P0 | J-004 | Variables documentadas, `python-dotenv` configurado |
| J-011 | Escribir tests unitarios para core | P0 | J-007 | pytest con >80% cobertura de core |
| J-012 | Configurar pytest y estructura de tests | P0 | J-003 | `pytest` corre, conftest.py configurado |

---

## Fase 2 — Motor de IA Híbrida

| ID | Historia / Tarea | Prioridad | Dependencias | Criterios de aceptación |
|----|-----------------|:---------:|:------------:|------------------------|
| J-020 | Implementar LLM Provider Protocol | P0 | J-006 | Protocol con métodos generate(), is_available() |
| J-021 | Implementar OllamaProvider | P0 | J-020 | Genera respuestas con Qwen 2.5 vía Ollama API |
| J-022 | Integrar GeminiProvider de IAAgent | P0 | J-020 | Genera respuestas con Gemini Flash, retry con backoff |
| J-023 | Implementar LLM Router | P0 | J-021, J-022 | Selecciona provider según complejidad y política |
| J-024 | Implementar tracking de consumo (llm_usage) | P0 | J-023, J-007 | Tokens, costos, latencia registrados en SQLite |
| J-025 | Implementar fallback controlado | P0 | J-023 | Fallback respeta políticas de privacidad |
| J-026 | Implementar CLI `jarvis costs` | P1 | J-024 | Muestra resumen por provider y período |
| J-027 | Implementar configuración de políticas por proyecto | P0 | J-008 | TOML por proyecto, allowed_providers configurable |
| J-028 | Tests para LLM Router y providers | P0 | J-023 | Mocks de providers, routing correcto, fallback testeado |

---

## Fase 3 — Memoria Persistente

| ID | Historia / Tarea | Prioridad | Dependencias | Criterios de aceptación |
|----|-----------------|:---------:|:------------:|------------------------|
| J-030 | Diseñar schema SQLite para memoria | P0 | J-007 | Tabla memory + FTS5, índices creados |
| J-031 | Implementar Memory Store (CRUD) | P0 | J-030 | Create, read, update, delete de registros |
| J-032 | Implementar FTS5 search | P0 | J-031 | Búsqueda de texto completo funcional |
| J-033 | Integrar embeddings con nomic-embed-text | P0 | J-021, J-031 | Embeddings generados vía Ollama, almacenados como BLOB |
| J-034 | Implementar búsqueda semántica (cosine similarity) | P0 | J-033 | Búsqueda por similaridad retorna top-K relevantes |
| J-035 | Implementar búsqueda híbrida (FTS + semantic) | P1 | J-032, J-034 | Combinación ponderada de scores |
| J-036 | Implementar namespace isolation | P0 | J-031, J-009 | Queries filtran por proyecto obligatoriamente |
| J-037 | Implementar Memory Manager | P0 | J-035, J-036 | Interfaz unificada para almacenar/buscar/inyectar contexto |
| J-038 | Implementar CLI `jarvis memory add/search/list` | P0 | J-037 | Comandos funcionales |
| J-039 | Implementar inyección de memoria en prompts | P1 | J-037, J-023 | `jarvis ask` con contexto de memoria incluido |
| J-040 | Tests de aislamiento de memoria | P0 | J-036 | Test que verifica que cross-project access falla |
| J-041 | Tests de persistencia entre sesiones | P0 | J-037 | Almacenar → cerrar → reabrir → recuperar |

---

## Fase 4 — Sistema de Agentes

| ID | Historia / Tarea | Prioridad | Dependencias | Criterios de aceptación |
|----|-----------------|:---------:|:------------:|------------------------|
| J-050 | Implementar Agent Protocol y base class | P1 | J-006 | Protocol con execute(), describe() |
| J-051 | Implementar Agent Registry | P1 | J-050 | Registro dinámico de agentes |
| J-052 | Implementar Tool Protocol y Registry | P1 | J-006 | Action/Observation contracts, registro de tools |
| J-053 | Implementar Orchestrator determinista | P1 | J-051, J-052 | Routing por regex + keywords |
| J-054 | Integrar Huey para background jobs | P1 | J-007 | SqliteHuey configurado, worker funcional |
| J-055 | Implementar worker process | P1 | J-054 | `jarvis-worker` ejecuta jobs en background |
| J-056 | Implementar agente de prueba | P1 | J-053 | Echo agent que demuestra el flujo completo |
| J-057 | Tests del sistema de agentes | P1 | J-056 | Registry, routing, ejecución testeados |

---

## Fase 5 — Reutilización de IAAgent

| ID | Historia / Tarea | Prioridad | Dependencias | Criterios de aceptación |
|----|-----------------|:---------:|:------------:|------------------------|
| J-060 | Empaquetar iaagent-core como paquete Python | P1 | J-052 | pyproject.toml, instalable con pip |
| J-061 | Integrar DiffAnalyzer como tool | P1 | J-060 | Produce mismos resultados que en IAAgent |
| J-062 | Integrar SecurityAnalyzer como tool | P1 | J-060 | 14+ patrones OWASP funcionando |
| J-063 | Integrar StaticAnalyzer como tool | P1 | J-060 | TODOs, debug code, secrets detectados |
| J-064 | Integrar RiskEngine como tool | P1 | J-060 | Score 0-10 calculado correctamente |
| J-065 | Integrar TestCaseGenerator | P1 | J-060 | 7 categorías de test cases generados |
| J-066 | Integrar ReportGenerator | P1 | J-060 | Reporte QA completo generado |
| J-067 | Integrar Azure DevOps client | P1 | J-060 | Lectura de PRs funcional |
| J-068 | Integrar GeminiProvider de iaagent-core | P1 | J-060, J-022 | Provider reutilizado sin duplicación |
| J-069 | Tests de regresión cruzados | P1 | J-061-J-068 | Tests de IAAgent pasan dentro de JARVIS |

---

## Fase 6 — QA Intelligence

| ID | Historia / Tarea | Prioridad | Dependencias | Criterios de aceptación |
|----|-----------------|:---------:|:------------:|------------------------|
| J-070 | Implementar QA Agent | P1 | J-056, J-069 | Agente con skills de análisis QA |
| J-071 | Implementar workflow full-pr-analysis | P1 | J-070 | Fetch → analyze → enrich → report → evidence |
| J-072 | Implementar memoria episódica de análisis | P1 | J-070, J-037 | Análisis previos recuperables |
| J-073 | Implementar Evidence Collector | P1 | J-070 | Evidencias almacenadas con metadata |
| J-074 | Implementar CLI `jarvis analyze-pr` | P1 | J-071 | Comando funcional con output formateado |
| J-075 | Integrar conocimiento de negocio PIE | P2 | J-037 | Reglas de negocio en memory semántica |
| J-076 | Tests de QA Agent con PR real | P1 | J-074 | Análisis de PR produce reporte completo |

---

## Fase 7 — IntegratePIE Connector

| ID | Historia / Tarea | Prioridad | Dependencias | Criterios de aceptación |
|----|-----------------|:---------:|:------------:|------------------------|
| J-080 | Extender Azure DevOps client para work items | P2 | J-067 | Lectura de PBI, bugs, tasks |
| J-081 | Implementar extracción de criterios de aceptación | P2 | J-080 | Criterios parseados y disponibles |
| J-082 | Implementar Azure DevOps Publisher (con aprobación) | P2 | J-070 | Publicación solo con aprobación humana |
| J-083 | Construir knowledge base de reglas PIE | P2 | J-075 | Decreto 170, categorías NEE, cadena FUDEI |

---

## Fase 8 — KameCol Intelligence

| ID | Historia / Tarea | Prioridad | Dependencias | Criterios de aceptación |
|----|-----------------|:---------:|:------------:|------------------------|
| J-090 | Implementar KameCol Public API client | P2 | J-052 | Catálogo, productos, pedidos |
| J-091 | Implementar KameCol Admin API client | P2 | J-090 | Dashboard, inventario (requiere API key auth) |
| J-092 | Implementar Customer Support Agent | P3 | J-090, J-056 | Responde consultas de catálogo |
| J-093 | Implementar self-service de pedidos | P3 | J-090 | Consulta estado por referencia |
| J-094 | Implementar Order Recovery workflow | P3 | J-091, J-054 | Recuperación automatizada con reglas de timing |
| J-095 | Implementar KPI summary skill | P3 | J-091 | Resumen inteligente de métricas |

---

## Fase 9-11 — Observabilidad, Control Center, Optimización

| ID | Historia / Tarea | Prioridad | Dependencias | Criterios de aceptación |
|----|-----------------|:---------:|:------------:|------------------------|
| J-100 | Dashboard de costos y métricas (CLI) | P2 | J-024 | Costos, tokens, latencia por período |
| J-101 | Benchmark de calidad (20+ ejemplos) | P2 | J-070 | Suite de evaluación automatizada |
| J-102 | Health checks | P2 | J-054 | Verificar Ollama, Gemini, SQLite, Huey |
| J-110 | Dashboard web básico | P3 | J-100 | Visualización de estado y métricas |
| J-111 | Gestión de memoria vía web | P3 | J-110, J-037 | CRUD de memoria desde browser |
| J-120 | Optimización de modelos locales | P3 | J-101 | Selección informada por benchmarks |
| J-121 | Autonomía nivel 3-4 | P3 | J-101 | Tareas recurrentes automatizadas |
| J-122 | PWA para acceso remoto | P3 | J-110 | Acceso desde iPhone con auth |

---

## Camino crítico

```
J-001 → J-002 → J-003 → J-004 → J-005/J-006/J-007 → J-008/J-009
  → J-020 → J-021/J-022 → J-023 → J-024/J-025
    → J-030 → J-031 → J-032/J-033 → J-034/J-036 → J-037 → J-038/J-039
      [MVP COMPLETADO]
      → J-050 → J-051/J-052 → J-053/J-054 → J-056
        → J-060 → J-061-J-069
          → J-070 → J-071/J-074 → J-076
            [QA FUNCIONAL]
```
