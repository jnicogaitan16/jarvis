# JARVIS — Alcance del MVP

**v1.0**

Fecha: 2026-10-24

---

## 1. Definición

El MVP de JARVIS es el conjunto mínimo de funcionalidades que demuestra valor real. Se completa al final de la **Fase 3** (memoria persistente).

**El MVP NO incluye:** agentes QA, integración con Azure DevOps, KameCol, interfaz web, ni publicación automatizada.

---

## 2. Capacidades del MVP

| Capacidad | Implementación | Verifica |
|-----------|---------------|----------|
| **Entrada de usuario** | CLI con Typer | El usuario puede hacer preguntas y dar instrucciones |
| **Selección de modelo** | LLM Router (Ollama + Gemini) | El sistema elige el provider según complejidad y política |
| **Herramientas deterministas** | Al menos 2 tools registradas | No todo pasa por LLM |
| **Resultado verificable** | Respuesta con metadatos (provider, tokens, latencia) | El usuario sabe qué modelo respondió |
| **Memoria persistente** | SQLite + FTS5 + embeddings locales | Recuperar información de sesiones anteriores |
| **Aislamiento de proyectos** | Namespaces en memoria | Datos de un proyecto no contaminan otro |
| **Event stream** | SQLite append-only | Toda actividad registrada |
| **Tracking de costos** | Tabla llm_usage | Saber cuánto se gasta en API |
| **Tests** | pytest con cobertura base | Verificar que funciona |
| **Configuración** | TOML + env vars | Personalizable sin tocar código |

---

## 3. User stories del MVP

### US-001: Responder preguntas
**Como** usuario, **quiero** ejecutar `jarvis ask "pregunta"` **para** recibir una respuesta del modelo apropiado.

**Criterios de aceptación:**
- Pregunta simple → modelo local (Ollama).
- Sin modelo disponible → mensaje informativo, no error.
- La respuesta incluye metadata (provider, modelo, tokens).

### US-002: Recordar información
**Como** usuario, **quiero** que JARVIS recuerde hechos que le indico **para** no repetirlos en sesiones futuras.

**Criterios de aceptación:**
- `jarvis memory add --project personal "Python 3.12 es el mínimo"` almacena el hecho.
- `jarvis memory search "versión Python"` lo recupera.
- La memoria persiste tras reiniciar JARVIS.

### US-003: Aislar proyectos
**Como** usuario, **quiero** que la memoria de IntegratePIE no aparezca en consultas de KameCol **para** mantener aislamiento.

**Criterios de aceptación:**
- Memoria almacenada con `--project integratepie` no aparece en búsquedas con `--project kamecol`.

### US-004: Ver costos
**Como** usuario, **quiero** ver cuánto he gastado en APIs **para** controlar mi presupuesto.

**Criterios de aceptación:**
- `jarvis costs` muestra resumen por provider.
- `jarvis costs --last 7d` filtra por período.

### US-005: Consultar con contexto
**Como** usuario, **quiero** que JARVIS use su memoria al responder **para** dar respuestas contextualizadas.

**Criterios de aceptación:**
- Después de almacenar información sobre un proyecto, preguntar sobre ese proyecto incluye el conocimiento almacenado en la respuesta.

---

## 4. Funcionalidades de IAAgent que aceleran el MVP

| Componente IAAgent | Uso en MVP | Esfuerzo |
|-------------------|-----------|----------|
| `llm/base.py` (Protocol) | Base para LLM Router | Copiar + extender |
| `llm/gemini.py` (Provider) | Provider cloud | Copiar directo |
| `sanitize.py` | Sanitización de logs | Copiar directo |
| `logging_config.py` | Logging con Rich | Copiar directo |
| `config.py` | Referencia para config | Adaptar |

Estos componentes (~800 líneas) pueden integrarse en la Fase 1-2 sin necesidad de empaquetar `iaagent-core` formalmente.

---

## 5. Lo que NO está en el MVP

| Feature | Fase | Razón de exclusión |
|---------|------|--------------------|
| Agente QA | F6 | Requiere sistema de agentes (F4) + IAAgent (F5) |
| Azure DevOps | F7 | Requiere QA Agent funcional + autorización |
| KameCol | F8 | Requiere API key auth + agentes |
| Interfaz web | F10 | CLI es suficiente para validar el core |
| Publicación automática | F7+ | Requiere controles de aprobación maduros |
| WhatsApp | F8+ | Requiere WhatsApp Business API (inversión) |
| pgvector | F3+ | SQLite + FTS5 es suficiente inicialmente |
| Docker | Opcional | No necesario para desarrollo local |

---

## 6. Criterio de éxito del MVP

El MVP es exitoso si:

1. **Funciona localmente** en el Mac mini M4 sin problemas de rendimiento.
2. **Recuerda información** entre sesiones de forma confiable.
3. **Selecciona el provider correcto** según la política del proyecto.
4. **Aísla proyectos** sin contaminación de memoria.
5. **Registra todo** en el event stream.
6. **No depende de un solo proveedor** — funciona con Ollama solo.
7. **Los tests pasan** y cubren las funcionalidades core.
8. **El costo es mínimo** — la capa gratuita de Gemini es suficiente para validar.

---

## 7. Comandos CLI del MVP

```bash
# Preguntas
jarvis ask "¿Qué es un PR?"
jarvis ask "¿Qué sé sobre IntegratePIE?" --project integratepie

# Memoria
jarvis memory add --project integratepie "Usa PHP 8.4 con Laravel 8.83"
jarvis memory search "Laravel versión"
jarvis memory search "reglas FUR" --project integratepie
jarvis memory list --project integratepie --type semantic

# Estado
jarvis status
jarvis costs
jarvis costs --last 7d

# Sistema
jarvis version
jarvis config show
```
