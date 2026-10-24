# Arquitectura de Seguridad — JARVIS

**v1.0 — Permisos, aislamiento y controles**

Fecha: 2026-10-24

---

## 1. Modelo de amenazas

JARVIS es un sistema personal pero interactúa con:
- **IntegratePIE:** Plataforma empresarial con datos de menores con NEE (regulación MINEDUC Chile).
- **KameCol:** E-commerce con datos de clientes colombianos (PII).
- **APIs cloud:** Envío de código y texto a proveedores externos.

### 1.1 Amenazas principales

| Amenaza | Probabilidad | Impacto | Mitigación |
|---------|:---:|:---:|-----------|
| Filtración de datos empresariales de IntegratePIE | Media | Crítico | Aislamiento de namespaces, no almacenar PII |
| Prompt injection via documentos o respuestas de API | Media | Alto | Sanitización de inputs, no ejecutar instrucciones de documentos |
| Credenciales expuestas en logs o repositorio | Media | Crítico | Sanitizer global, `.env` en `.gitignore` |
| Ejecución no autorizada en Azure DevOps | Baja | Alto | Aprobación humana obligatoria para escrituras |
| Contaminación de memoria entre proyectos | Media | Alto | Namespaces, filtros obligatorios en queries |
| LLM genera información falsa como conocimiento | Alta | Medio | No auto-incorporar respuestas LLM, confianza diferenciada |
| Acceso no autorizado a JARVIS (API) | Baja | Alto | Solo localhost en MVP, auth en fase posterior |
| Costos descontrolados de API | Media | Medio | Presupuesto configurable con auto-switch a local |

---

## 2. Aislamiento de proyectos

### 2.1 Project Context

Cada operación se ejecuta dentro de un contexto de proyecto:

```python
@dataclass(frozen=True)
class ProjectContext:
    project_id: str                    # "integratepie", "kamecol", "personal"
    display_name: str
    allowed_tools: frozenset[str]      # IDs de herramientas permitidas
    allowed_providers: frozenset[str]  # Proveedores LLM autorizados
    privacy_policy: PrivacyPolicy
    autonomy_level: int                # 0-4
    credentials_ref: str               # Referencia a credenciales (no las credenciales)
    memory_namespace: str              # Namespace de memoria

@dataclass(frozen=True)
class PrivacyPolicy:
    allow_cloud: bool
    allow_code_to_cloud: bool
    allow_pii_to_cloud: bool
    sensitive_patterns: frozenset[str]  # Regex de datos sensibles
    data_retention_days: int
```

### 2.2 Enforcement

```python
class SecurityGate:
    """Verifica permisos antes de cada operación."""

    def check_tool_access(self, tool_id: str, context: ProjectContext) -> bool:
        return tool_id in context.allowed_tools

    def check_llm_access(self, provider: str, context: ProjectContext) -> bool:
        return provider in context.allowed_providers

    def check_memory_access(self, memory_project: str, context: ProjectContext) -> bool:
        return memory_project == context.memory_namespace or memory_project == "system"

    def sanitize_for_cloud(self, text: str, policy: PrivacyPolicy) -> str:
        """Redacta datos sensibles antes de enviar a cloud."""
        for pattern in policy.sensitive_patterns:
            text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
        return text
```

---

## 3. Clasificación de operaciones

| Tipo | Requiere aprobación | Ejemplos |
|------|:---:|---------|
| **Lectura** | No | Leer PR, consultar catálogo, buscar en memoria |
| **Análisis** | No | Ejecutar analyzers, calcular riesgo, generar test cases |
| **Propuesta** | No | Preparar comentario, generar reporte |
| **Ejecución local** | No | Correr tests locales, generar embeddings |
| **Escritura externa** | **Sí** | Publicar en Azure DevOps, enviar email |
| **Modificación** | **Sí** | Actualizar work item, cambiar estado de orden |
| **Eliminación** | **Siempre + confirmación** | Invalidar memoria, cancelar job |

---

## 4. Protección de credenciales

### 4.1 Almacenamiento

```bash
# .env (NUNCA en git)
AZDO_PAT=<token>
AZDO_ORG_URL=https://dev.azure.com/organization
AZDO_PROJECT=project-name
GEMINI_API_KEY=AI...
KAMECOL_API_KEY=<futuro>
# Claude API no disponible como recurso personal
```

### 4.2 Sanitización global

IAAgent incluye `sanitize.py` que se aplica globalmente en JARVIS:

```python
SENSITIVE_PATTERNS = [
    r'(?i)(api[_-]?key|token|password|secret|pat)\s*[=:]\s*\S+',
    r'sk-ant-[a-zA-Z0-9-]+',          # Claude API keys
    r'AI[a-zA-Z0-9_-]{30,}',          # Gemini API keys
    r'\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b',  # RUT chileno
    r'\b\d{6,10}\b(?=.*cedula)',        # Cédula colombiana (en contexto)
]

def sanitize_for_logging(text: str) -> str:
    """Redacta información sensible antes de logging."""
    for pattern in SENSITIVE_PATTERNS:
        text = re.sub(pattern, '[REDACTED]', text)
    return text
```

### 4.3 Reglas de logs

- Todo logging pasa por `sanitize_for_logging()`.
- Los events del event stream sanitizan payloads automáticamente.
- Las evidencias de ejecución no incluyen credenciales ni PII.
- Los prompts enviados a LLMs cloud se sanitizan según la PrivacyPolicy del proyecto.

---

## 5. Prevención de prompt injection

### 5.1 Fuentes no confiables

| Fuente | Nivel de confianza | Tratamiento |
|--------|:---:|-------------|
| Input del usuario | Confiable | Se ejecuta como instrucción |
| Documentos de auditoría | Referencia | Se lee, no se ejecuta como instrucción |
| Código fuente | Referencia | Se analiza, no se ejecuta instrucciones embebidas |
| Respuestas de APIs externas | No confiable | Se sanitiza, se valida formato |
| Mensajes de clientes (WhatsApp) | No confiable | Se trata como datos, no como instrucciones |
| Respuestas de LLMs | Semi-confiable | Se valida formato; no se auto-incorpora como conocimiento |

### 5.2 Medidas

1. **Separación de datos e instrucciones:** Los documentos y respuestas de APIs se inyectan en el prompt con delimitadores claros (`<document>...</document>`) y la instrucción del sistema indica que el contenido dentro es datos, no instrucciones.

2. **No ejecutar instrucciones de documentos:** Si un documento dice "ejecuta rm -rf /", JARVIS lo ignora como instrucción. Solo el usuario puede emitir comandos.

3. **Validación de formato:** Las respuestas de LLMs que alimentan herramientas se parsean con schemas estrictos (Pydantic). Si el formato no coincide, se rechaza.

4. **Sandboxing de ejecución:** Los comandos que JARVIS ejecuta están en una allowlist. No se permite ejecución arbitraria.

---

## 6. Información empresarial

### 6.1 Principio

Disponer de acceso técnico a un sistema NO implica autorización para exportar su información. JARVIS respeta los límites de cada contexto.

### 6.2 Reglas para IntegratePIE

| Permitido | Prohibido |
|-----------|-----------|
| Analizar código fuente de PRs | Copiar código completo al repositorio JARVIS |
| Almacenar hallazgos de análisis QA | Almacenar datos de estudiantes (RUT, diagnósticos) |
| Guardar patrones arquitectónicos | Exportar `config/fur.php` completo |
| Recordar resultados de análisis | Almacenar credenciales de Azure DevOps en memoria |
| Indexar documentación técnica autorizada | Indexar datos de producción |

### 6.3 Reglas para KameCol

| Permitido | Prohibido |
|-----------|-----------|
| Consultar catálogo público | Almacenar datos de clientes (cédula, email) en JARVIS |
| Registrar métricas agregadas | Exportar base de datos de clientes |
| Almacenar patrones de producto | Almacenar información de pagos |
| Analizar métricas de ventas | Compartir datos de KameCol con contexto IntegratePIE |

---

## 7. Control de acceso a JARVIS

### MVP (localhost)

- FastAPI solo escucha en `127.0.0.1`.
- Sin autenticación necesaria (acceso local).
- CLI sin auth (usuario del sistema).

### Fase posterior (acceso remoto)

| Capa | Mecanismo |
|------|-----------|
| Transporte | HTTPS obligatorio (certificado Let's Encrypt o self-signed) |
| Autenticación | API key + session token |
| Autorización | Roles: admin (full), readonly (consultas) |
| Rate limiting | Configurable por endpoint |
| IP allowlist | Opcional para acceso remoto |
| 2FA | Para operaciones de escritura desde remoto |

---

## 8. Auditoría de seguridad

### 8.1 Eventos auditables

Todo el event stream es un audit log. Eventos de seguridad específicos:

| Evento | Trigger | Datos registrados |
|--------|---------|-------------------|
| `auth.login` | Acceso a JARVIS | IP, timestamp, método |
| `auth.denied` | Acceso denegado | IP, motivo |
| `tool.write_attempt` | Intento de escritura externa | tool_id, project, aprobado/rechazado |
| `memory.cross_project` | Acceso a memoria de otro proyecto | solicitante, target, autorizado/denegado |
| `llm.cloud_send` | Envío de datos a cloud | provider, project, tokens, sanitized=true |
| `security.pii_detected` | PII detectado en output | tipo de PII, ubicación, acción tomada |
| `security.injection_attempt` | Posible prompt injection | fuente, contenido sospechoso |

### 8.2 Retención

- Event log: indefinido (SQLite, compresión mensual de eventos >90 días).
- Evidencias: 90 días por defecto, configurable por proyecto.
- Logs de aplicación: 30 días rotación.

---

## 9. Checklist de seguridad por fase

### Fase 1 — JARVIS Core (MVP)

- [ ] `.env` en `.gitignore`
- [ ] `.env.example` sin valores reales
- [ ] Sanitizer global en logging
- [ ] FastAPI solo en localhost
- [ ] Credenciales en env vars, no en código
- [ ] ProjectContext obligatorio en todas las operaciones
- [ ] Memory namespace enforcement

### Fase 6 — QA Intelligence

- [ ] Aprobación humana para publicaciones en Azure DevOps
- [ ] No almacenar RUT ni datos de estudiantes en memoria
- [ ] Sanitizar código antes de enviar a cloud
- [ ] Rate limiting en consultas a Azure DevOps

### Fase 8 — KameCol Intelligence

- [ ] API key auth implementado en KameCol
- [ ] CORS configurado
- [ ] No almacenar PII colombianos en memoria
- [ ] Aislamiento total de memoria KameCol vs IntegratePIE

### Fase 10 — Control Center (web)

- [ ] HTTPS obligatorio
- [ ] Auth + session management
- [ ] CSRF protection
- [ ] CSP headers
- [ ] Rate limiting por endpoint
