# Auditoría Técnica — JARVIS

> Fecha: 2026-10-28
> Tests: 331/333 passed (2 fallos por incompatibilidad Typer + Python 3.14)

---

## Resumen

- **Funcionalidades verificadas:** CLI, Web API, agentes QA, memoria, LLM routing, integraciones
- **Tests:** 331 passed, coverage >=60%
- **Seguridad:** SecurityGate implementado pero NO integrado en flujo real
- **Datos a LLM:** Se envían SIN sanitizar (hallazgo crítico)

---

## Estado de Funcionalidades

### Funcional (comprobado via tests + código)

- CLI con 20+ comandos (ask, chat, analyze-pr, pipeline, memory, metrics, etc.)
- Web API FastAPI (/health, /metrics, /projects, /agents, /memory, /events)
- LLM Router con 3 providers (Ollama, Gemini, Claude Code) + fallback automático
- Memoria persistente SQLite + FTS5 con búsqueda híbrida (textual 40% + semántica 60%)
- EventStore append-only en SQLite
- Usage tracking (tokens, costos, latencia) por provider/proyecto
- QAAgent con bridge a IAAgent (6 analyzers + generators)
- CodeReviewAgent (12 patrones regex de análisis estático)
- GherkinAgent (generación BDD determinista sin LLM)
- TestStrategyAgent (evaluación ROI de automatización)
- WriterAgent (5 templates estructurados)
- Pipeline engine (4 workflows predefinidos, contexto compartido)
- KameColAgent (consultas catálogo/pedidos/KPIs)
- Plugin discovery (MCP servers)
- Health checks (7 servicios)
- Benchmarks (3 suites: intent, security, memory)
- Aislamiento de memoria por proyecto/namespace
- 5 niveles de autonomía configurables por proyecto
- Lectura controlada de repos (allow/deny patterns)

### Implementado pero NO activo

- SecurityGate (sanitización de credenciales + PII) — existe en código y tests pero no se invoca en flujo real
- Budget enforcement — configurado ($5/semana) pero no se verifica antes de requests
- LLM response cache — campo `cached` existe pero sin implementación
- Background jobs (Huey) — estructura existe pero tareas son stubs

### No implementado

- Análisis AST propio (solo regex; el AST viene via IAAgent)
- ML/LLM para detección de intent (solo regex)
- Cache de respuestas LLM propio
- Enforcement real del budget de LLM

---

## Seguridad — Hallazgos

### CRITICO: Datos enviados sin sanitizar a LLMs cloud

- `SecurityGate.sanitize_for_cloud()` existe pero NO se invoca en:
  - `cli.py` comando `ask` (línea 175)
  - `cli.py` comando `chat` (línea 1236)
  - `llm/router.py` función `generate()` (línea 94)
  - Ningún agente
- `allow_pii_to_cloud=False` se configura en TOML pero nunca se verifica en runtime
- **Impacto:** Datos sensibles (nombres de alumnos, RUTs, diagnósticos de IntegratePIE; cédulas, emails de KameCol) podrían enviarse a Gemini sin redactar

### OK: Aislamiento de memoria

- Memoria filtrada por namespace de proyecto (comprobado via tests)
- Cross-project access bloqueado en `SecurityGate.check_memory_access()`

### OK: Lectura de repos controlada

- `repo_reader.py` tiene allow/deny patterns
- `.env`, `*.db`, `*.sqlite3` están en deny list
- `media/*`, `node_modules/*` excluidos

### OK: Credenciales no en código

- `.env.example` no contiene valores reales
- `.gitignore` incluye `.env`, `*.db`, `data/`, `workspace/`

### MEDIO: Budget no enforced

- `config/models.toml` define $5/semana y $1.50/día alerta
- No hay código que verifique estos límites antes de hacer requests LLM
- Usage tracking SÍ registra costos, pero no bloquea

---

## Validación de .env.example

El cambio en `.env.example` es correcto:
- Mejor documentación y organización por secciones
- Agrega variables faltantes (MySQL, Sentry, Trello, seguridad)
- No contiene valores reales de credenciales
- Incluye notas de seguridad al final

---

## Archivos Nuevos Pendientes de Commit

- `.claude/` — Configuración de Claude Code para el proyecto
- `docs/research/ENTERPRISE-DEV-TEAM-PLUGINS.md` — Investigación de plugins
- `workspace/` — Directorio de trabajo con cache de enrichments

---

*Auditoría generada por JARVIS · 2026-10-28*
