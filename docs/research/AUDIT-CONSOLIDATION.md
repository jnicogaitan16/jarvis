# Consolidación de Auditorías Técnicas

**JARVIS — Análisis transversal de IntegratePIE, IAAgent y KameCol**

Fecha: 2026-10-24

---

## 1. Resumen ejecutivo

Se auditaron tres proyectos que constituyen la base operativa de JARVIS:

| Proyecto | Dominio | Stack | LOC | Estado |
|----------|---------|-------|-----|--------|
| IntegratePIE | Educación especial SaaS (Chile) | PHP 8.4 / Laravel 8.83 / MySQL / Azure | ~174,000 | Producción, regulado por MINEDUC |
| IAAgent | Agente QA automatizado | Python 3.11+ / Typer / Azure DevOps API | ~10,000 | Producción, 38+ PRs analizados |
| KameCol | E-commerce streetwear (Colombia) | Django 5.2 / DRF / Next.js 14 / PostgreSQL 16 | No estimado | Producción, flujo comercial completo |

---

## 2. Análisis transversal

### 2.1 IntegratePIE + IAAgent — Sinergia QA

**Capacidades QA reutilizables de IAAgent para IntegratePIE:**

| Capacidad IAAgent | Aplicabilidad a IntegratePIE | Adaptación necesaria |
|-------------------|------------------------------|----------------------|
| DiffAnalyzer | Directa — analiza PRs PHP/Laravel | Ninguna, ya soporta PHP |
| SecurityAnalyzer (14 patrones OWASP) | Directa — CSRF deshabilitado, PII en sesión | Agregar patrones Laravel-específicos |
| StaticAnalyzer | Directa — TODOs, debug code, secrets | Ninguna |
| RiskEngine (score 0-10) | Directa | Calibrar pesos para dominio educativo |
| TestCaseGenerator (7 categorías) | Alta — pero requiere contexto de negocio NEE | Agregar conocimiento de reglas MINEDUC |
| LLM Enrichment (escenarios Gherkin) | Alta — Playwright listo en IntegratePIE | Adaptar prompt de Laravel genérico a PIE |
| Azure DevOps Client (1018 líneas) | Directa — IntegratePIE usa Azure DevOps | Ninguna |
| ReportGenerator | Alta | Agregar secciones específicas PIE |

**Integraciones compatibles:**
- Ambos usan Azure DevOps (pipelines, PRs, work items).
- IAAgent ya genera `PR_Comment.md` publicable en Azure DevOps.
- IntegratePIE tiene Playwright instalado pero sin tests — IAAgent puede generar los primeros.

**Conocimiento funcional requerido que JARVIS debe incorporar:**
- Decreto 170/2009 y categorías NEE (33 diagnósticos).
- Reglas de la cadena FUDEI → FUR → PAI → PACI.
- Máquina de estados de informes (9 estados).
- Configuración de rollout FUR 2026 por fases.
- Sistema de permisos PerPer.

**Duplicación potencial:**
- IAAgent genera test cases programáticos + LLM. Si JARVIS construye un agente QA desde cero, se duplicaría esta funcionalidad. Recomendación: reutilizar los generadores existentes.

**Dependencias:**
- IAAgent requiere `AZDO_PAT`, `AZDO_ORG_URL`, `AZDO_PROJECT` para operar con Azure DevOps de IntegratePIE.
- Las credenciales de IntegratePIE son empresariales — no deben almacenarse en JARVIS sin autorización.

### 2.2 IAAgent + JARVIS — Estrategia de reutilización

**Componentes reutilizables (6,400+ líneas, ~64% del código productivo):**

| Categoría | Componentes | Líneas | Esfuerzo de integración |
|-----------|-------------|--------|------------------------|
| A — Sin cambios | models/, 4 analyzers, 2 generators, LLM base/claude_code/gemini, azure_devops, trello, sanitize, filesystem, logging | ~4,100 | Bajo (1-2 días) |
| B — Refactor menor | static_analyzer, risk_engine, report_generator, LLM factory/claude, config | ~2,300 | Medio (3-5 días) |
| C — Solo referencia | enrichment (prompt hardcoded), pipeline (lineal), skills .md, knowledge .md | ~1,600 | N/A |
| D — Eliminar | gemini_client, context_pack, prompt_builder (dead code) | ~1,444 | N/A |

**Lo que JARVIS debe construir nuevo (no existe en IAAgent):**
1. Arquitectura multiagente real (IAAgent es un pipeline lineal de 10 etapas).
2. Sistema de memoria persistente (IAAgent es completamente stateless).
3. Orquestación dinámica (routing condicional, no secuencial fijo).
4. HTTP server / API (IAAgent es solo CLI).
5. Soporte multi-dominio (IAAgent solo analiza PRs).

**Cambios necesarios en los módulos reutilizados:**
- `LLMProvider` Protocol: agregar soporte para streaming y async.
- `config.py`: expandir para múltiples proyectos y servicios.
- `risk_engine.py`: hacer pesos configurables por proyecto.
- Prompts: parametrizar idioma, rol y dominio.

### 2.3 KameCol + JARVIS — Oportunidades de automatización

**APIs consumibles inmediatamente (sin autenticación):**

| Endpoint | Uso para JARVIS |
|----------|----------------|
| `GET /api/products/` | Agente de catálogo para atención al cliente |
| `GET /api/products/{slug}/` | Stock, precios, tallas en tiempo real |
| `GET /api/navigation/` | Navegación conversacional por categorías |
| `GET /api/transaction-status/{ref}/` | Self-service de estado de pedidos |

**APIs que requieren credenciales admin:**

| Endpoint | Uso para JARVIS |
|----------|----------------|
| `GET /api/admin/orders/pending-recovery/` | Recuperación de pagos pendientes |
| `POST /api/admin/orders/{ref}/send-reminder/` | Disparar recordatorios |
| `GET /api/admin/dashboard/kpis/` | Resúmenes de métricas |
| `GET /api/admin/analytics/` | Análisis de funnel |

**Procesos automatizables por prioridad:**

| Prioridad | Proceso | Dependencia de KameCol |
|-----------|---------|----------------------|
| P0 | Agente WhatsApp (catálogo + estado de pedidos) | WhatsApp Business API (no existe aún) |
| P1 | Self-service de pedidos (ref + cédula) | Endpoint de validación (trivial, ~20 líneas) |
| P1 | Recuperación automática de pagos | Scheduler + reglas de timing |
| P2 | Alertas de stock bajo | Umbrales configurables |
| P2 | Resúmenes inteligentes de KPIs | LLM + endpoints de dashboard |

**Controles de seguridad necesarios:**
- Las APIs admin usan sesión Django + 2FA (TOTP). Se necesita API key auth para acceso server-to-server.
- No existe CORS configurado — riesgo si JARVIS accede desde dominio diferente.
- Los datos de clientes (cédula, email, teléfono) son PII colombianos.
- Los precios se recalculan server-side — JARVIS no debe manipularlos.

### 2.4 Componentes comunes identificados

**Deben compartirse entre proyectos:**

| Componente | Justificación |
|-----------|---------------|
| Motor LLM (provider abstraction) | IAAgent ya tiene Protocol + 3 providers. Extender para JARVIS. |
| Registro de herramientas (tool registry) | Patrón común: cada tool declara capacidades, permisos, I/O. |
| Job engine (Huey/SQLite) | Background jobs para QA, recuperación de pagos, alertas. |
| Sistema de logs | Registro unificado con Rich (IAAgent ya lo usa). |
| Métricas de consumo | Tracking de tokens y costos (IAAgent trackea parcialmente). |
| Sanitizer | IAAgent tiene sanitize.py para credenciales — aplicable a todos. |

**NO deben compartirse:**

| Elemento | Razón |
|----------|-------|
| Credenciales | Cada proyecto tiene sus propias. JARVIS las gestiona por contexto. |
| Memoria de proyectos | IntegratePIE es empresarial, KameCol es comercial. Aislamiento obligatorio. |
| Datos de estudiantes NEE | Regulación MINEDUC. No pueden salir del contexto de IntegratePIE. |
| Datos de clientes KameCol | PII colombianos. No mezclar con contexto empresarial. |
| Prompts específicos | Cada dominio requiere conocimiento distinto. |

---

## 3. Hallazgos críticos transversales

### 3.1 Brechas de seguridad

| Proyecto | Hallazgo | Severidad | Impacto en JARVIS |
|----------|----------|-----------|-------------------|
| IntegratePIE | CSRF deshabilitado | CRÍTICO | JARVIS no debe ejecutar acciones POST sin verificar estado de CSRF |
| IntegratePIE | Sesión sin cifrar con PII | ALTO | No extraer datos de sesión hacia JARVIS |
| IntegratePIE | RUT en URLs de API | ALTO | Logs de JARVIS no deben contener RUTs |
| IntegratePIE | Multi-tenancy sin RLS | ALTO | Consultas de JARVIS deben incluir siempre filtro de RBD |
| KameCol | Sin CORS configurado | ALTO | Configurar antes de integrar JARVIS |
| KameCol | HSTS no configurado | MEDIO | Resolver en KameCol, no en JARVIS |
| IAAgent | Sin try/except en analyzers | MEDIO | Agregar error handling al integrar en JARVIS |
| IAAgent | Thresholds hardcoded | BAJO | Hacer configurables por proyecto |

### 3.2 Deuda técnica compartida

| Área | IntegratePIE | IAAgent | KameCol |
|------|-------------|---------|---------|
| Tests E2E | Playwright vacío, Nightwatch parcial | 74 tests (~60% cobertura) | 7 specs Playwright + sandbox Wompi |
| Análisis estático | Ninguno configurado | Ninguno configurado | Bandit + pip-audit en CI |
| CI/CD | 6 pipelines Azure DevOps | Ninguno | 4 workflows GitHub Actions |
| Documentación API | Sin Swagger/OpenAPI | Sin API (solo CLI) | Sin Swagger/OpenAPI |
| Docker | No (Azure App Service) | No | No (Render + Vercel) |

### 3.3 Patrones arquitectónicos comparados

| Patrón | IntegratePIE | IAAgent | KameCol |
|--------|-------------|---------|---------|
| Arquitectura | MVC + Service Layer | Pipeline lineal | Service Layer + DRF |
| API | REST interno (~50 endpoints) | CLI (Typer) | REST público + admin (~50 endpoints) |
| Autenticación | Token legacy (sin expiración) | PAT de Azure DevOps | Sesión Django + 2FA |
| Almacenamiento | Azure Blob + Google Drive + S3 | Filesystem local | Cloudflare R2 |
| Observabilidad | Sentry + Mixpanel | Rich logging | Sentry + GA4 + analytics interno |
| Cola de trabajos | Sincrónica (Redis/SQS disponible) | N/A | N/A |

---

## 4. Incertidumbres y datos faltantes

| Incertidumbre | Proyecto | Impacto en JARVIS |
|---------------|----------|-------------------|
| Autorización del equipo IntegratePIE para integración con JARVIS | IntegratePIE | Bloquea agente Azure DevOps Publisher |
| Costo de WhatsApp Business API para KameCol | KameCol | Define viabilidad del agente WhatsApp |
| Volumen de PRs mensuales de IntegratePIE | IntegratePIE | Dimensiona carga del agente QA |
| Límites de rate de la API de Azure DevOps | IntegratePIE | Afecta frecuencia de consultas |
| Presupuesto mensual para APIs de IA | General | Limita uso de modelos cloud |
| Acceso a `config/fur.php` completo para knowledge base | IntegratePIE | Sin él, el agente QA no comprende reglas de negocio |

---

## 5. Recomendaciones para la arquitectura de JARVIS

1. **Reutilizar IAAgent como módulo QA** — El 64% del código es directamente aprovechable. No reconstruir.
2. **Aislar contextos** — Memoria, credenciales y datos de cada proyecto en namespaces separados.
3. **Empezar por QA** — Es el dominio con más trabajo previo (IAAgent) y mayor necesidad (IntegratePIE sin cobertura).
4. **KameCol después del MVP** — Las APIs públicas están listas pero la integración WhatsApp requiere inversión externa.
5. **No copiar datos sensibles** — Estudiantes NEE, PII colombianos y credenciales empresariales no deben residir en JARVIS.
6. **Priorizar herramientas deterministas** — Los 6 analyzers de IAAgent son regex/programáticos y no requieren LLM.
7. **Unificar el provider LLM** — Extender el Protocol de IAAgent para soportar todos los casos de uso de JARVIS.
