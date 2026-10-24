# ADR-001: Estrategia de reutilización de IAAgent

**Estado:** Aceptada
**Fecha:** 2026-10-24
**Autor:** Equipo JARVIS

---

## Contexto

IAAgent es un agente de QA automatizado en producción (v0.1.0) con 38+ PRs analizados exitosamente. Contiene ~10,000 líneas de código productivo con 6 analyzers deterministas, 3 generators, abstracción LLM con fallback triple, y un cliente Azure DevOps maduro (1,018 líneas).

JARVIS necesita capacidades QA como una de sus funcionalidades principales. Reconstruir estas capacidades desde cero desperdiciaría trabajo probado en producción.

---

## Decisión

**Se adopta la Alternativa D: IAAgent como módulo especializado de JARVIS.**

JARVIS se construye como plataforma nueva con arquitectura propia (multiagente, memoria, multi-dominio). IAAgent se refactoriza gradualmente como paquete Python instalable (`iaagent-core`) que JARVIS consume como módulo QA.

---

## Alternativas evaluadas

| Alternativa | Descripción | Veredicto |
|:-----------:|-------------|:---------:|
| A | Transformar IAAgent directamente en JARVIS | Rechazada — alto riesgo de romper QA funcional |
| B | Crear JARVIS copiando módulos de IAAgent | Rechazada — crea deuda de mantenimiento por divergencia |
| C | Mantener IAAgent como servicio independiente | Rechazada — desperdicia 64% de código reutilizable |
| **D** | **IAAgent como módulo especializado de JARVIS** | **Aceptada** |

---

## Justificación

1. **Maximiza reutilización:** ~6,400 líneas (~64%) del código productivo es directamente reutilizable.
2. **Preserva QA funcional:** IAAgent CLI sigue operando durante toda la transición.
3. **Arquitectura limpia:** JARVIS nace con diseño multiagente sin heredar deuda técnica.
4. **Evolución coordinada:** Un solo equipo mantiene ambos, sin riesgo de divergencia.
5. **Producción probada:** Los analyzers y el Azure DevOps client tienen evidencia de uso real.

---

## Componentes reutilizados

| Destino | Componentes | Líneas |
|---------|------------|:------:|
| `iaagent-core` (sin cambios) | models/, 4 analyzers, 2 generators, llm/base, llm/gemini, azure_devops, trello, sanitize, filesystem, logging | ~4,100 |
| `iaagent-core` (con refactor) | static_analyzer, risk_engine, report_generator, llm/factory, config | ~2,300 |
| JARVIS (referencia) | enrichment (reimplementar con prompts dinámicos), skills .md (templates) | ~1,600 |
| Eliminar | gemini_client, context_pack, prompt_builder (dead code) | ~1,444 |

---

## Plan de ejecución

1. **Semanas 1-2:** JARVIS Core funcional. IAAgent sigue independiente.
2. **Semanas 3-4:** Empaquetar `iaagent-core` como paquete instalable.
3. **Semanas 5-6:** JARVIS QA Agent integra `iaagent-core`.

---

## Consecuencias

### Positivas
- JARVIS arranca con capacidades QA probadas desde la Fase 5.
- El sistema base de JARVIS (Fases 1-4) se construye sin dependencia de IAAgent.
- IAAgent CLI sigue disponible para uso directo durante y después de la transición.

### Negativas
- El empaquetamiento requiere refactorizar IAAgent (~3-5 días de esfuerzo).
- Se necesitan tests de regresión antes y después del refactor.
- La interfaz entre `iaagent-core` y JARVIS debe diseñarse con cuidado.

### Riesgos
- El refactor rompe funcionalidad QA existente → Mitigación: 74 tests existentes como red de seguridad.
- Las interfaces resultan inadecuadas → Mitigación: diseñar contratos Pydantic antes de implementar.

---

## Referencias

- `docs/research/IAAGENT-REUSE-ASSESSMENT.md` — Evaluación técnica completa
- `iaAgent-auditoria.md` — Auditoría técnica de IAAgent
